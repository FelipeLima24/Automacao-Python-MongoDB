"""
Testes simples para o MVP.

Cobertura principal:
- leitura de .txt unico
- leitura de .zip com varios .txt
- simulacao
- chamada do mongosh sem depender do shell instalado
"""

import io
import os
import sys
import tempfile
import zipfile
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(__file__))

from automacao_mongodb_v1 import (
    MONGODB_DATABASE,
    MONGODB_URI,
    executar,
    ler_arquivo,
    simular,
)


def contar_linhas_validas(conteudo):
    return [linha for linha in conteudo.splitlines() if linha.strip()]


def test_importacao():
    """Valida se o modulo principal sobe sem erro."""
    print("\n[TESTE 0] Importacao do modulo")
    print("-" * 60)

    try:
        import automacao_mongodb_v1  # noqa: F401
        print("[OK] Modulo importado com sucesso")
        return True
    except Exception as e:
        print(f"[ERRO] Erro ao importar: {e}")
        return False


def test_ler_txt_exemplo():
    """Valida o arquivo .txt de exemplo com varias linhas diferentes."""
    print("\n[TESTE 1] Leitura do arquivo .txt de exemplo")
    print("-" * 60)

    sucesso, conteudo, arquivos = ler_arquivo("queries_exemplo.txt")

    if not sucesso:
        print(f"[ERRO] {conteudo}")
        return False

    linhas = contar_linhas_validas(conteudo)

    if arquivos != ["queries_exemplo.txt"]:
        print(f"[ERRO] Lista de arquivos inesperada: {arquivos}")
        return False

    if len(linhas) < 8:
        print(f"[ERRO] Esperava pelo menos 8 comandos, mas vieram {len(linhas)}")
        return False

    if "db.faturas.updateMany" not in conteudo or "db.pagamentos.updateMany" not in conteudo:
        print("[ERRO] O exemplo .txt nao cobre collections esperadas")
        return False

    print(f"[OK] Arquivo lido: {arquivos[0]}")
    print(f"[OK] Total de comandos: {len(linhas)}")
    return True


def test_ler_zip_multiplos_txt():
    """Valida o ZIP com varios .txt em pastas diferentes."""
    print("\n[TESTE 2] Leitura do ZIP com varios .txt")
    print("-" * 60)

    sucesso, conteudo, arquivos = ler_arquivo("lote_exemplo.zip")

    if not sucesso:
        print(f"[ERRO] {conteudo}")
        return False

    arquivos_esperados = [
        "01_clientes/01_status_cadastro.txt",
        "01_clientes/02_segmentacao.txt",
        "02_financeiro/01_faturas.txt",
        "02_financeiro/02_pagamentos.txt",
        "03_contratos/01_ajustes.txt",
    ]

    if arquivos != arquivos_esperados:
        print(f"[ERRO] Arquivos do ZIP diferentes do esperado: {arquivos}")
        return False

    linhas = contar_linhas_validas(conteudo)
    if len(linhas) < 10:
        print(f"[ERRO] Esperava pelo menos 10 comandos no ZIP, mas vieram {len(linhas)}")
        return False

    if "db.clientes.updateMany" not in conteudo or "db.contratos.updateOne" not in conteudo:
        print("[ERRO] O ZIP nao cobre a variedade esperada de comandos")
        return False

    print(f"[OK] ZIP lido com {len(arquivos)} arquivos .txt")
    print(f"[OK] Total de comandos encontrados: {len(linhas)}")
    return True


def test_simular_mostra_arquivos_e_comandos():
    """Garante que a simulacao exibe os pontos principais na tela."""
    print("\n[TESTE 3] Saida da simulacao")
    print("-" * 60)

    sucesso, conteudo, arquivos = ler_arquivo("lote_exemplo.zip")
    if not sucesso:
        print(f"[ERRO] Nao conseguiu ler o ZIP para a simulacao: {conteudo}")
        return False

    buffer = io.StringIO()
    try:
        with redirect_stdout(buffer):
            simular(conteudo, arquivos)
    except Exception as e:
        print(f"[ERRO] Falha ao rodar simular(): {e}")
        return False

    saida = buffer.getvalue()

    if "SIMULACAO - Nada sera executado no banco" not in saida:
        print("[ERRO] Cabecalho de simulacao nao apareceu")
        return False

    if "01_clientes/01_status_cadastro.txt" not in saida or "03_contratos/01_ajustes.txt" not in saida:
        print("[ERRO] A simulacao nao mostrou a lista completa de arquivos")
        return False

    if "db.pagamentos.updateMany" not in saida:
        print("[ERRO] A simulacao nao mostrou os comandos esperados")
        return False

    print("[OK] Simulacao exibiu arquivos e comandos do lote")
    return True


