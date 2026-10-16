# Pergunta pronta ao TSE — despesas contratadas e comparativo de 2022

**Assunto:** Solicitação de regra de identidade, entregas e comparabilidade das despesas contratadas — Eleições 2022

Prezadas/os,

Estou preparando uma análise reproduzível, sem finalidade de fiscalização individual, sobre candidaturas a deputado federal nas Eleições 2022. Usei o recurso oficial **Prestação de contas de candidatos**, recurso CKAN `e45493d5-75df-4ccf-a4b4-7b1f5213577d`, no arquivo:

`https://cdn.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2022.zip`

O arquivo congelado para a análise tem SHA-256 `d706fa9abaa8e00a222a4bdafc310bc198b8c8f2dd55a31c4177847344967bc4`, tamanho `474699288` bytes, `ETag` `"1c4b5618-65d07ece19dcc"` e `Last-Modified` `Sun, 04 Oct 2026 18:28:00 GMT`.

Aplicando `AA_ELEICAO = 2022`, `ST_TURNO = 1` e `DS_CARGO = Deputado Federal`, encontrei 21.874 ocorrências excedentes de linhas textualmente idênticas nos membros por UF. A comparação foi feita em todos os campos do leiaute, sem remover colunas. A igualdade de conteúdo não foi tratada como prova de duplicação econômica.

Peço, por favor, orientação oficial sobre os pontos abaixo:

1. **Identidade da despesa:** duas linhas com todos os campos iguais, inclusive `SQ_CANDIDATO`, `TP_PRESTACAO_CONTAS`, `NR_DOCUMENTO`, `SQ_DESPESA`, `DT_DESPESA`, fornecedor, descrição e `VR_DESPESA_CONTRATADA`, podem representar dois itens legítimos ou a regra do sistema considera uma delas repetição de publicação? Existe uma chave oficial de unicidade para o registro de despesa?
2. **`SQ_DESPESA` e documento:** `SQ_DESPESA` é único dentro de candidato, entrega, UF ou arquivo? O mesmo `SQ_DESPESA`/`NR_DOCUMENTO` pode conter vários itens econômicos? Existe regra oficial para agregar esses itens?
3. **Exemplo de linha idêntica:** no membro `despesas_contratadas_candidatos_2022_AC.csv`, as linhas 1410 e 1411 têm `SQ_CANDIDATO = 10001642332` e `SQ_DESPESA = 51789637`, com todos os campos iguais. Como o TSE orienta tratar esse par?
4. **Exemplo de múltiplos itens:** no membro `despesas_contratadas_candidatos_2022_PR.csv`, o candidato `SQ_CANDIDATO = 160001597847` possui `SQ_DESPESA = 51841829` e `NR_DOCUMENTO = 180` em várias linhas com descrições e valores diferentes, incluindo `CAIXA PERSONALIZADA` (R$ 1.890,00), `ADESIVO VINIL - CORTE DE CONTORNO` (R$ 115,00), `BANNER/FAIXA PERSONALIZADA ACABAMENTO EM MADEIRA` (R$ 34,00, R$ 20,00 e R$ 84,00). Essas linhas devem ser somadas como itens distintos?
5. **Tipo de prestação:** para reproduzir `Gastos Financeiros` no DivulgaCandContas, deve-se usar somente a última prestação `Final` recebida com sucesso? Como entram `Parcial`, `Relatório Financeiro`, `Regularização da Omissão` e retificações? Qual campo e qual regra indicam a entrega válida e mais recente?
6. **Definição do comparativo:** `Gastos Financeiros` corresponde exatamente à soma de `VR_DESPESA_CONTRATADA` após a seleção da entrega? `Gastos Estimáveis` são excluídos desse total? Há exclusões, como contas de DRD, que devem ser aplicadas?
7. **Chave e situação da candidatura:** qual chave oficial liga uma linha do comparativo ao arquivo (`SQ_CANDIDATO` ou outra)? Qual regra deve ser usada para candidaturas substituídas, inaptas, não eleitas ou com situação alterada depois da eleição?
8. **Ausência e zero:** no comparativo/exportação, como distinguir ausência de prestação ou de lançamento de um valor observado igual a zero?
9. **Versão e auditoria:** existe exportação oficial do comparativo em CSV, com leiaute, data/hora de geração, versão, checksum ou identificador de snapshot, que possa ser arquivada para conciliação por candidato?

Agradeço se puderem indicar os documentos, leiautes ou procedimento oficial que sustentem as respostas. Sem essa regra, manterei a base financeira bloqueada e não deduplicarei as linhas automaticamente.

Atenciosamente,

[Nome]
