"""
AUTOMACAO MONGODB V2.0 - EXEMPLO COM PYMONGO

Objetivo desta versao:
- mostrar como ficaria uma automacao conectando direto pelo Python;
- comparar com a V1, que delega a execucao para o mongosh;
- manter o exemplo didatico e simples.

Diferenca principal para a V1:
- V1: Python le o lote e chama o mongosh;
- V2: Python le o lote, interpreta as linhas suportadas e executa usando PyMongo.

Limitacoes desta V2:
- aceita apenas updateOne e updateMany;
- espera argumentos em JSON/EJSON estrito;
- nao tenta interpretar qualquer sintaxe livre de JavaScript do shell.
"""

from __future__ import annotations

import os
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from bson import json_util
from pymongo import MongoClient
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError

# Configuracao fixa, igual ao MVP anterior.
MONGODB_URI = "mongodb://localhost:27017"
MONGODB_DATABASE = "smartbill"

# O regex extrai:
# - nome da collection
# - metodo (updateOne ou updateMany)
# - argumentos entre parenteses
COMMAND_PATTERN = re.compile(
    r"^\s*db\.(?P<colecao>[A-Za-z_][A-Za-z0-9_]*)\.(?P<metodo>updateOne|updateMany)\s*\((?P<argumentos>.*)\)\s*;?\s*$"
)

# Traducao do nome da option do texto para o nome esperado pelo PyMongo.
SUPPORTED_OPTION_KEYS = {
    "upsert": "upsert",
    "hint": "hint",
    "comment": "comment",
    "collation": "collation",
    "arrayFilters": "array_filters",
    "bypassDocumentValidation": "bypass_document_validation",
    "let": "let",
}


def ler_arquivo(caminho: str) -> Tuple[bool, List[Tuple[str, int, str]], List[str] | str]:
    """
    Le .zip ou .txt e devolve uma lista de linhas uteis.

    Retorno em caso de sucesso:
    - True
    - lista de tuplas (arquivo_origem, numero_linha, comando)
    - lista de arquivos lidos

    Retorno em caso de erro:
    - False
    - []
    - mensagem de erro
    """

    if not os.path.exists(caminho):
        return False, [], f"Arquivo nao encontrado: {caminho}"

    linhas_comandos: List[Tuple[str, int, str]] = []
    arquivos_lidos: List[str] = []

    if caminho.lower().endswith(".zip"):
        try:
            with zipfile.ZipFile(caminho, "r") as zf:
                arquivos_txt = [
                    nome
                    for nome in sorted(zf.namelist())
                    if nome.lower().endswith(".txt") and not nome.startswith("__MACOSX")
                ]

                if not arquivos_txt:
                    return False, [], "Nenhum .txt encontrado no ZIP"

                for nome in arquivos_txt:
                    conteudo = zf.read(nome).decode("utf-8", errors="replace")
                    arquivos_lidos.append(nome)
                    for numero_linha, linha in enumerate(conteudo.splitlines(), start=1):
                        linha_limpa = linha.strip()
                        if linha_limpa:
                            linhas_comandos.append((nome, numero_linha, linha_limpa))

        except zipfile.BadZipFile:
            return False, [], "Arquivo ZIP corrompido"

    elif caminho.lower().endswith(".txt"):
        try:
            with open(caminho, "r", encoding="utf-8") as arquivo:
                conteudo = arquivo.read()
            nome_arquivo = os.path.basename(caminho)
            arquivos_lidos.append(nome_arquivo)
            for numero_linha, linha in enumerate(conteudo.splitlines(), start=1):
                linha_limpa = linha.strip()
                if linha_limpa:
                    linhas_comandos.append((nome_arquivo, numero_linha, linha_limpa))
        except Exception as erro:  # noqa: BLE001
            return False, [], f"Erro ao ler arquivo: {erro}"

    else:
        return False, [], "Formato nao suportado. Use .zip ou .txt"

    return True, linhas_comandos, arquivos_lidos


