# MEMORIA_PROJETO - V1.0 MVP

## Resumo

Automacao de execucao de lotes MongoDB para a sustentacao faturamento B2C.

## Versao Atual: 1.0 (MVP)

### O que faz

1. Abre .zip ou .txt
2. Le conteudo dos arquivos
3. Mostra comandos (simulacao)
4. Executa no MongoDB via mongosh

### O que NAO faz

- Nao interpreta comandos
- Nao valida logica
- Nao faz rollback
- Nao usa transacoes
- Nao corrige erros

## Divisao de Responsabilidades

| Area | Responsabilidade |
|------|------------------|
| Desenvolvimento | Criar comandos corretos |
| Sustentacao | Executar lote |

**Se o arquivo vier quebrado: devolva ao desenvolvimento.**

## Decisoes Tecnicas

### Por que mongosh via subprocess?

- Executa comandos nativamente
- Nao precisa parsear nada
- Nao precisa pymongo
- Nao precisa regex
- Simplicidade maxima

### O que foi removido (vs versao anterior)

- Regex de comando
- Parser de argumentos
- json_util / bson
- pymongo
- Dataclasses
- Transacoes
- Rollback
- Fail-fast / continue-on-error
- Relatorios JSON
- Argumentos CLI

## Estrutura

```
automacao_mongodb_v1.py   <- Script unico
MEMORIA_PROJETO.md        <- Este arquivo
README.md                 <- Documentacao
GUIA_RAPIDO.txt          <- Instrucoes curtas
```

## Configuracao

No topo do arquivo `automacao_mongodb_v1.py`:

```python
MONGODB_URI = "mongodb://localhost:27017"
MONGODB_DATABASE = "smartbill"
```

## Dependencias

- Python 3.x
- mongosh (MongoDB Shell)

## Proximas Versoes (Stand By)

| Feature | Status |
|---------|--------|
| Log em arquivo | Futuro |
| Selecao parcial do lote | Futuro |
| Outros comandos (insert/delete) | Futuro |
| Relatorio de execucao | Futuro |

## Historico

- v1.0: MVP simplificado com mongosh
- v0.x: Versao complexa (descontinuada)
