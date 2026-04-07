#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de teste para automacao_mongodb_v1.py

Valida:
- Leitura de arquivo .txt
- Leitura de arquivo .zip
- Funcao de simulacao
- Funcoes essenciais
"""

import sys
import os
import zipfile
import tempfile
from pathlib import Path

# Adiciona o diretorio atual ao path
sys.path.insert(0, os.path.dirname(__file__))

# Importa as funcoes do script V1
from automacao_mongodb_v1 import ler_arquivo, simular

def test_ler_txt():
    """Testa leitura de arquivo .txt"""
    print("\n[TESTE 1] Leitura de arquivo .txt")
    print("-" * 50)

    # Usa o arquivo de exemplo que existe
    caminho = "queries_exemplo.txt"

    if not os.path.exists(caminho):
        print(f"[ERRO] Arquivo {caminho} nao encontrado!")
        return False

    sucesso, conteudo, arquivos = ler_arquivo(caminho)

    if not sucesso:
        print(f"[ERRO] {conteudo}")
        return False

    print(f"[OK] Arquivo lido com sucesso")
    print(f"[OK] Arquivos: {arquivos}")
    print(f"[OK] Linhas de comando: {len(conteudo.split(chr(10)))}")
    print(f"[OK] Primeiras 100 caracteres:\n{conteudo[:100]}...")

    return True


def test_ler_zip():
    """Testa leitura de arquivo .zip"""
    print("\n[TESTE 2] Leitura de arquivo .zip")
    print("-" * 50)

    caminho = "lote_exemplo.zip"

    if not os.path.exists(caminho):
        print(f"[ERRO] Arquivo {caminho} nao encontrado!")
        return False

    sucesso, conteudo, arquivos = ler_arquivo(caminho)

    if not sucesso:
        print(f"[ERRO] {conteudo}")
        return False

    print(f"[OK] ZIP lido com sucesso")
    print(f"[OK] Arquivos encontrados: {arquivos}")
    print(f"[OK] Total de linhas: {len(conteudo.split(chr(10)))}")

    return True


def test_simular():
    """Testa funcao simular"""
    print("\n[TESTE 3] Funcao simular()")
    print("-" * 50)

    caminho = "queries_exemplo.txt"
    sucesso, conteudo, arquivos = ler_arquivo(caminho)

    if not sucesso:
        print(f"[ERRO] Nao conseguiu ler arquivo para simular")
        return False

    print("[OK] Conteudo carregado, chamando simular()...\n")

    try:
        simular(conteudo, arquivos)
        print("\n[OK] Funcao simular() executada sem erros")
        return True
    except Exception as e:
        print(f"[ERRO] Erro ao chamar simular(): {e}")
        return False


def test_arquivo_invalido():
    """Testa comportamento com arquivo invalido"""
    print("\n[TESTE 4] Comportamento com arquivo invalido")
    print("-" * 50)

    sucesso, conteudo, _ = ler_arquivo("/arquivo/nao/existe.txt")

    if sucesso:
        print("[ERRO] Deveria retornar False para arquivo invalido")
        return False

    print(f"[OK] Retornou corretamente: {conteudo}")
    return True


def test_zip_invalido():
    """Testa comportamento com ZIP invalido"""
    print("\n[TESTE 5] Comportamento com ZIP invalido")
    print("-" * 50)

    # Cria arquivo temporario com conteudo invalido
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(b"nao e um zip valido")
        tmp_path = tmp.name

    try:
        sucesso, conteudo, _ = ler_arquivo(tmp_path)

        if sucesso:
            print("[ERRO] Deveria retornar False para ZIP invalido")
            return False

        print(f"[OK] Retornou corretamente: {conteudo}")
        return True
    finally:
        os.unlink(tmp_path)


def test_importacao():
    """Testa se o modulo importa sem erros"""
    print("\n[TESTE 0] Importacao do modulo")
    print("-" * 50)

    try:
        import automacao_mongodb_v1
        print("[OK] Modulo importado com sucesso")
        print(f"[OK] Funcoes disponiveis:")
        print(f"    - ler_arquivo")
        print(f"    - simular")
        print(f"    - executar")
        print(f"    - menu")
        return True
    except Exception as e:
        print(f"[ERRO] Erro ao importar: {e}")
        return False


def main():
    """Executa todos os testes"""
    print("\n" + "=" * 70)
    print("TESTE DE FUNCIONALIDADE - automacao_mongodb_v1.py")
    print("=" * 70)

    testes = [
        test_importacao,
        test_ler_txt,
        test_ler_zip,
        test_simular,
        test_arquivo_invalido,
        test_zip_invalido,
    ]

    resultados = []
    for teste in testes:
        try:
            resultado = teste()
            resultados.append((teste.__name__, resultado))
        except Exception as e:
            print(f"\n[ERRO CRITICO] {teste.__name__}: {e}")
            resultados.append((teste.__name__, False))

    # Resumo
    print("\n" + "=" * 70)
    print("RESUMO DOS TESTES")
    print("=" * 70)

    total = len(resultados)
    passou = sum(1 for _, r in resultados if r)
    falhou = total - passou

    for nome, resultado in resultados:
        status = "[PASSOU]" if resultado else "[FALHOU]"
        print(f"{status} {nome}")

    print("-" * 70)
    print(f"Total: {total} | Passou: {passou} | Falhou: {falhou}")

    if falhou == 0:
        print("\n[SUCESSO] Todos os testes passaram! Script esta funcional.")
        return 0
    else:
        print(f"\n[ERRO] {falhou} teste(s) falharam.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    print("\n")
    sys.exit(exit_code)