def dividir_argumentos(argumentos: str) -> List[str]:
    """
    Divide os argumentos do comando sem quebrar JSON interno.

    Exemplo:
    updateMany({"a": 1}, {"$set": {"b": 2}}, {"upsert": false})
    """

    partes: List[str] = []
    atual: List[str] = []
    profundidade_chaves = 0
    profundidade_listas = 0
    profundidade_parenteses = 0
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
            profundidade_listas += 1
        elif caractere == "]":
            profundidade_listas -= 1
        elif caractere == "(":
            profundidade_parenteses += 1
        elif caractere == ")":
            profundidade_parenteses -= 1

        if caractere == "," and profundidade_chaves == 0 and profundidade_listas == 0 and profundidade_parenteses == 0:
            partes.append("".join(atual).strip())
            atual = []
            continue

        atual.append(caractere)

    ultima_parte = "".join(atual).strip()
    if ultima_parte:
        partes.append(ultima_parte)

    return partes


def mapear_opcoes(opcoes: Dict[str, Any]) -> Tuple[bool, Dict[str, Any] | str]:
    """Converte options do texto para kwargs aceitos pelo PyMongo."""

    chaves_invalidas = [chave for chave in opcoes if chave not in SUPPORTED_OPTION_KEYS]
    if chaves_invalidas:
        return False, f"Options nao suportadas: {', '.join(chaves_invalidas)}"

    kwargs = {SUPPORTED_OPTION_KEYS[chave]: valor for chave, valor in opcoes.items()}
    return True, kwargs


def parsear_comando(linha: str) -> Tuple[bool, Dict[str, Any] | str]:
    """
    Interpreta uma linha suportada e devolve uma estrutura de dados.

    Aqui esta a maior "dificuldade extra" em relacao a V1:
    como o Python vai executar diretamente, ele precisa entender a linha,
    e nao apenas repassar o texto para o mongosh.
    """

    match = COMMAND_PATTERN.match(linha)
    if not match:
        return False, "Linha nao esta no formato suportado"

    metodo = match.group("metodo")
    colecao = match.group("colecao")
    argumentos_brutos = match.group("argumentos").strip()
    argumentos = dividir_argumentos(argumentos_brutos)

    if len(argumentos) not in {2, 3}:
        return False, "Comando precisa ter 2 ou 3 argumentos"

    try:
        filtro = json_util.loads(argumentos[0])
        atualizacao = json_util.loads(argumentos[1])
    except Exception as erro:  # noqa: BLE001
        return False, f"Erro ao converter filter/update: {erro}"

    if not isinstance(filtro, dict):
        return False, "Filter precisa ser um objeto JSON/EJSON"

    if not isinstance(atualizacao, (dict, list)):
        return False, "Update precisa ser objeto ou pipeline"

    opcoes: Dict[str, Any] = {}
    if len(argumentos) == 3:
        try:
            opcoes = json_util.loads(argumentos[2])
        except Exception as erro:  # noqa: BLE001
            return False, f"Erro ao converter options: {erro}"
        if not isinstance(opcoes, dict):
            return False, "Options precisa ser objeto JSON/EJSON"

    sucesso_opcoes, kwargs_ou_erro = mapear_opcoes(opcoes)
    if not sucesso_opcoes:
        return False, str(kwargs_ou_erro)

    return True, {
        "colecao": colecao,
        "metodo": metodo,
        "filtro": filtro,
        "atualizacao": atualizacao,
        "kwargs": kwargs_ou_erro,
    }


def simular(linhas_comandos: List[Tuple[str, int, str]]) -> None:
    """Mostra o lote como seria processado, sem alterar dados."""

    print("\n" + "=" * 60)
    print("SIMULACAO V2 - PYMONGO")
    print("=" * 60)
    print(f"Banco alvo: {MONGODB_DATABASE}")
    print(f"Total de linhas uteis: {len(linhas_comandos)}")
    print("-" * 60)

    for arquivo, numero_linha, comando in linhas_comandos:
        print(f"[{arquivo}:{numero_linha}] {comando}")

    print("-" * 60)
    print("FIM DA SIMULACAO")
    print("=" * 60)


