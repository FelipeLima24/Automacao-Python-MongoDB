# Automacao MongoDB - MVP de Sustentacao B2C

## Contexto do processo atual

Hoje a area recebe do desenvolvimento um lote com comandos MongoDB prontos.
Esse lote pode vir em um arquivo `.txt` ou em um `.zip` contendo varios `.txt`.

No MVP atual, a sustentacao nao monta query, nao faz parser e nao corrige regra de negocio.
O papel do script e ajudar a abrir o lote, mostrar o que sera executado e disparar a execucao quando o arquivo estiver ok.

Se o lote vier quebrado, incompleto ou com logica errada, ele deve voltar para o desenvolvimento.

## Objetivo do script

O script `automacao_mongodb_v1.py` faz quatro coisas:

1. Recebe o caminho de um `.txt` ou `.zip`.
2. Localiza e le o conteudo dos `.txt`.
3. Mostra os comandos em modo de simulacao.
4. Executa os comandos no banco `smartbill` usando `mongosh`.

## Pre-requisitos

- Python 3.x instalado na maquina
- `mongosh` instalado e disponivel no `PATH`
- Acesso ao MongoDB que sera usado na operacao
- Arquivo `.txt` ou `.zip` enviado pelo desenvolvimento

Para validar se o `mongosh` esta disponivel:

```powershell
mongosh --version
```

Download oficial do `mongosh`:
https://www.mongodb.com/try/download/shell

## Criacao do ambiente virtual (venv)

No PowerShell, dentro da pasta do projeto:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Se quiser sair do ambiente virtual:

```powershell
deactivate
```

Se o PowerShell bloquear a ativacao do `venv`, rode:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

## Instalacao das dependencias

Este MVP nao usa bibliotecas externas de Python.
Mesmo assim, o fluxo padrao do projeto continua sendo:

```powershell
pip install -r requirements.txt
```

Hoje esse comando nao instala nenhuma lib extra, porque o script usa apenas a biblioteca padrao do Python.

Importante: `mongosh` nao entra no `requirements.txt`, porque ele nao e uma biblioteca Python. Ele precisa ser instalado separadamente na maquina.

## Configuracao

A conexao esta fixa no topo de [automacao_mongodb_v1.py]

```python
MONGODB_URI = "mongodb://localhost:27017"
MONGODB_DATABASE = "smartbill"
```

Se precisar apontar para outro ambiente, ajuste essas duas constantes.

Observacao: neste MVP o script nao le configuracao do `.env`. A referencia usada na execucao real e a que estiver no topo do arquivo Python.

## Como executar o script

```powershell
python automacao_mongodb_v1.py
```

Depois informe o caminho de um arquivo como:

```text
queries_exemplo.txt
lote_exemplo.zip
```

## Como funciona o mini menu

O fluxo do menu é direto:

1. O script pede o caminho do arquivo `.txt` ou `.zip`.
2. Se for `.zip`, ele procura todos os `.txt` dentro do pacote.
3. O script mostra quais arquivos foram encontrados e quantas linhas de comando existem.
4. Voce escolhe entre simular, executar direto ou sair.
5. Se escolher simular, o script exibe o lote inteiro e pergunta se voce quer executar em seguida.
6. Se escolher executar, o script pede a confirmacao digitando `EXECUTAR`.

## Diferenca entre simulacao e execucao real

`Simulação`:

- le o arquivo normalmente
- mostra o conteudo na tela
- nao altera nada no banco

`Execução real`:

- monta um arquivo temporario `.js`
- adiciona `use smartbill;` no inicio
- chama o `mongosh` para rodar o lote no MongoDB

Fluxo recomendado do MVP:

1. Receber o lote do desenvolvimento.
2. Rodar primeiro em simulacao.
3. Conferir os comandos e os arquivos encontrados.
4. Executar de verdade somente depois da confirmacao.

## Formato do arquivo de entrada

Arquivo `.txt`:

- comandos MongoDB em texto simples
- um comando por linha

Arquivo `.zip`:

- pode conter varios `.txt`
- o script junta todos os `.txt` encontrados para formar o lote final

Exemplo de comando:

```javascript
db.clientes.updateMany({"statusCadastro": "pendente"}, {"$set": {"statusCadastro": "ativo"}})
db.faturas.updateOne({"numero": "FAT-2026-0315"}, {"$set": {"status": "cancelada"}}, {"upsert": false})
```

## Limitacoes do MVP

- O script nao valida regra de negocio.
- O script nao corrige comando enviado pelo desenvolvimento.
- O script nao faz rollback automatico.
- O script nao tenta tratar o lote comando a comando.
- Se o `mongosh` nao estiver instalado, a execucao real nao funciona.

## MongoDB Compass vs mongosh

Hoje a empresa usa o MongoDB Compass de forma manual.
Esse script nao automatiza cliques no Compass e nao executa o lote por dentro da interface grafica.

O MVP usa `mongosh` porque essa e a forma mais simples de pegar os comandos que ja chegam prontos, apontar para o banco `smartbill` e executar sem criar um parser em Python.

Na pratica:

- `MongoDB Compass` pode continuar sendo usado para consulta visual e conferencia manual.
- `mongosh` e obrigatorio para a execucao real do script.
- Se a maquina tiver apenas o Compass, a leitura e a simulacao funcionam, mas a execucao real vai falhar quando o script tentar chamar `mongosh`.

## Arquivos de apoio do MVP

- automacao_mongodb_v1.py: script principal
- README.md:  documentacao operacional
- MEMORIA_PROJETO.md: memoria enxuta do MVP
- queries_exemplo.txt: exemplo de lote em arquivo unico
- lote_exemplo.zip: exemplo de lote com varios `.txt`
