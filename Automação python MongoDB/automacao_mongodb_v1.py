# -*- coding: utf-8 -*-
"""
================================================================================
AUTOMACAO MONGODB V1.0 - MVP SIMPLIFICADO
================================================================================

PROCESSO ATUAL:
- Desenvolvimento envia .zip com .txt
- Cada .txt contem comandos MongoDB prontos
- Sustentacao apenas EXECUTA, nao valida nem corrige

ESTE SCRIPT:
1. Pergunta caminho do arquivo (.zip ou .txt)
2. Pergunta: simular ou executar?
3. Se simular: mostra comandos na tela
4. Se executar: roda no MongoDB via mongosh

SE O ARQUIVO VIER QUEBRADO: Devolva ao desenvolvimento.

================================================================================
"""

import os
import subprocess
import tempfile
import zipfile
from datetime import datetime

# ================================================================================
# CONFIGURACAO
# ================================================================================

MONGODB_URI = "mongodb://localhost:27017"
MONGODB_DATABASE = "smartbill"


# ================================================================================
# FUNCAO: LER ARQUIVO DE ENTRADA
# ================================================================================
# Abre .zip ou .txt e retorna o conteudo completo dos comandos.
# Nao faz nenhuma validacao do conteudo - apenas le.

def ler_arquivo(caminho):
    """
    Le arquivo .zip ou .txt e retorna conteudo dos comandos.
    Retorna tupla: (sucesso, conteudo_ou_erro, lista_arquivos)
    """

    if not os.path.exists(caminho):
        return False, f"Arquivo nao encontrado: {caminho}", []

    conteudo_total = []
    arquivos_lidos = []

    # CASO 1: Arquivo ZIP
    if caminho.lower().endswith(".zip"):
        try:
            with zipfile.ZipFile(caminho, "r") as zf:
                # Pega todos os .txt (ignora pastas do Mac)
                arquivos_txt = [
                    n for n in sorted(zf.namelist())
                    if n.lower().endswith(".txt") and not n.startswith("__MACOSX")
                ]

                if not arquivos_txt:
                    return False, "Nenhum .txt encontrado no ZIP", []

                for nome in arquivos_txt:
                    conteudo = zf.read(nome).decode("utf-8", errors="replace")
                    conteudo_total.append(conteudo)
                    arquivos_lidos.append(nome)

        except zipfile.BadZipFile:
            return False, "Arquivo ZIP corrompido", []

    # CASO 2: Arquivo TXT
    elif caminho.lower().endswith(".txt"):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                conteudo = f.read()
            conteudo_total.append(conteudo)
            arquivos_lidos.append(os.path.basename(caminho))
        except Exception as e:
            return False, f"Erro ao ler arquivo: {e}", []

    else:
        return False, "Formato nao suportado. Use .zip ou .txt", []

    # Junta tudo com quebra de linha
    texto_final = "\n".join(conteudo_total)
    return True, texto_final, arquivos_lidos


# ================================================================================
# FUNCAO: SIMULAR
# ================================================================================
# Mostra na tela o que seria executado. Nao toca no banco.

def simular(conteudo, arquivos):
    """
    Mostra os comandos que seriam executados.
    """
    print("\n" + "=" * 60)
    print("SIMULACAO - Nada sera executado no banco")
    print("=" * 60)
    print(f"Arquivos: {', '.join(arquivos)}")
    print(f"Banco alvo: {MONGODB_DATABASE}")
    print("-" * 60)
    print("\nCOMANDOS QUE SERAO EXECUTADOS:\n")
    print(conteudo)
    print("\n" + "-" * 60)
    print("FIM DA SIMULACAO")
    print("=" * 60)


# ================================================================================
# FUNCAO: EXECUTAR
# ================================================================================
# Executa os comandos no MongoDB usando mongosh via subprocess.
# Mongosh ja interpreta os comandos nativamente - nao precisamos parsear nada.

