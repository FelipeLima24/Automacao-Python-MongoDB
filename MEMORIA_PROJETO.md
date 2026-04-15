# MEMORIA_PROJETO

## 1. Contexto do negocio

Projeto da area de Sustentacao de Faturamento B2C.
Objetivo operacional: executar lotes de update MongoDB recebidos do desenvolvimento.

## 2. Processo atual da operacao

1. Desenvolvimento envia arquivo .zip.
2. Dentro do .zip existem arquivos .txt.
3. Cada linha do .txt ja e um comando MongoDB pronto.
4. Sustentacao executa o lote.

## 3. Responsabilidade entre times

Desenvolvimento:
- cria o comando;
- define regra de negocio;
- corrige lote quando houver erro de conteudo.

Sustentacao:
- executa o lote recebido;
- registra log operacional;
- devolve lote quando vier fora do contrato.

Regra operacional:
- sustentacao nao cria comando;
- sustentacao nao corrige negocio;
- sustentacao nao interpreta intencao funcional.

## 4. Decisao de descartar a V1

V1 dependia de mongosh e foi descartada.

Motivo:
- dependencia externa inviavel para padronizacao em ambiente corporativo controlado.

Conclusao:
- V1 removida do projeto.

## 5. Decisao de usar PyMongo

V2 com PyMongo e a unica versao valida.

Motivo:
- executa direto pelo Python;
- reduz dependencia operacional;
- melhora previsibilidade para execucao recorrente via agendador.

## 6. Motivo da adaptacao do comando

Entrada do lote:

db.document.updateMany({...}, {$set: {...}});

O PyMongo nao executa texto no formato do shell.
Ele exige chamada Python com filtro e update separados:

collection.update_many(filtro, update)

Logo, a adaptacao tecnica minima e obrigatoria.

## 7. Restricoes do ambiente corporativo

- execucao automatica;
- execucao recorrente;
- Control-M;
- sem interacao humana.

Implicacoes diretas no codigo:
- sem menu;
- sem input();
- sem prompts;
- retorno deterministico para sucesso/falha;
- logs operacionais objetivos.

## 8. Decisao de simplificacao

A V2 foi simplificada agressivamente para manter apenas o essencial.

Removido:
- V1;
- teste automatizado legado;
- arquivos antigos fora do escopo atual;
- estruturas e camadas desnecessarias.

Mantido:
- leitura de .zip/.txt;
- leitura de linhas;
- adaptacao minima para PyMongo;
- execucao no Mongo;
- log basico de operacao.

## 9. Escopo MVP atual

Dentro do escopo:
- batch simples e previsivel;
- foco em execucao, nao em inteligencia de validacao;
- rastreabilidade por log.

Fora do escopo:
- validacao de regra de negocio;
- correcao automatica de lote;
- parser complexo;
- rollback/transacao;
- tratamento de cenarios fora do contrato.
