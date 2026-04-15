"""
AUTOMACAO MONGODB V2 - EXECUCAO BATCH

Script operacional para Sustentacao B2C.
Roda em modo nao interativo para uso recorrente via agendador.

Regras deste script:
- executa lote recebido;
- nao cria comando;
- nao corrige negocio;
- nao interpreta intencao do time de desenvolvimento.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import zipfile
from pathlib import Path

from pymongo import MongoClient
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError


MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DATABASE = "smartbill"
MONGODB_COLLECTION = "document"

BASE_DIR = Path(__file__).resolve().parents[1]

# No MVP o lote vem de caminho fixo para manter a execucao previsivel.
ARQUIVO_ENTRADA_FIXO = BASE_DIR / "testes" / "lote_mvp_teste.txt"

LOG_FILE = BASE_DIR / "logs" / "automacao_mongodb_v2.log"

COMANDO_PREFIXO = f"db.{MONGODB_COLLECTION}.updateMany("
COMANDO_SUFIXO = ");"


def configurar_log() -> logging.Logger:
    """Configura log simples em arquivo e console."""

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )

    return logging.getLogger("automacao_mongodb_v2")


def localizar_arquivos_txt(caminho_entrada: Path) -> tuple[list[Path], tempfile.TemporaryDirectory[str] | None]:
    """
    Recebe um .txt ou .zip e devolve a lista de .txt prontos para leitura.

    Se vier zip, extraimos em pasta temporaria para manter o lote original intacto.
    """

    if not caminho_entrada.exists():
        raise FileNotFoundError(f"Arquivo de entrada nao encontrado: {caminho_entrada}")

    if caminho_entrada.suffix.lower() == ".txt":
        return [caminho_entrada], None

    if caminho_entrada.suffix.lower() == ".zip":
        pasta_temp = tempfile.TemporaryDirectory(prefix="lote_mongodb_")

        try:
            with zipfile.ZipFile(caminho_entrada, "r") as arquivo_zip:
                arquivo_zip.extractall(pasta_temp.name)
        except zipfile.BadZipFile as erro:
            pasta_temp.cleanup()
            raise ValueError("Arquivo ZIP corrompido") from erro

        arquivos_txt = sorted(Path(pasta_temp.name).rglob("*.txt"))
        if not arquivos_txt:
            pasta_temp.cleanup()
            raise ValueError("Nenhum .txt encontrado no ZIP")

        return arquivos_txt, pasta_temp

    raise ValueError("Formato nao suportado. Use .zip ou .txt")


def ler_linhas_de_comando(arquivos_txt: list[Path]) -> list[dict[str, object]]:
    """
    Le os .txt e transforma cada linha nao vazia em um comando.

    A gente guarda arquivo e linha para facilitar rastreabilidade no log.
    """

    comandos: list[dict[str, object]] = []

    for arquivo in arquivos_txt:
        with arquivo.open("r", encoding="utf-8", errors="replace") as handler:
            for numero_linha, linha in enumerate(handler, start=1):
                texto = linha.strip()
                if not texto:
                    continue

                comandos.append(
                    {
                        "arquivo": arquivo.name,
                        "linha": numero_linha,
                        "texto": texto,
                    }
                )

    if not comandos:
        raise ValueError("Nenhum comando encontrado nos arquivos do lote")

    return comandos


def dividir_filtro_update(argumentos: str) -> tuple[str, str]:
    """
    Separa os dois argumentos do updateMany: filtro e update.

    Nao usamos split(',') simples porque ha virgulas dentro do proprio JSON.
    Aqui so quebramos na virgula que esta fora de chaves, colchetes e strings.
    """

    partes: list[str] = []
    atual: list[str] = []

    profundidade_chaves = 0
    profundidade_colchetes = 0
    em_string = False
    escape_ativo = False

    for caractere in argumentos:
        if em_string:
            atual.append(caractere)
            if escape_ativo:
                escape_ativo = False
            elif caractere == "\\":
                escape_ativo = True
            elif caractere == '"':
                em_string = False
            continue

        if caractere == '"':
            em_string = True
            atual.append(caractere)
            continue

        if caractere == "{":
            profundidade_chaves += 1
        elif caractere == "}":
            profundidade_chaves -= 1
        elif caractere == "[":
            profundidade_colchetes += 1
        elif caractere == "]":
            profundidade_colchetes -= 1

        if caractere == "," and profundidade_chaves == 0 and profundidade_colchetes == 0:
            partes.append("".join(atual).strip())
            atual = []
            continue

        atual.append(caractere)

    partes.append("".join(atual).strip())

    if len(partes) != 2:
        raise ValueError("Nao foi possivel separar filtro e update")

    return partes[0], partes[1]


def adaptar_comando_para_pymongo(comando: dict[str, object]) -> tuple[dict, dict]:
    """
    Converte a linha recebida para o formato aceito pelo PyMongo.

    O shell aceita texto completo como db.document.updateMany(...),
    mas o driver Python so aceita filtro e update separados em dict.
    """

    texto = str(comando["texto"])
    arquivo = str(comando["arquivo"])
    linha = int(comando["linha"])
    origem = f"{arquivo}:{linha}"

    if not texto.startswith(COMANDO_PREFIXO):
        raise ValueError(f"{origem} nao inicia com {COMANDO_PREFIXO}")

    if not texto.endswith(COMANDO_SUFIXO):
        raise ValueError(f"{origem} nao termina com {COMANDO_SUFIXO}")

    # Aqui a gente remove o prefixo "db.document.updateMany(" e o sufixo ");"
    # porque o PyMongo nao entende esse formato de string inteira.
    # Ele precisa receber apenas filtro e update como objetos separados.
    argumentos = texto[len(COMANDO_PREFIXO) : -len(COMANDO_SUFIXO)]
    filtro_texto, update_texto = dividir_filtro_update(argumentos)

    # Esse ajuste e tecnico: no shell e comum vir {$set: ...} sem aspas na chave.
    # Para json.loads funcionar, precisamos deixar "${operador}" como string JSON valida.
    update_texto = update_texto.replace("{$set:", '{"$set":', 1)

    try:
        filtro = json.loads(filtro_texto)
        update = json.loads(update_texto)
    except json.JSONDecodeError as erro:
        raise ValueError(f"{origem} falhou ao converter comando para dict") from erro

    return filtro, update


def executar_lote(comandos: list[dict[str, object]], logger: logging.Logger) -> int:
    """Executa o lote no MongoDB e retorna quantidade de erros."""

    try:
        client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
        )
        client.admin.command("ping")
    except ServerSelectionTimeoutError as erro:
        raise RuntimeError(f"Falha ao conectar no MongoDB: {erro}") from erro
    except PyMongoError as erro:
        raise RuntimeError(f"Erro ao abrir conexao MongoDB: {erro}") from erro

    colecao = client[MONGODB_DATABASE][MONGODB_COLLECTION]


    total_sucesso = 0
    total_erro = 0
    total_matched = 0
    total_modified = 0


    try:
        for posicao, comando in enumerate(comandos, start=1):
            origem = f"{comando['arquivo']}:{comando['linha']}"
            try:
                filtro, update = adaptar_comando_para_pymongo(comando)
                resultado = colecao.update_many(filtro, update)
            except Exception as erro:  # noqa: BLE001
                total_erro += 1
                logger.error(
                    "COMANDO_ERRO | comando=%s | detalhe=%s",
                    origem,
                    erro,
                )
                break

            total_sucesso += 1
            total_matched += resultado.matched_count
            total_modified += resultado.modified_count
    finally:
        client.close()

    logger.info(
        "RESUMO_EXECUCAO | sucesso=%s | erro=%s | matched_total=%s | modified_total=%s",
        total_sucesso,
        total_erro,
        total_matched,
        total_modified,
    )

    return total_erro


def main() -> int:
    """Ponto de entrada batch para Control-M."""

    logger = configurar_log()

    logger.info("ARQUIVO_ENTRADA=%s", ARQUIVO_ENTRADA_FIXO)

    pasta_temp: tempfile.TemporaryDirectory[str] | None = None

    try:

        arquivos_txt, pasta_temp = localizar_arquivos_txt(ARQUIVO_ENTRADA_FIXO)
        logger.info("ARQUIVOS_TXT=%s", len(arquivos_txt))
        comandos = ler_linhas_de_comando(arquivos_txt)
        logger.info("COMANDOS_ENCONTRADOS=%s", len(comandos))

 
        total_erros = executar_lote(comandos, logger)
        status = "SUCESSO" if total_erros == 0 else "FALHA"
        logger.info("FIM_EXECUCAO | status=%s", status)

        return 0 if total_erros == 0 else 1

    except Exception as erro:  # noqa: BLE001
        logger.error("FALHA_GERAL | detalhe=%s", erro)
        logger.info("FIM_EXECUCAO | status=FALHA")
        return 1

    finally:
        if pasta_temp is not None:
            pasta_temp.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