def executar(conteudo):
    """
    Executa os comandos no MongoDB via mongosh.
    Retorna tupla: (sucesso, mensagem)
    """

    print("\n" + "=" * 60)
    print("EXECUTANDO NO MONGODB")
    print("=" * 60)

    # Monta o script que sera executado pelo mongosh
    # Inclui o "use smartbill" no inicio
    script = f"use {MONGODB_DATABASE};\n{conteudo}"

    # Salva em arquivo temporario
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".js",
        delete=False,
        encoding="utf-8"
    ) as tmp:
        tmp.write(script)
        arquivo_temp = tmp.name

    try:
        print(f"[INFO] Conectando em: {MONGODB_URI}")
        print(f"[INFO] Banco: {MONGODB_DATABASE}")
        print("[INFO] Executando comandos...\n")

        # Chama mongosh passando o arquivo de script
        resultado = subprocess.run(
            ["mongosh", MONGODB_URI, "--file", arquivo_temp],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutos de timeout
        )

        # Mostra saida
        if resultado.stdout:
            print("SAIDA DO MONGODB:")
            print("-" * 40)
            print(resultado.stdout)

        if resultado.stderr:
            print("ERROS/AVISOS:")
            print("-" * 40)
            print(resultado.stderr)

        if resultado.returncode == 0:
            print("\n[OK] Execucao concluida com sucesso!")
            return True, "Sucesso"
        else:
            print(f"\n[ERRO] Codigo de retorno: {resultado.returncode}")
            return False, f"Erro na execucao (codigo {resultado.returncode})"

    except FileNotFoundError:
        msg = "mongosh nao encontrado. Instale o MongoDB Shell."
        print(f"\n[ERRO] {msg}")
        print("       Download: https://www.mongodb.com/try/download/shell")
        return False, msg

    except subprocess.TimeoutExpired:
        msg = "Timeout - execucao demorou mais de 5 minutos"
        print(f"\n[ERRO] {msg}")
        return False, msg

    except Exception as e:
        msg = f"Erro inesperado: {e}"
        print(f"\n[ERRO] {msg}")
        return False, msg

    finally:
        # Remove arquivo temporario
        if os.path.exists(arquivo_temp):
            os.remove(arquivo_temp)


# ================================================================================
# FUNCAO: MENU PRINCIPAL
# ================================================================================
# Interface interativa simples.

def menu():
    """
    Menu interativo principal.
    """

    print("\n" + "=" * 60)
    print("AUTOMACAO MONGODB V1.0 - SUSTENTACAO B2C")
    print("=" * 60)
    print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"Banco: {MONGODB_DATABASE}")
    print("=" * 60)

    # PASSO 1: Pedir arquivo
    print("\n[1] Informe o caminho do arquivo (.zip ou .txt)")
    print("    Exemplo: C:\\lotes\\abril.zip")
    print("    Exemplo: ./comandos.txt\n")

    caminho = input("Arquivo: ").strip().strip('"').strip("'")

    if not caminho:
        print("\n[ERRO] Caminho vazio. Saindo.")
        return

    # PASSO 2: Ler arquivo
    sucesso, conteudo, arquivos = ler_arquivo(caminho)

    if not sucesso:
        print(f"\n[ERRO] {conteudo}")
        return

    print(f"\n[OK] Arquivo lido: {', '.join(arquivos)}")

    # Conta linhas nao vazias (so pra informar)
    linhas = [l for l in conteudo.split("\n") if l.strip()]
    print(f"[OK] {len(linhas)} linha(s) de comando encontrada(s)")

    # PASSO 3: Escolher acao
    print("\n[2] O que deseja fazer?")
    print("    [1] Simular (ver comandos)")
    print("    [2] Executar direto")
    print("    [0] Sair\n")

    opcao = input("Opcao: ").strip()

    if opcao == "0":
        print("\nSaindo.")
        return

    if opcao == "1":
        # Simular
        simular(conteudo, arquivos)

        # Perguntar se quer executar
        print("\n[3] Deseja executar agora?")
        print("    [S] Sim")
        print("    [N] Nao\n")

        confirma = input("Executar? (S/N): ").strip().upper()

        if confirma == "S":
            print("\n[ATENCAO] Os comandos serao executados no banco!")
            print("          Acao NAO pode ser desfeita automaticamente.\n")

            confirma2 = input("Digite EXECUTAR para confirmar: ").strip()

            if confirma2 == "EXECUTAR":
                executar(conteudo)
            else:
                print("\nCancelado.")
        else:
            print("\nSimulacao encerrada. Nada foi executado.")

    elif opcao == "2":
        # Executar direto
        print("\n[ATENCAO] Os comandos serao executados DIRETO no banco!")
        print("          Acao NAO pode ser desfeita automaticamente.")
        print("          Recomendamos simular primeiro.\n")

        confirma = input("Digite EXECUTAR para confirmar: ").strip()

        if confirma == "EXECUTAR":
            executar(conteudo)
        else:
            print("\nCancelado.")

    else:
        print("\n[ERRO] Opcao invalida.")


# ================================================================================
# PONTO DE ENTRADA
# ================================================================================

if __name__ == "__main__":
    menu()
    print("\n[FIM]\n")
