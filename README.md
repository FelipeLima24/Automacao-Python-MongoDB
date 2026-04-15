# Automacao MongoDB - Sustentacao B2C

## Objetivo do projeto

Este projeto executa updates em massa no MongoDB a partir de lotes enviados pelo time de desenvolvimento.

O foco e operacional:
- execucao automatica;
- execucao recorrente;
- uso via Control-M;
- sem interacao humana.

## Contexto da area

Na rotina de Sustentacao de Faturamento B2C, o desenvolvimento envia um arquivo .zip.
Dentro desse .zip existem um ou mais .txt, e cada linha do .txt ja chega com comando pronto.

Exemplo de linha:

db.document.updateMany({...}, {$set: {...}});

A sustentacao nao altera regra de negocio. Apenas executa o lote.

## Como o script funciona

1. Usa um caminho fixo de entrada.
2. Identifica se a entrada e .zip ou .txt.
3. Se for .zip, extrai os .txt para pasta temporaria.
4. Le os comandos linha por linha.
5. Faz a adaptacao tecnica minima para PyMongo.
6. Conecta no MongoDB.
7. Executa os updates no banco smartbill, collection document.
8. Registra log de inicio, volume, sucesso/erro por comando e fim.

## Fluxo de execucao batch

O script foi feito para agendador e por isso:
- nao possui menu;
- nao usa input();
- nao pede confirmacao;
- retorna codigo 0 em sucesso e 1 em falha.

## Adaptacao PyMongo (explicacao simples)

O comando do arquivo chega no formato do shell MongoDB:

db.document.updateMany(filtro, update);

O PyMongo nao executa esse texto completo.
Ele precisa receber:

collection.update_many(filtro_dict, update_dict)

Por isso a V2 faz apenas o necessario:
- remove prefixo e sufixo do comando;
- separa filtro e update;
- converte texto para dict;
- chama update_many.

Isso e adaptacao tecnica, nao validacao de negocio.

## Como rodar localmente

Ativar ambiente:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Executar:

```powershell
python .\scripts\automacao_mongodb_v2_pymongo.py
```

## Arquivos principais

- scripts/automacao_mongodb_v2_pymongo.py
- testes/lote_mvp_teste.txt
- testes/lote_mvp_teste.zip
- logs/automacao_mongodb_v2.log

## Limitacoes do MVP

- nao cria comandos;
- nao valida regra de negocio;
- nao corrige lote recebido;
- nao implementa rollback ou transacao;
- trabalha apenas com comandos no padrao updateMany esperado.