def executar(linhas_comandos: List[Tuple[str, int, str]]) -> Tuple[bool, str]:
    """
    Executa diretamente pelo driver PyMongo.

    Em SQL, isso seria o equivalente a abrir uma conexao com o driver
    e chamar comandos pelo proprio Python, sem usar um cliente externo.
    """

    print("\n" + "=" * 60)
    print("EXECUTANDO NO MONGODB VIA PYMONGO")
    print("=" * 60)

    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000, connectTimeoutMS=8000)
        client.admin.command("ping")
        db = client[MONGODB_DATABASE]
    except ServerSelectionTimeoutError as erro:
        return False, f"Falha ao conectar no MongoDB: {erro}"
    except PyMongoError as erro:
        return False, f"Erro ao abrir conexao MongoDB: {erro}"

    try:
        total_sucesso = 0

        for arquivo, numero_linha, linha in linhas_comandos:
            sucesso_parse, comando_ou_erro = parsear_comando(linha)
            if not sucesso_parse:
                return False, f"Erro no parsing [{arquivo}:{numero_linha}]: {comando_ou_erro}"

            comando = comando_ou_erro
            colecao = db[comando["colecao"]]
            kwargs = dict(comando["kwargs"])

            try:
                if comando["metodo"] == "updateMany":
                    resultado = colecao.update_many(comando["filtro"], comando["atualizacao"], **kwargs)
                else:
                    resultado = colecao.update_one(comando["filtro"], comando["atualizacao"], **kwargs)
            except PyMongoError as erro:
                return False, f"Erro ao executar [{arquivo}:{numero_linha}]: {erro}"

            total_sucesso += 1
            print(
                f"[OK] {arquivo}:{numero_linha} | {comando['metodo']} em {comando['colecao']} | "
                f"matched={resultado.matched_count} modified={resultado.modified_count}"
            )

        return True, f"Execucao concluida com sucesso. Linhas executadas: {total_sucesso}"
    finally:
        client.close()


def menu() -> None:
    """Menu interativo da V2."""

    print("\n" + "=" * 60)
    print("AUTOMACAO MONGODB V2.0 - PYMONGO")
    print("=" * 60)
    print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"Banco: {MONGODB_DATABASE}")
    print("=" * 60)
    print("OBSERVACAO: esta versao executa direto pelo Python.")
    print("Ela exige um formato de linha mais controlado do que a V1.\n")

    caminho = input("Arquivo (.zip ou .txt): ").strip().strip('"').strip("'")
    if not caminho:
        print("\n[ERRO] Caminho vazio.")
        return

    sucesso, linhas_comandos, arquivos_ou_erro = ler_arquivo(caminho)
    if not sucesso:
        print(f"\n[ERRO] {arquivos_ou_erro}")
        return

    arquivos = arquivos_ou_erro
    print(f"\n[OK] Arquivo(s) lido(s): {', '.join(arquivos)}")
    print(f"[OK] {len(linhas_comandos)} linha(s) util(eis) encontrada(s)")

    print("\n[1] Simular")
    print("[2] Executar direto")
    print("[0] Sair\n")

    opcao = input("Opcao: ").strip()
    if opcao == "0":
        print("\nSaindo.")
        return

    if opcao == "1":
        simular(linhas_comandos)
        confirma = input("\nDeseja executar agora? Digite EXECUTAR: ").strip()
        if confirma == "EXECUTAR":
            sucesso_execucao, mensagem = executar(linhas_comandos)
            print(f"\n{'[OK]' if sucesso_execucao else '[ERRO]'} {mensagem}")
        else:
            print("\nCancelado.")
    elif opcao == "2":
        confirma = input("\nDigite EXECUTAR para confirmar: ").strip()
        if confirma == "EXECUTAR":
            sucesso_execucao, mensagem = executar(linhas_comandos)
            print(f"\n{'[OK]' if sucesso_execucao else '[ERRO]'} {mensagem}")
        else:
            print("\nCancelado.")
    else:
        print("\n[ERRO] Opcao invalida.")


if __name__ == "__main__":
    menu()
    print("\n[FIM]\n")
