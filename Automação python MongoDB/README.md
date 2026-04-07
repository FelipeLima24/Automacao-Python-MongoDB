# Automacao MongoDB - Sustentacao B2C

Script para execucao de lotes de comandos MongoDB.

## Uso Rapido

```bash
python automacao_mongodb_v1.py
```

Siga o menu:
1. Informe o caminho do .zip ou .txt
2. Escolha: simular ou executar
3. Confirme a execucao

## Requisitos

- Python 3.x
- mongosh (MongoDB Shell)

### Instalar mongosh

Download: https://www.mongodb.com/try/download/shell

Apos instalar, verifique:
```bash
mongosh --version
```

## Configuracao

Edite o topo do arquivo `automacao_mongodb_v1.py`:

```python
MONGODB_URI = "mongodb://localhost:27017"
MONGODB_DATABASE = "smartbill"
```

## Formato do Arquivo de Entrada

### Arquivo .txt

Comandos MongoDB, um por linha:

```javascript
db.clientes.updateMany({"status": "pendente"}, {"$set": {"status": "ok"}})
db.faturas.updateOne({"numero": "FAT-001"}, {"$set": {"pago": true}})
```

### Arquivo .zip

Um .zip contendo um ou mais arquivos .txt com comandos.

## Exemplo de Uso

```
============================================================
AUTOMACAO MONGODB V1.0 - SUSTENTACAO B2C
============================================================
Data: 07/04/2026 10:30
Banco: smartbill
============================================================

[1] Informe o caminho do arquivo (.zip ou .txt)

Arquivo: C:\lotes\abril.zip

[OK] Arquivo lido: comandos.txt
[OK] 5 linha(s) de comando encontrada(s)

[2] O que deseja fazer?
    [1] Simular (ver comandos)
    [2] Executar direto
    [0] Sair

Opcao: 1

============================================================
SIMULACAO - Nada sera executado no banco
============================================================
...
```

## Fluxo Recomendado

1. Receber .zip do desenvolvimento
2. Rodar script
3. Simular primeiro
4. Conferir comandos
5. Executar se estiver ok

## Limitacoes

- Apenas executa comandos, nao valida logica
- Sem rollback automatico
- Sem transacoes
- Se o arquivo vier errado, devolva ao desenvolvimento

## Arquivos

| Arquivo | Descricao |
|---------|-----------|
| automacao_mongodb_v1.py | Script principal |
| MEMORIA_PROJETO.md | Memoria tecnica |
| GUIA_RAPIDO.txt | Instrucoes curtas |
