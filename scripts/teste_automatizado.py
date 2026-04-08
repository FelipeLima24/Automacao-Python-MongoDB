"""
Script auxiliar para execucao automatizada de testes.
Executa o script principal sem interacao manual.
"""

import os
import subprocess
import tempfile
import zipfile

# Configuracao
MONGODB_URI = "mongodb://localhost:27017"
MONGODB_DATABASE = "smartbill"
MONGOSH_PATH = r"C:\Users\TheRe\AppData\Local\Programs\mongosh\mongosh.exe"

def ler_arquivo_zip(caminho):
    """Le arquivo .zip e retorna conteudo dos comandos."""

    conteudo_total = []
    arquivos_lidos = []

    with zipfile.ZipFile(caminho, "r") as zf:
        arquivos_txt = [
            nome
            for nome in sorted(zf.namelist())
            if nome.lower().endswith(".txt") and not nome.startswith("__MACOSX")
        ]

        for nome in arquivos_txt:
            conteudo = zf.read(nome).decode("utf-8", errors="replace")
            conteudo_total.append(conteudo)
            arquivos_lidos.append(nome)

    return "\n".join(conteudo_total), arquivos_lidos


def executar_mongodb(conteudo):
    """Executa os comandos no MongoDB via mongosh."""

    print("\n" + "=" * 60)
    print("EXECUTANDO NO MONGODB - MODO AUTOMATIZADO")
    print("=" * 60)

    script = f"use {MONGODB_DATABASE};\n{conteudo}"

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

        resultado = subprocess.run(
            [MONGOSH_PATH, MONGODB_URI, "--file", arquivo_temp],
            capture_output=True,
            text=True,
            timeout=300,
        )

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
            return True

        print(f"\n[ERRO] Codigo de retorno: {resultado.returncode}")
        return False

    except Exception as e:
        print(f"\n[ERRO] {e}")
        return False

    finally:
        if os.path.exists(arquivo_temp):
            os.remove(arquivo_temp)


if __name__ == "__main__":
    import sys
    from datetime import datetime

    print("\n" + "=" * 60)
    print("TESTE AUTOMATIZADO - SUSTENTACAO B2C")
    print("=" * 60)
    print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"Banco: {MONGODB_DATABASE}")
    print("=" * 60)

    # Caminho do arquivo ZIP
    caminho_zip = r"c:\Users\TheRe\OneDrive\Documentos\Automacao-Python-MongoDB\testes\lotes\lote_sustentacao_abril_2026.zip"

    print(f"\n[INFO] Lendo arquivo: {caminho_zip}")

    conteudo, arquivos = ler_arquivo_zip(caminho_zip)

    print(f"[OK] Arquivos lidos: {', '.join(arquivos)}")

    linhas = [linha for linha in conteudo.split("\n") if linha.strip() and linha.strip().startswith("db.")]
    print(f"[OK] {len(linhas)} comandos MongoDB encontrados")

    print("\n[INFO] Iniciando execucao real no banco...")

    sucesso = executar_mongodb(conteudo)

    print("\n" + "=" * 60)
    if sucesso:
        print("RESULTADO: SUCESSO")
    else:
        print("RESULTADO: FALHA")
    print("=" * 60)

    sys.exit(0 if sucesso else 1)
