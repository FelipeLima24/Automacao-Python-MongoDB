"""
AUTOMACAO MONGODB V2.0 - EXECUCAO VIA PYMONGO

Esta versao segue o mesmo fluxo da V1:
- le um .txt ou .zip com comandos prontos;
- mostra a simulacao na tela;
- executa so depois da confirmacao.

Diferenca real da V2:
- a V1 entrega o texto inteiro para o mongosh interpretar;
- a V2 usa o driver PyMongo;
- por isso, antes de executar, a V2 precisa tirar da linha apenas
  o filtro e o update.

Para manter a sustentacao simples, a V2 aceita somente o formato real
combinado para o lote:

db.document.updateMany({"customer.document": "11111111111111", "document.barCode": "000000000000000000000000000000000000000000000000", "document.flProForma": false}, {$set: {"customer.accountNumber": "99999999999"}});

Se o desenvolvimento mandar algo fora desse contrato, a V2 para e devolve erro.
"""

from __future__ import annotations

import json
import os
import zipfile
from dataclasses import dataclass
from datetime import datetime

from pymongo import MongoClient
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError

MONGODB_URI = "mongodb://localhost:27017"
MONGODB_DATABASE = "smartbill"

COLECAO_ALVO = "document"
COMANDO_PREFIXO = "db.document.updateMany("
COMANDO_SUFIXO = ");"
FORMATO_EXEMPLO = (
    'db.document.updateMany({"customer.document": "11111111111111", '
    '"document.barCode": "000000000000000000000000000000000000000000000000", '
    '"document.flProForma": false}, {$set: {"customer.accountNumber": "99999999999"}});'
)

CHAVES_FILTRO = {
    "customer.document",
    "document.barCode",
    "document.flProForma",
}
CHAVES_SET = {"customer.accountNumber"}


@dataclass
class ComandoDocumento:
    """
    Guarda so o que o PyMongo precisa para executar a linha.

    A ideia aqui e deixar a execucao bem direta:
    linha original -> filtro -> update
    """

    arquivo: str
    linha: int
    texto_original: str
    filtro: dict
    atualizacao: dict


