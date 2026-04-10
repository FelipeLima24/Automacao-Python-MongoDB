# Automacao MongoDB - Sustentacao B2C

## Visao geral

Este projeto automatiza a execucao de lotes de update no MongoDB a partir de arquivos `.txt` ou `.zip`.

O processo real da area e:
- o desenvolvimento envia comandos MongoDB prontos;
- a sustentacao recebe o lote;
- a sustentacao simula, executa e valida o resultado.

O banco alvo do projeto e `smartbill`.

## Versoes do projeto

### V1

Arquivo:
- `scripts/automacao_mongodb_v1.py`

Resumo:
- preservada sem alteracoes estruturais;
- le `.txt` e `.zip`;
- simula ou executa;
- usa `mongosh`.

Uso ideal:
- quando voce quer o caminho mais parecido com o processo manual.

### V2

Arquivo:
- `scripts/automacao_mongodb_v2_pymongo.py`

Resumo:
- mantém o menu simples da V1;
- le `.txt` e `.zip`;
- simula ou executa;
- usa `pymongo` em vez de `mongosh`;
- executa `updateOne` e `updateMany` a partir do formato padronizado do lote.

Uso ideal:
- quando voce quer executar direto pelo Python, sem shell externo.

## Pre-requisitos

- Python 3.x
- ambiente virtual `venv`
- MongoDB acessivel em `mongodb://localhost:27017`
- banco `smartbill`

Para a V1:
- `mongosh` instalado

Para a V2:
- `pymongo` instalado na `venv`

## Instalacao

Criar e ativar a `venv`:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Instalar dependencias:

```powershell
python -m pip install -r requirements.txt
```

## Dependencias

Arquivo:
- `requirements.txt`

Dependencia atual:
- `pymongo==4.6.0`

Uso:
- driver oficial MongoDB para Python;
- necessario para a V2.

Observacao:
- a V1 nao usa biblioteca externa Python para o banco;
- ela depende do `mongosh`, que deve estar instalado separadamente.

## Formato do lote

Os arquivos podem vir como:
- `.txt` unico
- `.zip` com varios `.txt`

Cada linha util do lote contem um comando MongoDB completo.
Na V2, cada linha nao vazia e tratada como comando. O script nao tenta
descobrir comentario, corrigir texto ou ajustar logica do lote.

Formato padrao utilizado nos exemplos atuais:

```javascript
db.document.updateMany({"customer.document": "11111111110001", "document.barCode": "000000000000000000000000000000000000000000000001", "document.flProForma": false}, {$set: {"customer.accountNumber": "99999900001"}});
```

## Como executar

### V1

```powershell
python .\scripts\automacao_mongodb_v1.py
```

### V2

```powershell
python .\scripts\automacao_mongodb_v2_pymongo.py
```

Ou, para evitar confusao com Python global:

```powershell
.\venv\Scripts\python.exe .\scripts\automacao_mongodb_v2_pymongo.py
```

## Diferenca entre simular e executar

Simular:
- le o lote;
- mostra o conteudo;
- nao altera o banco.

Executar:
- conecta no MongoDB;
- aponta para `smartbill`;
- executa todos os updates do lote.

## Diagnostico importante validado neste projeto

Um problema real apareceu durante os testes:
- o arquivo `testes/exemplos_document/queries_exemplo.txt` executava updates em `db.document`;
- mas o banco carregado inicialmente tinha apenas `clientes`, `contratos`, `faturas` e `pagamentos`;
- a collection `document` estava vazia.

Resultado no `mongosh`:

```javascript
{
  acknowledged: true,
  matchedCount: 0,
  modifiedCount: 0
}
```

Isso nao significa que a query estava errada.
Significa apenas que nenhum documento foi encontrado pelo filtro.

## Como verificar no mongosh

Entrar no shell:

```powershell
mongosh
```

Selecionar o banco:

```javascript
use smartbill
```

Ver collections:

```javascript
show collections
```

Contar documentos da collection esperada:

```javascript
db.document.countDocuments({})
```

Testar o filtro antes do update:

```javascript
db.document.countDocuments({
  "customer.document": "11111111110001",
  "document.barCode": "000000000000000000000000000000000000000000000001",
  "document.flProForma": false
})
```

Interpretacao:
- `0`: o update nao vai alterar nada;
- `> 0`: existe ao menos um documento compativel.

## Resultado validado

A V2 foi testada contra o Mongo local em Docker com massa compativel em `db.document`.

Resultado validado:
- `60` comandos lidos;
- `60` comandos encontrados;
- `matched = 60`;
- `modified = 59`.

O `59` ocorreu porque a primeira linha ja tinha sido atualizada num teste anterior.

## Arquivos principais

- `scripts/automacao_mongodb_v1.py`
- `scripts/automacao_mongodb_v2_pymongo.py`
- `testes/exemplos_document/queries_exemplo.txt`
- `testes/exemplos_document/queries_exemplo_2.txt`
- `testes/exemplos_document/lote_exemplo.zip`
- `testes/exemplos_document/lote_exemplo_2.zip`
- `MEMORIA_PROJETO.md`
- `DOCUMENTACAO_TECNICA.txt`
- `requirements.txt`

## Regras praticas para nao se perder

1. Se a V2 acusar `No module named pymongo`, voce esta usando o Python errado.
2. Sempre rode a V2 pela `venv`.
3. Se `matchedCount = 0`, o problema costuma ser massa ou filtro, nao sintaxe.
4. Se a collection do arquivo nao existir, o lote nao vai produzir efeito.
5. Nao altere a V1 quando estiver estudando a V2; use as duas como comparacao.
