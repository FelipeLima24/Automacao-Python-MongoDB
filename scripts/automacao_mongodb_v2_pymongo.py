"""
AUTOMACAO MONGODB V2.0 - EXECUCAO VIA PYMONGO

Objetivo desta versao:
- manter a experiencia simples da V1;
- continuar lendo .zip ou .txt com comandos prontos;
- simular o lote inteiro na tela;
- executar pelo proprio Python, sem depender do mongosh.

Ponto importante:
- o texto do arquivo continua vindo no formato do shell MongoDB;
- para o PyMongo executar, o Python precisa extrair o minimo necessario
  de cada linha: collection, metodo, filtro e update.
- isso nao significa "validar regra de negocio"; significa apenas
  transformar a linha em algo que o driver Python consiga executar.
"""

from __future__ import annotations

import json
import os
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime

from pymongo import MongoClient
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError

# Configuracao fixa, espelhando o estilo simples da V1.
MONGODB_URI = "mongodb://localhost:27017"
MONGODB_DATABASE = "smartbill"

# Aceitamos apenas os dois updates usados no processo.
COMANDO_PATTERN = re.compile(
    r"^\s*db\.(?P<colecao>[A-Za-z_][A-Za-z0-9_]*)\.(?P<metodo>updateOne|updateMany)\s*\((?P<argumentos>.*)\)\s*;\s*$"
)


@dataclass
class ComandoMongo:
    """
    Estrutura minima para o Python executar o comando.

    Analogia com Java:
    - pense nesta classe como um objeto simples de transporte de dados;
    - ela guarda o que foi lido do arquivo ja separado em partes.
    """

    arquivo: str
    linha: int
    texto_original: str
    colecao: str
    metodo: str
    filtro: dict
    atualizacao: dict | list


def ler_arquivo(caminho: str):
    """
    Le arquivo .zip ou .txt e retorna conteudo dos comandos.
    Retorna tupla: (sucesso, conteudo_ou_erro, lista_arquivos)
    """

    if not os.path.exists(caminho):
        return False, f"Arquivo nao encontrado: {caminho}", []

    conteudo_total = []
    arquivos_lidos = []

    # No ZIP, junta todos os .txt na ordem do nome para manter o lote previsivel.
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

    # Se vier um .txt solto, le exatamente esse arquivo.
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

    # Junta tudo em um unico bloco, igual a V1, para facilitar simulacao.
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
    Separa apenas as linhas que realmente parecem comandos.

    Linhas vazias e comentarios simples sao ignorados.
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


def dividir_argumentos(argumentos: str) -> list[str]:
    """
    Divide os argumentos principais do update sem quebrar JSON interno.

    Exemplo de entrada:
    { ... }, { $set: { ... } }
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


def normalizar_json_mongo(texto: str) -> str:
    """
    Faz o minimo ajuste para o texto do shell virar JSON valido.

    Exemplo:
    { $set: { "campo": "valor" } }
    vira:
    { "$set": { "campo": "valor" } }
    """

    return re.sub(r'([{,]\s*)(\$[A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', texto)


def parsear_linha(numero_linha: int, linha: str, arquivo: str) -> ComandoMongo:
    """
    Converte uma linha do arquivo em um comando que o PyMongo entende.

    Este e o ponto central da V2.
    O arquivo chega como texto do shell MongoDB, mas o PyMongo precisa
    receber objetos Python equivalentes.
    """

    match = COMANDO_PATTERN.match(linha)
    if not match:
        raise ValueError(
            f"Linha {numero_linha} do arquivo {arquivo} nao esta em formato suportado."
        )

    colecao = match.group("colecao")
    metodo = match.group("metodo")
    argumentos_brutos = match.group("argumentos").strip()
    argumentos = dividir_argumentos(argumentos_brutos)

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
        atualizacao = json.loads(normalizar_json_mongo(argumentos[1]))
    except json.JSONDecodeError as erro:
        raise ValueError(
            f"Update invalido na linha {numero_linha} do arquivo {arquivo}: {erro}"
        ) from erro

    return ComandoMongo(
        arquivo=arquivo,
        linha=numero_linha,
        texto_original=linha,
        colecao=colecao,
        metodo=metodo,
        filtro=filtro,
        atualizacao=atualizacao,
    )


def preparar_comandos(conteudo: str, arquivos: list[str]) -> list[ComandoMongo]:
    """
    Parseia todas as linhas do lote antes da execucao.

    Aqui ainda nao mexemos no banco.
    A ideia e falhar cedo se algum comando estiver fora do formato combinado.
    """

    comandos = []
    arquivo_corrente = arquivos[0] if len(arquivos) == 1 else "lote"

    for numero_linha, linha in obter_linhas_comando(conteudo):
        comandos.append(parsear_linha(numero_linha, linha, arquivo_corrente))

    return comandos


def executar(conteudo: str, arquivos: list[str]):
    """
    Executa os comandos no MongoDB usando PyMongo.
    Retorna tupla: (sucesso, mensagem)

    Diferenca para a V1:
    - V1 entrega um arquivo .js para o mongosh;
    - V2 abre a conexao direto no Python e chama update_one/update_many.

    Equivalente ao `use smartbill` do shell:
    - no PyMongo fazemos `client[MONGODB_DATABASE]`.
    """

    print("\n" + "=" * 60)
    print("EXECUTANDO NO MONGODB VIA PYMONGO")
    print("=" * 60)

    try:
        comandos = preparar_comandos(conteudo, arquivos)
    except ValueError as erro:
        return False, str(erro)

    try:
        client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
        )
        client.admin.command("ping")
        db = client[MONGODB_DATABASE]
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
        print("[INFO] Executando comandos...\n")

        for comando in comandos:
            colecao = db[comando.colecao]

            try:
                if comando.metodo == "updateMany":
                    resultado = colecao.update_many(comando.filtro, comando.atualizacao)
                else:
                    resultado = colecao.update_one(comando.filtro, comando.atualizacao)
            except PyMongoError as erro:
                msg = (
                    f"Erro ao executar linha {comando.linha} "
                    f"({comando.colecao}.{comando.metodo}): {erro}"
                )
                print(f"\n[ERRO] {msg}")
                return False, msg

            total_sucesso += 1
            total_matched += resultado.matched_count
            total_modified += resultado.modified_count

            print(
                f"[OK] Linha {comando.linha} | "
                f"{comando.colecao}.{comando.metodo} | "
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
    """Menu interativo principal da V2, espelhando o fluxo da V1."""

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

    linhas = [linha for linha in conteudo.split("\n") if linha.strip() and not linha.strip().startswith("//")]
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
