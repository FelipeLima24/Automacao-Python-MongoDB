
"""
Testes de fluxo do menu interativo.

Aqui a ideia e validar o caminho que um analista faria no dia a dia:
carregar o lote, entrar em simulacao e revisar o que sera executado.
"""

import io
import os
import sys
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(__file__))

from automacao_mongodb_v1 import menu


def rodar_menu_com_entradas(inputs):
    """Executa o menu com entradas simuladas e devolve a saida."""
    original_stdin = sys.stdin

    try:
        sys.stdin = io.StringIO("\n".join(inputs))
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            menu()

        return True, buffer.getvalue()
    except Exception as e:
        return False, str(e)
    finally:
        sys.stdin = original_stdin


def test_arquivos_base_do_mvp():
    """Confere se os arquivos principais do MVP estao presentes."""
    print("\n[TESTE 1] Arquivos base do MVP")
    print("-" * 60)

    arquivos_necessarios = [
        "automacao_mongodb_v1.py",
        "README.md",
        "MEMORIA_PROJETO.md",
        "requirements.txt",
        "queries_exemplo.txt",
        "lote_exemplo.zip",
    ]

    todos_ok = True
    for arquivo in arquivos_necessarios:
        existe = os.path.exists(arquivo)
        status = "[OK]" if existe else "[ERRO]"
        print(f"{status} {arquivo}")
        if not existe:
            todos_ok = False

    if os.path.exists("GUIA_RAPIDO.txt"):
        print("[ERRO] GUIA_RAPIDO.txt nao deveria mais existir")
        return False

    if todos_ok:
        print("[OK] Estrutura principal do MVP esta consistente")
        return True

    print("[ERRO] Faltam arquivos obrigatorios do MVP")
    return False


def test_fluxo_simulacao_txt():
    """Simula o fluxo manual com o arquivo .txt unico."""
    print("\n[TESTE 2] Menu interativo com queries_exemplo.txt")
    print("-" * 60)

    sucesso, saida = rodar_menu_com_entradas([
        "queries_exemplo.txt",
        "1",
        "N",
    ])

    if not sucesso:
        print(f"[ERRO] Falha ao rodar menu: {saida}")
        return False

    if "SIMULACAO - Nada sera executado no banco" not in saida:
        print("[ERRO] A simulacao nao apareceu para o .txt")
        return False

    if "[OK] Arquivo(s) lido(s): queries_exemplo.txt" not in saida:
        print("[ERRO] O menu nao confirmou o arquivo .txt corretamente")
        return False

    if "Simulacao encerrada. Nada foi executado." not in saida:
        print("[ERRO] O fluxo do .txt nao terminou como esperado")
        return False

    print("[OK] Fluxo do .txt passou pela simulacao sem executar nada")
    return True


def test_fluxo_simulacao_zip():
    """Simula o fluxo manual com um ZIP que contem varios .txt."""
    print("\n[TESTE 3] Menu interativo com lote_exemplo.zip")
    print("-" * 60)

    sucesso, saida = rodar_menu_com_entradas([
        "lote_exemplo.zip",
        "1",
        "N",
    ])

    if not sucesso:
        print(f"[ERRO] Falha ao rodar menu: {saida}")
        return False

    if "01_clientes/01_status_cadastro.txt" not in saida:
        print("[ERRO] O menu nao mostrou os arquivos do ZIP")
        return False

    if "03_contratos/01_ajustes.txt" not in saida:
        print("[ERRO] O menu nao listou o ultimo arquivo do lote")
        return False

    if "linha(s) de comando encontrada(s)" not in saida:
        print("[ERRO] O menu nao informou a quantidade de comandos")
        return False

    if "db.faturas.updateMany" not in saida or "db.notificacoes.updateMany" not in saida:
        print("[ERRO] A simulacao do ZIP nao mostrou os comandos esperados")
        return False

    print("[OK] Fluxo do ZIP funcionou com varios arquivos no lote")
    return True


def main():
    print("\n" + "=" * 70)
    print("TESTE DE FLUXO - automacao_mongodb_v1.py")
    print("=" * 70)

    testes = [
        ("Arquivos base", test_arquivos_base_do_mvp()),
        ("Simulacao TXT", test_fluxo_simulacao_txt()),
        ("Simulacao ZIP", test_fluxo_simulacao_zip()),
    ]

    print("\n" + "=" * 70)
    print("RESUMO")
    print("=" * 70)

    for nome, resultado in testes:
        status = "[PASSOU]" if resultado else "[FALHOU]"
        print(f"{status} {nome}")

    total = len(testes)
    passou = sum(1 for _, r in testes if r)

    print("-" * 70)
    print(f"Total: {total} | Passou: {passou}")

    if passou == total:
        print("\n[SUCESSO] Todos os testes de fluxo passaram.")
        return 0

    print("\n[ERRO] Algum teste de fluxo falhou.")
    return 1


if __name__ == "__main__":
    exit_code = main()
    print("\n")
    sys.exit(exit_code)