def ler_arquivo(caminho: str):
    """
    Le um .txt ou junta todos os .txt de um .zip.
    Retorna: (sucesso, conteudo_ou_erro, lista_arquivos)
    """

    if not os.path.exists(caminho):
        return False, f"Arquivo nao encontrado: {caminho}", []

    conteudo_total = []
    arquivos_lidos = []

    if caminho.lower().endswith(".zip"):
        try:
            with zipfile.ZipFile(caminho, "r") as zf:
                arquivos_txt = [
                    nome
                    for nome in sorted(zf.namelist())
                    if nome.lower().endswith(".txt") and not nome.startswith("__MACOSX")
                ]

                if not arquivos_txt:
                    return False, "Nenhum .txt encontrado no ZIP", []

                for nome in arquivos_txt:
                    conteudo = zf.read(nome).decode("utf-8", errors="replace")
                    conteudo_total.append(conteudo)
                    arquivos_lidos.append(nome)

        except zipfile.BadZipFile:
            return False, "Arquivo ZIP corrompido", []

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

    texto_final = "\n".join(conteudo_total)
    return True, texto_final, arquivos_lidos


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
    Separa so as linhas com comando.

    Comentario simples e linha vazia nao entram na conta.
    """

    linhas_validas = []

    for numero_linha, linha in enumerate(conteudo.splitlines(), start=1):
        linha_limpa = linha.strip()

        if not linha_limpa:
            continue

        if linha_limpa.startswith("//"):
            continue

        linhas_validas.append((numero_linha, linha_limpa))

    return linhas_validas


def dividir_argumentos_principais(argumentos: str) -> list[str]:
    """
    Separa filtro e update sem quebrar nas virgulas internas.

    Exemplo:
    {"a": 1, "b": 2}, {$set: {"c": 3}}

    Aqui a virgula que interessa e so a que separa os dois argumentos.
    """

    partes = []
    atual = []
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

    ultima_parte = "".join(atual).strip()

    if ultima_parte:
        partes.append(ultima_parte)

    return partes


def normalizar_update(update_texto: str) -> str:
    """
    O lote chega no estilo do shell MongoDB: {$set: {...}}

    O json.loads so aceita a chave com aspas.
    Como o contrato do lote e fixo, aqui fazemos apenas essa adaptacao.
    """

    if not update_texto.startswith("{$set:"):
        raise ValueError("O update precisa comecar com {$set: ...}.")

    return update_texto.replace("{$set:", '{"$set":', 1)


def validar_estrutura(filtro: dict, atualizacao: dict, numero_linha: int, arquivo: str) -> None:
    """
    Garante que a linha esta exatamente no contrato combinado.

    A sustentacao nao deve adivinhar outro formato.
    Se vier diferente, o certo e devolver para o desenvolvimento ajustar.
    """

    if set(filtro.keys()) != CHAVES_FILTRO:
        raise ValueError(
            f"Linha {numero_linha} do arquivo {arquivo} fora do padrao esperado. "
            f"Use exatamente: {FORMATO_EXEMPLO}"
        )

    if filtro["document.flProForma"] is not False:
        raise ValueError(
            f"Linha {numero_linha} do arquivo {arquivo} deve manter "
            '"document.flProForma": false.'
        )

    if set(atualizacao.keys()) != {"$set"}:
        raise ValueError(
            f"Linha {numero_linha} do arquivo {arquivo} deve usar somente $set."
        )

    if not isinstance(atualizacao["$set"], dict):
        raise ValueError(
            f"Linha {numero_linha} do arquivo {arquivo} precisa ter um objeto dentro de $set."
        )

    if set(atualizacao["$set"].keys()) != CHAVES_SET:
        raise ValueError(
            f"Linha {numero_linha} do arquivo {arquivo} deve atualizar somente "
            '"customer.accountNumber".'
        )


def parsear_linha(numero_linha: int, linha: str, arquivo: str) -> ComandoDocumento:
    """
    Traduz uma linha pronta do shell para o formato que o PyMongo aceita.

    O PyMongo nao executa o texto inteiro do comando.
    Ele precisa receber:
    - um dict para o filtro
    - um dict para o update
    """

    if not linha.startswith(COMANDO_PREFIXO) or not linha.endswith(COMANDO_SUFIXO):
        raise ValueError(
            f"Linha {numero_linha} do arquivo {arquivo} fora do formato suportado. "
            f"Use exatamente: {FORMATO_EXEMPLO}"
        )

    argumentos_brutos = linha[len(COMANDO_PREFIXO) : -len(COMANDO_SUFIXO)]
    argumentos = dividir_argumentos_principais(argumentos_brutos)

    if len(argumentos) != 2:
        raise ValueError(
            f"Linha {numero_linha} do arquivo {arquivo} deve ter exatamente 2 argumentos."
        )

    try:
        filtro = json.loads(argumentos[0])
    except json.JSONDecodeError as erro:
        raise ValueError(
            f"Filtro invalido na linha {numero_linha} do arquivo {arquivo}: {erro}"
        ) from erro

    try:
        atualizacao = json.loads(normalizar_update(argumentos[1]))
    except json.JSONDecodeError as erro:
        raise ValueError(
            f"Update invalido na linha {numero_linha} do arquivo {arquivo}: {erro}"
        ) from erro

    validar_estrutura(filtro, atualizacao, numero_linha, arquivo)

    return ComandoDocumento(
        arquivo=arquivo,
        linha=numero_linha,
        texto_original=linha,
        filtro=filtro,
        atualizacao=atualizacao,
    )


def preparar_comandos(conteudo: str, arquivos: list[str]) -> list[ComandoDocumento]:
    """
    Parseia tudo antes de abrir a execucao no banco.

    Assim, se uma linha vier quebrada, a falha acontece cedo
    e o operador ve exatamente onde esta o problema.
    """

    comandos = []
    arquivo_corrente = arquivos[0] if len(arquivos) == 1 else "lote"

    for numero_linha, linha in obter_linhas_comando(conteudo):
        comandos.append(parsear_linha(numero_linha, linha, arquivo_corrente))

    return comandos


def executar(conteudo: str, arquivos: list[str]):
    """
    Executa o lote no MongoDB usando PyMongo.

    O fluxo continua simples:
    - ler o lote
    - validar o formato
    - conectar
    - rodar update_many linha por linha
    """

    print("\n" + "=" * 60)
    print("EXECUTANDO NO MONGODB VIA PYMONGO")
    print("=" * 60)

    try:
        comandos = preparar_comandos(conteudo, arquivos)
    except ValueError as erro:
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
        colecao = db[COLECAO_ALVO]
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
        print(f"[INFO] Colecao: {COLECAO_ALVO}")
        print("[INFO] Executando comandos...\n")

        for comando in comandos:
            try:
                resultado = colecao.update_many(comando.filtro, comando.atualizacao)
            except PyMongoError as erro:
                msg = f"Erro ao executar linha {comando.linha}: {erro}"
                print(f"\n[ERRO] {msg}")
                return False, msg

            total_sucesso += 1
            total_matched += resultado.matched_count
            total_modified += resultado.modified_count

            print(
                f"[OK] Linha {comando.linha} | "
                f"document.updateMany | "
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
    """Menu interativo principal, no mesmo estilo da V1."""

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

    linhas = [
        linha
        for linha in conteudo.split("\n")
        if linha.strip() and not linha.strip().startswith("//")
    ]
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
