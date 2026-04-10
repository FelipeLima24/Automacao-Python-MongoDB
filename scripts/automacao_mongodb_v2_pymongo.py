"""
AUTOMACAO MONGODB V2.0 - EXECUCAO VIA PYMONGO

Esta versao foi simplificada para seguir o mesmo espirito da V1

Diferenca principal:
- a V1 entrega o texto inteiro para o mongosh;
- a V2 executa direto pelo Python com PyMongo.

Como o PyMongo nao executa o comando como string bruta, a V2 faz apenas a
adaptacao tecnica minima de cada linha:
- remove o prefixo do comando;
- remove o sufixo do comando;
- separa filtro e update;
- converte para dict;
- executa no banco.

Importante:
- a V2 nao valida negocio;
- a V2 nao corrige lote;
- se o arquivo vier errado, o correto continua sendo devolver para o
  desenvolvimento.
"""

from __future__ import annotations

import json
import os
import zipfile
from datetime import datetime

from pymongo import MongoClient
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError

MONGODB_URI = "mongodb://localhost:27017"
MONGODB_DATABASE = "smartbill"

# A V2 segue um contrato simples e direto.
# O lote ja vem pronto, entao so removemos o que envolve o filtro e o update.
COMANDO_PREFIXO = "db.document.updateMany("
COMANDO_SUFIXO = ");"


def ler_arquivo(caminho: str):
    """
    Le um .txt ou todos os .txt de um .zip.

    O retorno segue o mesmo estilo da V1:
    - se deu certo
    - conteudo final do lote
    - lista de arquivos lidos
    """

    if not os.path.exists(caminho):
        return False, f"Arquivo nao encontrado: {caminho}", []

    conteudo_total = []
    arquivos_lidos = []
    # zip
    if caminho.lower().endswith(".zip"):
        try:
            with zipfile.ZipFile(caminho, "r") as zf:
                arquivos_txt = [
                    nome
                    for nome in sorted(zf.namelist())
                    if nome.lower().endswith(".txt") and not nome.startswith("__MACOSX")
                ]

                # erro
                if not arquivos_txt:
                    return False, "Nenhum .txt encontrado no ZIP", []

                for nome in arquivos_txt:
                    conteudo = zf.read(nome).decode("utf-8", errors="replace")
                    conteudo_total.append(conteudo)
                    arquivos_lidos.append(nome)
        # erro
        except zipfile.BadZipFile:
            return False, "Arquivo ZIP corrompido", []
    # txt
    elif caminho.lower().endswith(".txt"):
        try:
            with open(caminho, "r", encoding="utf-8") as arquivo:
                conteudo = arquivo.read()
            conteudo_total.append(conteudo)
            arquivos_lidos.append(os.path.basename(caminho))
        except OSError as erro:
            return False, f"Erro ao ler arquivo: {erro}", []

    else:
        return False, "Formato nao suportado. Use .zip ou .txt", []

    return True, "\n".join(conteudo_total), arquivos_lidos


def simular(conteudo: str, arquivos: list[str]) -> None:
    """Mostra o lote na tela sem alterar o banco."""

    print("\n" + "=" * 60)
    print("SIMULACAO V2 - Nada sera executado no banco")
    print("=" * 60)
    print(f"Arquivos do lote: {', '.join(arquivos)}")
    print(f"Banco alvo: {MONGODB_DATABASE}")
    print("-" * 60)
    print("\nCOMANDOS QUE SERAO EXECUTADOS:\n")
    print(conteudo)
    print("\n" + "-" * 60)
    print("FIM DA SIMULACAO")
    print("=" * 60)


def obter_linhas_comando(conteudo: str) -> list[tuple[int, str]]:
    """
    Separa o lote em linhas preservando a numeracao original.

    Regra adotada:
    - cada linha nao vazia e um comando;
    - o script nao tenta limpar, corrigir ou interpretar alem disso.

    Isso respeita a divisao de responsabilidade:
    - desenvolvimento monta o lote;
    - sustentacao executa o lote.
    """

    linhas = []

    for numero_linha, linha in enumerate(conteudo.splitlines(), start=1):
        linha_limpa = linha.strip()
        if not linha_limpa:
            continue
        linhas.append((numero_linha, linha_limpa))

    return linhas


