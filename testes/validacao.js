// Validacao dos dados modificados
print('='.repeat(60));
print('VALIDACAO FINAL - DADOS MODIFICADOS');
print('='.repeat(60));

print('\n--- CLIENTES ---');
print('Total documentos: ' + db.clientes.countDocuments());
print('\nClientes regularizados (inadimplente: false):');
db.clientes.find({inadimplente: false}).limit(3).forEach(doc => {
    print('  CPF: ' + doc.cpf + ' | Status: ' + doc.status + ' | Motivo: ' + doc.motivoRegularizacao);
});

print('\nEmails corrigidos:');
db.clientes.find({emailValidado: true}).limit(3).forEach(doc => {
    print('  Email: ' + doc.email + ' | Validado em: ' + doc.dataValidacaoEmail);
});

print('\nClientes com LGPD atualizado:');
db.clientes.find({aceitouLGPD: true}).limit(3).forEach(doc => {
    print('  CPF: ' + doc.cpf + ' | Canal: ' + doc.canalPreferido);
});

print('\n--- CONTRATOS ---');
print('Total documentos: ' + db.contratos.countDocuments());
print('\nContratos ativados:');
db.contratos.find({status: 'ativo', ativadoPor: {$exists: true}}).limit(3).forEach(doc => {
    print('  Contrato: ' + doc.numeroContrato + ' | Ativado por: ' + doc.ativadoPor);
});

print('\nContratos cancelados:');
db.contratos.find({status: 'cancelado'}).limit(3).forEach(doc => {
    print('  Contrato: ' + doc.numeroContrato + ' | Motivo: ' + doc.motivoCancelamento);
});

print('\nContratos com plano migrado:');
db.contratos.find({planoAnterior: {$exists: true}}).limit(3).forEach(doc => {
    print('  Contrato: ' + doc.numeroContrato + ' | ' + doc.planoAnterior + ' -> ' + doc.planoAtual);
});

print('\n--- FATURAS ---');
print('Total documentos: ' + db.faturas.countDocuments());
print('\nFaturas processadas:');
db.faturas.find({status: 'processado', processadoPor: {$exists: true}}).limit(3).forEach(doc => {
    print('  Fatura: ' + doc.numeroFatura + ' | Processado por: ' + doc.processadoPor);
});

print('\nFaturas pagas:');
db.faturas.find({status: 'pago'}).limit(3).forEach(doc => {
    print('  Fatura: ' + doc.numeroFatura + ' | Forma: ' + doc.formaPagamento + ' | Valor: R$ ' + doc.valorPago);
});

print('\nFaturas com juros aplicados:');
db.faturas.find({jurosAplicado: true}).limit(3).forEach(doc => {
    print('  Fatura: ' + doc.numeroFatura + ' | Original: R$ ' + doc.valorOriginal + ' | Total: R$ ' + doc.valorTotal);
});

print('\n--- PAGAMENTOS ---');
print('Total documentos: ' + db.pagamentos.countDocuments());
print('\nPagamentos PIX confirmados:');
db.pagamentos.find({tipo: 'pix', status: 'confirmado'}).limit(3).forEach(doc => {
    print('  ID: ' + doc.transacaoId + ' | Banco: ' + doc.nomeOrigem + ' | R$ ' + doc.valorConfirmado);
});

print('\nBoletos liquidados:');
db.pagamentos.find({tipo: 'boleto', status: 'liquidado'}).limit(3).forEach(doc => {
    print('  Canal: ' + doc.canalPagamento);
});

print('\nCartoes aprovados:');
db.pagamentos.find({tipo: 'cartao', status: 'aprovado'}).limit(3).forEach(doc => {
    print('  NSU: ' + doc.nsu + ' | Bandeira: ' + doc.bandeira + ' | Parcelas: ' + doc.parcelas);
});

print('\nEstornos processados:');
db.pagamentos.find({status: 'estornado'}).limit(3).forEach(doc => {
    print('  ID: ' + doc.transacaoId + ' | Motivo: ' + doc.motivoEstorno + ' | R$ ' + doc.valorEstorno);
});

print('\n' + '='.repeat(60));
print('VALIDACAO CONCLUIDA COM SUCESSO!');
print('='.repeat(60));
