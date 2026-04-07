#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Teste de fluxo interativo para automacao_mongodb_v1.py

Simula o usuario interagindo com o menu.
"""

import sys
import os

# Adiciona ao path
sys.path.insert(0, os.path.dirname(__file__))

def test_fluxo_simulacao():
    """Testa o fluxo: seleionar arquivo -> simular -> sair"""
    print("\n[TESTE FLUXO] Menu interativo - Simulacao")
    print("-" * 60)

    # Simula entrada do usuario
    inputs = [
        "queries_exemplo.txt",  # Arquivo
        "1",                     # Simular
        "N",                     # Nao executar
    ]

    import io
    from unittest.mock import patch

    # Salva stdin original
    original_stdin = sys.stdin

    try:
        # Substitui input pela lista de respostas
        sys.stdin = io.StringIO("\n".join(inputs))

        # Importa menu
        from automacao_mongodb_v1 import menu

        print("[INFO] Simulando menu com entradas:")
        for i, inp in enumerate(inputs, 1):
            print(f"       {i}. {inp}")

        print("\n[INFO] Executando menu()...\n")

        # Executa menu
        menu()

        print("\n[OK] Menu executado sem erros!")
        return True

    except Exception as e:
        print(f"\n[ERRO] {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Restaura stdin
        sys.stdin = original_stdin


def test_estrutura_projeto():
    """Verifica estrutura de arquivos do projeto"""
    print("\n[TESTE] Estrutura do projeto")
    print("-" * 60)

    arquivos_necessarios = [
        "automacao_mongodb_v1.py",
        "README.md",
        "MEMORIA_PROJETO.md",
        "GUIA_RAPIDO.txt",
        "requirements.txt",
        "lote_exemplo.zip",
        "queries_exemplo.txt",
    ]

    arquivos_antigos = [
        "automacao_mongodb.py",
        "teste_ambiente.py",
        "conteudo_pdf_apresentacao.md",
        "pytest.ini",
        ".pytest_cache",
        "__pycache__",
        "tests",
        "logs",
    ]

    print("\nVerificando arquivos necessarios:")
    todos_ok = True

    for arquivo in arquivos_necessarios:
        existe = os.path.exists(arquivo)
        status = "[OK]" if existe else "[ERRO]"
        print(f"  {status} {arquivo}")
        if not existe:
            todos_ok = False

    print("\nVerificando que arquivos antigos foram removidos:")
    nenhum_antigo = True

    for arquivo in arquivos_antigos:
        existe = os.path.exists(arquivo)
        if existe:
            print(f"  [AVISO] {arquivo} ainda existe!")
            nenhum_antigo = False
        else:
            print(f"  [OK] {arquivo} removido")

    if todos_ok and nenhum_antigo:
        print("\n[OK] Estrutura do projeto esta correta!")
        return True
    else:
        print("\n[ERRO] Problemas na estrutura do projeto!")
        return False


def main():
    print("\n" + "=" * 70)
    print("TESTE DE FLUXO - automacao_mongodb_v1.py")
    print("=" * 70)

    print("\n[TESTE 1] Estrutura do projeto")
    teste1 = test_estrutura_projeto()

    print("\n[TESTE 2] Fluxo interativo (menu)")
    teste2 = test_fluxo_simulacao()

    # Resumo
    print("\n" + "=" * 70)
    print("RESUMO")
    print("=" * 70)

    testes = [
        ("Estrutura", teste1),
        ("Menu", teste2),
    ]

    for nome, resultado in testes:
        status = "[PASSOU]" if resultado else "[FALHOU]"
        print(f"{status} {nome}")

    total = len(testes)
    passou = sum(1 for _, r in testes if r)

    print("-" * 70)
    print(f"Total: {total} | Passou: {passou}")

    if passou == total:
        print("\n[SUCESSO] All tests passed!")
        return 0
    else:
        print(f"\n[ERRO] Some tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = main()
    print("\n")
    sys.exit(exit_code)
