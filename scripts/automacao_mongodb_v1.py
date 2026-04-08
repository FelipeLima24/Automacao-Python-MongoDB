"""
AUTOMACAO MONGODB V1.0 - MVP

PROCESSO ATUAL:
- Desenvolvimento envia .zip com .txt
- Cada .txt contem comandos MongoDB prontos
- Sustentacao apenas EXECUTA, nao valida nem corrige

ESTE SCRIPT:
1. Pergunta caminho do arquivo (.zip ou .txt)
2. Pergunta: simular ou executar?
3. Se simular: mostra comandos na tela
4. Se executar: roda no MongoDB via mongosh

PARA EXECUTAR DE VERDADE:
- A maquina precisa ter o mongosh instalado

SE O ARQUIVO VIER QUEBRADO: Devolva ao desenvolvimento.

**Mais informações no arquivo: DOCUMENTACAO_TECNICA.txt**
"""

import os
import subprocess
import tempfile
import zipfile
from datetime import datetime

# Configuracao fixa do MVP.
# Se precisar apontar para outro ambiente, ajuste.
MONGODB_URI = "mongodb://localhost:27017"
MONGODB_DATABASE = "smartbill"

MONGOSH_PATH = r"C:\Users\TheRe\AppData\Local\Programs\mongosh\mongosh.exe"


def ler_arquivo(caminho):
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
        except Exception as e:
            return False, f"Erro ao ler arquivo: {e}", []

    else:
        return False, "Formato nao suportado. Use .zip ou .txt", []

    # Junta tudo em um unico bloco para a simulacao e a execucao.
    texto_final = "\n".join(conteudo_total)
    return True, texto_final, arquivos_lidos


def simular(conteudo, arquivos):
    """Mostra o lote na tela sem alterar o banco."""

    print("\n" + "=" * 60)
    print("SIMULACAO - Nada sera executado no banco")
    print("=" * 60)
    print(f"Arquivos do lote: {', '.join(arquivos)}")
    print(f"Banco alvo: {MONGODB_DATABASE}")
    print("-" * 60)
    print("\nCOMANDOS QUE SERAO EXECUTADOS:\n")
    print(conteudo)
    print("\n" + "-" * 60)
    print("FIM DA SIMULACAO")
    print("=" * 60)


def executar(conteudo):
    """
    Executa os comandos no MongoDB via mongosh.
    Retorna tupla: (sucesso, mensagem)
    """

    print("\n" + "=" * 60)
    print("EXECUTANDO NO MONGODB")
    print("=" * 60)

    # O Python so prepara o lote; quem interpreta de verdade e o mongosh.
    script = f"use {MONGODB_DATABASE};\n{conteudo}"

    # O arquivo temporario evita montar um comando gigante no terminal.
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".js",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        tmp.write(script)
        arquivo_temp = tmp.name

    try:
        print(f"[INFO] Conectando em: {MONGODB_URI}")
        print(f"[INFO] Banco: {MONGODB_DATABASE}")
        print("[INFO] Executando comandos...\n")

        # Passa o arquivo temporario para o mongosh executar o lote.
        resultado = subprocess.run(
            [MONGOSH_PATH, MONGODB_URI, "--file", arquivo_temp],
            capture_output=True,
            text=True,
            timeout=300,
        )

        # Saídas
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

        print(f"\n[ERRO] Codigo de retorno: {resultado.returncode}")
        return False, f"Erro na execucao (codigo {resultado.returncode})"

    # Se cair aqui, normalmente o shell nao esta instalado ou nao esta no PATH.
    except FileNotFoundError:
        msg = "mongosh nao encontrado. Instale o MongoDB Shell."
        print(f"\n[ERRO] {msg}")
        print("Download: https://www.mongodb.com/try/download/shell")
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
        # Limpa o temporario mesmo se a execucao falhar.
        if os.path.exists(arquivo_temp):
            os.remove(arquivo_temp)


def menu():
    """Menu interativo principal."""

    print("\n" + "=" * 60)
    print("AUTOMACAO MONGODB V1.0 - SUSTENTACAO B2C")
    print("=" * 60)
    print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"Banco: {MONGODB_DATABASE}")
    print("=" * 60)

    # Primeiro escolhemos qual lote sera lido.
    print("\n[1] Informe o caminho do arquivo (.zip ou .txt)")
    print("    Exemplo: C:\\lotes\\abril.zip")
    print("    Exemplo: ./comandos.txt\n")

    caminho = input("Arquivo: ").strip().strip('"').strip("'")

    if not caminho:
        print("\n[ERRO] Caminho vazio. Saindo.")
        return

    # O script so le o lote; nao tenta validar a regra de negocio.
    sucesso, conteudo, arquivos = ler_arquivo(caminho)

    if not sucesso:
        print(f"\n[ERRO] {conteudo}")
        return

    print(f"\n[OK] Arquivo(s) lido(s): {', '.join(arquivos)}")

    # Conta apenas linhas com conteudo para dar uma nocao rapida do tamanho do lote.
    linhas = [linha for linha in conteudo.split("\n") if linha.strip()]
    print(f"[OK] {len(linhas)} linha(s) de comando encontrada(s)")

    # A partir daqui o usuario escolhe se quer so revisar ou executar.
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

        # Depois da simulacao, ainda existe uma segunda confirmacao.
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
        print("\n[ATENCAO] Os comandos serao executados DIRETO no banco!")
        print("          Acao NAO pode ser desfeita automaticamente.")
        print("          Recomendamos simular primeiro.\n")

        confirma = input("Digite EXECUTAR para confirmar: ").strip()

        if confirma == "EXECUTAR":
            executar(conteudo)
        elif confirma == "executar":
            executar(conteudo)
        elif confirma.lower() in {"sim", "s"}:
            executar(conteudo)
        else:
            print("\nCancelado.")

    else:
        print("\n[ERRO] Opcao invalida.")


if __name__ == "__main__":
    menu()
    print("\n[FIM]\n")