def dividir_argumentos_principais(argumentos: str) -> tuple[str, str]:
    """
    Separa os dois argumentos principais do updateMany:
    - filtro
    - update

    Nao da para usar split(',') porque ha varias virgulas dentro do
    proprio filtro e do proprio update. Entao percorremos o texto e
    aceitamos como separador apenas a virgula que estiver fora dos blocos
    de chaves e fora de strings.
    """

    atual = []
    partes = []
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
        raise ValueError("Nao foi possivel separar filtro e update da linha.")

    return partes[0], partes[1]


def normalizar_update(update_texto: str) -> str:
    """
    Converte o update do estilo do shell para JSON lido pelo Python.

    Exemplo:
    - entrada: {$set: {"campo": "valor"}}
    - saida:   {"$set": {"campo": "valor"}}

    Isso nao e validacao de negocio.
    E apenas a adaptacao minima para que json.loads consiga transformar
    o texto em dict Python.
    """

    return update_texto.replace("{$set:", '{"$set":', 1)


def parsear_linha(numero_linha: int, linha: str) -> tuple[dict, dict]:
    """
    Pega a linha pronta do lote e devolve:
    - filtro em dict
    - update em dict

    Aqui esta a diferenca real para a V1.
    A V1 repassa a string inteira para o mongosh.
    A V2 precisa extrair o minimo necessario porque o PyMongo nao aceita
    a string completa do comando.
    """

    if not linha.startswith(COMANDO_PREFIXO):
        raise ValueError(
            f"Linha {numero_linha} nao comeca com {COMANDO_PREFIXO}"
        )

    if not linha.endswith(COMANDO_SUFIXO):
        raise ValueError(
            f"Linha {numero_linha} nao termina com {COMANDO_SUFIXO}"
        )

    argumentos = linha[len(COMANDO_PREFIXO) : -len(COMANDO_SUFIXO)]
    filtro_texto, update_texto = dividir_argumentos_principais(argumentos)

    filtro = json.loads(filtro_texto)
    update = json.loads(normalizar_update(update_texto))

    return filtro, update


def preparar_comandos(conteudo: str) -> list[tuple[int, dict, dict]]:
    """
    Monta a lista de comandos que a execucao vai usar.

    Esta etapa nao tenta "validar o lote".
    Ela apenas transforma cada linha em algo que o PyMongo consegue
    executar.
    """

    comandos = []

    for numero_linha, linha in obter_linhas_comando(conteudo):
        filtro, update = parsear_linha(numero_linha, linha)
        comandos.append((numero_linha, filtro, update))

    return comandos