def test_executar_chama_mongosh_sem_exigir_shell_real():
    """Valida a montagem do script e a chamada do mongosh via mock."""
    print("\n[TESTE 4] Execucao com mock do mongosh")
    print("-" * 60)

    chamada = {}

    def fake_run(args, capture_output, text, timeout):
        chamada["args"] = args
        chamada["timeout"] = timeout
        chamada["capture_output"] = capture_output
        chamada["text"] = text
        chamada["arquivo_temp"] = args[3]

        with open(args[3], "r", encoding="utf-8") as arquivo:
            chamada["script"] = arquivo.read()

        return SimpleNamespace(returncode=0, stdout="ok\n", stderr="")

    comando = (
        'db.logsIntegracao.updateOne({"lote": "LTP-2026-04-07"}, '
        '{"$set": {"status": "reprocessado"}}, {"upsert": false})'
    )

    buffer = io.StringIO()
    with patch("automacao_mongodb_v1.subprocess.run", side_effect=fake_run):
        with redirect_stdout(buffer):
            sucesso, mensagem = executar(comando)

    if not sucesso or mensagem != "Sucesso":
        print(f"[ERRO] Retorno inesperado da execucao: {sucesso}, {mensagem}")
        return False

    if chamada.get("args") != ["mongosh", MONGODB_URI, "--file", chamada["arquivo_temp"]]:
        print(f"[ERRO] Chamada do mongosh diferente do esperado: {chamada.get('args')}")
        return False

    if chamada.get("timeout") != 300:
        print(f"[ERRO] Timeout inesperado: {chamada.get('timeout')}")
        return False

    if not chamada.get("capture_output") or not chamada.get("text"):
        print("[ERRO] subprocess.run nao recebeu os parametros esperados")
        return False

    script_esperado = f"use {MONGODB_DATABASE};\n{comando}"
    if chamada.get("script") != script_esperado:
        print("[ERRO] Script enviado ao mongosh nao ficou como esperado")
        return False

    if os.path.exists(chamada["arquivo_temp"]):
        print("[ERRO] O arquivo temporario deveria ter sido removido")
        return False

    print("[OK] Execucao montou o script corretamente e limpou o temporario")
    return True


def test_arquivo_invalido():
    """Valida retorno para arquivo inexistente."""
    print("\n[TESTE 5] Arquivo inexistente")
    print("-" * 60)

    sucesso, conteudo, _ = ler_arquivo("arquivo_que_nao_existe.txt")

    if sucesso:
        print("[ERRO] Deveria retornar False para arquivo inexistente")
        return False

    if "Arquivo nao encontrado" not in conteudo:
        print(f"[ERRO] Mensagem inesperada: {conteudo}")
        return False

    print(f"[OK] Retorno correto: {conteudo}")
    return True


def test_zip_invalido():
    """Valida retorno quando o arquivo tem extensao .zip mas nao e um ZIP valido."""
    print("\n[TESTE 6] ZIP invalido")
    print("-" * 60)

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(b"conteudo invalido")
        tmp_path = tmp.name

    try:
        sucesso, conteudo, _ = ler_arquivo(tmp_path)

        if sucesso:
            print("[ERRO] Deveria retornar False para ZIP invalido")
            return False

        if conteudo != "Arquivo ZIP corrompido":
            print(f"[ERRO] Mensagem inesperada: {conteudo}")
            return False

        print("[OK] ZIP invalido foi tratado corretamente")
        return True
    finally:
        os.unlink(tmp_path)


def test_zip_sem_txt():
    """Valida comportamento quando o ZIP nao traz nenhum .txt."""
    print("\n[TESTE 7] ZIP sem arquivos .txt")
    print("-" * 60)

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        with zipfile.ZipFile(tmp_path, "w") as zf:
            zf.writestr("arquivo.csv", "coluna;valor")

        sucesso, conteudo, _ = ler_arquivo(tmp_path)

        if sucesso:
            print("[ERRO] Deveria falhar quando nao existe .txt no ZIP")
            return False

        if conteudo != "Nenhum .txt encontrado no ZIP":
            print(f"[ERRO] Mensagem inesperada: {conteudo}")
            return False

        print("[OK] ZIP sem .txt foi recusado corretamente")
        return True
    finally:
        os.unlink(tmp_path)


def main():
    """Executa todos os testes."""
    print("\n" + "=" * 70)
    print("TESTE DE FUNCIONALIDADE - automacao_mongodb_v1.py")
    print("=" * 70)

    testes = [
        test_importacao,
        test_ler_txt_exemplo,
        test_ler_zip_multiplos_txt,
        test_simular_mostra_arquivos_e_comandos,
        test_executar_chama_mongosh_sem_exigir_shell_real,
        test_arquivo_invalido,
        test_zip_invalido,
        test_zip_sem_txt,
    ]

    resultados = []
    for teste in testes:
        try:
            resultado = teste()
            resultados.append((teste.__name__, resultado))
        except Exception as e:
            print(f"\n[ERRO CRITICO] {teste.__name__}: {e}")
            resultados.append((teste.__name__, False))

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
        print("\n[SUCESSO] Todos os testes passaram.")
        return 0

    print(f"\n[ERRO] {falhou} teste(s) falharam.")
    return 1


if __name__ == "__main__":
    exit_code = main()
    print("\n")
    sys.exit(exit_code)