def executar(conteudo: str, arquivos: list[str]):
    """
    Executa o lote no MongoDB com PyMongo.

    Fluxo:
    - transforma cada linha em filtro/update;
    - abre a conexao MongoDB;
    - seleciona o banco smartbill;
    - executa updateMany linha por linha na collection document.

    Equivalente ao `use smartbill` do shell:
    - aqui fazemos db = client["smartbill"]
    """

    print("\n" + "=" * 60)
    print("EXECUTANDO NO MONGODB VIA PYMONGO")
    print("=" * 60)

    try:
        comandos = preparar_comandos(conteudo)
    except Exception as erro:  # noqa: BLE001
        print(f"\n[ERRO] {erro}")
        return False, str(erro)

    try:
        client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
        )
        client.admin.command("ping")
        db = client[MONGODB_DATABASE]
        colecao = db["document"]
    except ServerSelectionTimeoutError as erro:
        msg = f"Falha ao conectar no MongoDB: {erro}"
        print(f"\n[ERRO] {msg}")
        return False, msg
    except PyMongoError as erro:
        msg = f"Erro ao abrir conexao MongoDB: {erro}"
        print(f"\n[ERRO] {msg}")
        return False, msg

    try:
        total_sucesso = 0
        total_matched = 0
        total_modified = 0

        print(f"[INFO] Conectando em: {MONGODB_URI}")
        print(f"[INFO] Banco: {MONGODB_DATABASE}")
        print("[INFO] Colecao: document")
        print("[INFO] Executando comandos...\n")

        for numero_linha, filtro, update in comandos:
            try:
                resultado = colecao.update_many(filtro, update)
            except PyMongoError as erro:
                msg = f"Erro ao executar linha {numero_linha}: {erro}"
                print(f"\n[ERRO] {msg}")
                return False, msg

            total_sucesso += 1
            total_matched += resultado.matched_count
            total_modified += resultado.modified_count

            print(
                f"[OK] Linha {numero_linha} | document.updateMany | "
                f"matched={resultado.matched_count} modified={resultado.modified_count}"
            )

        msg = (
            f"Execucao concluida com sucesso. "
            f"Comandos: {total_sucesso} | "
            f"Matched: {total_matched} | Modified: {total_modified}"
        )
        print(f"\n[OK] {msg}")
        return True, msg

    finally:
        client.close()


def menu():
    """Menu interativo principal da V2, no mesmo estilo da V1."""

    print("\n" + "=" * 60)
    print("AUTOMACAO MONGODB V2.0 - SUSTENTACAO B2C")
    print("=" * 60)
    print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"Banco: {MONGODB_DATABASE}")
    print("=" * 60)

    print("\n[1] Informe o caminho do arquivo (.zip ou .txt)")
    print("    Exemplo: C:\\lotes\\abril.zip")
    print("    Exemplo: ./comandos.txt\n")

    caminho = input("Arquivo: ").strip().strip('"').strip("'")

    if not caminho:
        print("\n[ERRO] Caminho vazio. Saindo.")
        return

    sucesso, conteudo, arquivos = ler_arquivo(caminho)

    if not sucesso:
        print(f"\n[ERRO] {conteudo}")
        return

    print(f"\n[OK] Arquivo(s) lido(s): {', '.join(arquivos)}")

    linhas = [linha for linha in conteudo.split("\n") if linha.strip()]
    print(f"[OK] {len(linhas)} linha(s) de comando encontrada(s)")

    print("\n[2] O que deseja fazer?")
    print("    [1] Simular (ver comandos)")
    print("    [2] Executar direto")
    print("    [0] Sair\n")

    opcao = input("Opcao: ").strip()

    if opcao == "0":
        print("\nSaindo.")
        return

    if opcao == "1":
        simular(conteudo, arquivos)

        print("\n[3] Deseja executar agora?")
        print("    [S] Sim")
        print("    [N] Nao\n")

        confirma = input("Executar? (S/N): ").strip().upper()

        if confirma == "S":
            print("\n[ATENCAO] Os comandos serao executados no banco!")
            print("          Acao NAO pode ser desfeita automaticamente.\n")

            confirma2 = input("Digite EXECUTAR para confirmar: ").strip()

            if confirma2 == "EXECUTAR":
                executar(conteudo, arquivos)
            else:
                print("\nCancelado.")
        else:
            print("\nSimulacao encerrada. Nada foi executado.")

    elif opcao == "2":
        print("\n[ATENCAO] Os comandos serao executados DIRETO no banco!")
        print("          Acao NAO pode ser desfeita automaticamente.")
        print("          Recomendamos simular primeiro.\n")

        confirma = input("Digite EXECUTAR para confirmar: ").strip()

        if confirma in {"EXECUTAR", "executar"}:
            executar(conteudo, arquivos)
        else:
            print("\nCancelado.")

    else:
        print("\n[ERRO] Opcao invalida.")


if __name__ == "__main__":
    menu()
    print("\n[FIM]\n")
