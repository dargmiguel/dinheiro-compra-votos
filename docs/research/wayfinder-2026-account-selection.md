# Seleção de entrega de contas para despesas declaradas — Eleições 2026

**Data de corte da pesquisa:** 13 de outubro de 2026.  
**Pergunta:** qual entrega oficial deve ser usada para medir despesas declaradas em 2026; a fórmula de dívida de 2022 vale para 2026 ou para despesas contratadas brutas; quais os prazos e qual o estado atual dos dados?

## Resposta executiva

**Não há norma geral do TSE que determine uma entrega única para toda medida de despesas declaradas.** As normas distinguem obrigações e prazos para relatório financeiro, prestação parcial e prestação final; elas não autorizam somar essas entregas como se fossem fatos econômicos distintos. O leia-me oficial do arquivo de despesas contratadas de 2026 dá códigos ao tipo de entrega (`0=Final`, `1=Relatório Financeiro`, `2=Parcial`) e define `Final` como a entrega final da prestação. Ele **não** diz que o total bruto de despesas contratadas deve ser selecionado pela mesma fórmula de dívida apresentada na seção I.1. Para uma medida final declarada, filtrar a entrega `Final` é compatível com a definição oficial da modalidade; a regra de “última Final recepcionada com sucesso” é explicitamente documentada para o cálculo de dívida, não como regra geral de qualquer indicador. Retificações devem ser tratadas conforme suas regras próprias, não somadas como contas independentes. ([leia-me oficial 2026, ZIP de candidatos, `leiame_despesas-contratadas-candidatos.pdf`, pp. 4, 9–10](https://cdn.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2026.zip))

A regra atribuída a 2022 para dívida **também aparece no leia-me oficial do conjunto de candidatos de 2026**: para a dívida exibida no DivulgaCandContas, usar a última entrega recepcionada com sucesso do tipo `Final`, subtrair valores pagos dos contratados e aplicar exclusões de contas DRD. Isso responde positivamente quanto à fórmula de dívida documentada para 2026, mas **não** a torna fórmula para despesas contratadas brutas.

Na data de corte, o prazo da prestação final do primeiro turno ainda estava em curso (até **3 de novembro de 2026**). O Portal de Dados Abertos do TSE listava o recurso de contas de candidatos de 2026, mas informa que a data de atualização deve ser verificada dentro do arquivo, e seus metadados estavam atualizados em **21 de agosto de 2026**. O leia-me descreve arquivos em constante atualização; logo, o estado de atualização deve ser verificado no arquivo específico e sua data `DT_GERACAO`/`HH_GERACAO`. A existência do recurso não prova que a cópia consultada já contenha entregas finais completas. Não tratar as parciais como finais.

## O que as normas de 2026 exigem

A Resolução TSE nº 23.607/2019, com alterações aplicáveis às Eleições 2026 introduzidas pela Resolução TSE nº 23.752/2026, separa modalidades de prestação e deveres de informação. A resolução de 2026 altera o art. 47 para estabelecer o envio pela internet da prestação parcial entre **9 e 13 de setembro**, registrando movimentações até **8 de setembro**. A publicação do TSE para o pleito reafirma esses termos e identifica o sistema Conta+JE. ([Resolução TSE nº 23.752/2026](https://www.tse.jus.br/legislacao/compilada/res/2026/resolucao-no-23-752-de-26-de-fevereiro-de-2026); [orientação TSE de prazos 2026](https://www.tse.jus.br/comunicacao/noticias/2026/Setembro/faltam-27-dias-confira-os-principais-prazos-da-prestacao-de-contas-eleitoral); [página TSE de prestação de contas 2026](https://www.tse.jus.br/eleicoes/eleicoes-2026-content/prestacao-de-contas))

O relatório financeiro é obrigação diferente: o art. 47, I, prevê informar recursos financeiros recebidos em até **72 horas** do recebimento. O prazo se refere à informação do recebimento, não constitui uma conta final de despesas contratadas. ([Resolução TSE nº 23.607/2019, texto compilado](https://www.tse.jus.br/legislacao/compilada/res/2019/resolucao-no-23-607-de-17-de-dezembro-de-2019?texto=compilado); [Resolução TSE nº 23.752/2026](https://www.tse.jus.br/legislacao/compilada/res/2026/resolucao-no-23-752-de-26-de-fevereiro-de-2026))

As contas finais do primeiro turno devem ser enviadas até o **30º dia posterior à eleição**. Para 2026, o TSE indica o período de **5 de outubro a 3 de novembro de 2026** e identifica 3 de novembro como último dia. Candidaturas que disputarem segundo turno têm prestação final complementar no prazo de até **20 dias após o segundo turno**, na forma da resolução. ([Resolução TSE nº 23.607/2019, texto compilado](https://www.tse.jus.br/legislacao/compilada/res/2019/resolucao-no-23-607-de-17-de-dezembro-de-2019?texto=compilado); [TSE, prazos de prestação 2026](https://www.tse.jus.br/comunicacao/noticias/2026/Setembro/faltam-27-dias-confira-os-principais-prazos-da-prestacao-de-contas-eleitoral); [calendário eleitoral TSE 2026](https://www.tse.jus.br/eleicoes/eleicoes-2026/calendario-eleitoral-2026))

O art. 71 da Resolução 23.607 disciplina prestação retificadora, inclusive suas hipóteses e apresentação. A regra não transforma parciais e retificadoras em entregas finais independentes a somar: eventual versão retificada deve ser considerada no contexto processual e com sua situação de recebimento/validade. ([Resolução TSE nº 23.607/2019, texto compilado](https://www.tse.jus.br/legislacao/compilada/res/2019/resolucao-no-23-607-de-17-de-dezembro-de-2019?texto=compilado); [Resolução TSE nº 23.752/2026](https://www.tse.jus.br/legislacao/compilada/res/2026/resolucao-no-23-752-de-26-de-fevereiro-de-2026))

Essas disposições normativas especificam **o que deve ser informado e quando**. A norma não estabelece uma regra de seleção a ser usada em toda estatística de “despesas declaradas”, nem manda agregar parcial, relatório financeiro, final e retificadora. O leia-me do recurso 2026, porém, permite distinguir os tipos e oferece a regra da **dívida** (não de qualquer total): última entrega `Final` recepcionada com sucesso. Para despesas contratadas brutas, use os registros `Final` em uma extração identificada e verifique a atualização/retificação correspondente; não use a fórmula de dívida nem some entregas.

O leia-me 2026 lista `TP_PRESTACAO_CONTAS` e `DT_PRESTACAO_CONTAS`, mas não descreve campo de status de recepção bem-sucedida. Portanto, a aplicação do seletor “última Final recebida com sucesso” à **dívida** vem da fórmula publicada pelo TSE; não é possível inferir sucesso/ordem final de todas as contas de um CSV usando apenas esses campos listados. Para total bruto, retenha apenas entregas `Final`, marque a data de geração do arquivo e não invente status de sucesso/retificação ausentes.

## Regra de dívida documentada em 2026 — e limite do seu escopo

O leia-me oficial de despesas contratadas de candidatos 2026 define `TP_PRESTACAO_CONTAS` como códigos `0=Final`, `1=Relatório Financeiro` e `2=Parcial`; define a Final como o tipo de entrega em que serão gerados relatórios de análise, exame, diligência e conclusivo; chama o Relatório Financeiro de prestação de informações de doações recebidas dentro de 72 horas; e descreve a Parcial como prestação completa para avaliação prévia antes da análise final. Define ainda `VR_DESPESA_CONTRATADA` como o valor contratado declarado. Na observação I.1, o mesmo leia-me documenta para a dívida do DivulgaCandContas: somar valores contratados na última entrega recepcionada com sucesso do tipo `Final`, com exclusões de DRD, e subtrair os valores pagos dessa última `Final`, com suas exclusões específicas. ([leia-me oficial 2026, ZIP de candidatos, pp. 4, 9–10](https://cdn.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2026.zip))

A mesma observação aparece no leia-me oficial do conjunto de 2022. ([leia-me oficial 2022, ZIP de candidatos](https://cdn.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2022.zip); transcrição e localizadores do leia-me no [relatório de pesquisa de 2022](tse-2022-despesas-repeticoes.md), seção 2.4.)

A fórmula não é sinônimo de soma bruta de `VR_DESPESA_CONTRATADA`: ela subtrai valores pagos, escolhe a última entrega `Final` recebida com sucesso e contém exclusões. **Portanto, a regra sobrevive em 2026 para o cálculo específico de dívida documentado pelo TSE; não se aplica automaticamente a um indicador de total bruto contratado.**

## Prazos e estado da fonte de dados na data de corte

| Item | Regra/prazo oficial de 2026 | Estado em 13/10/2026 |
|---|---|---|
| Relatório financeiro | Até 72 horas do recebimento financeiro (art. 47, I) | Obrigação em vigor durante campanha; seu prazo não é a prestação final. |
| Prestação parcial | Envio entre 9 e 13/09; movimentação até 08/09 | Janela encerrada; parcial permanece parcial. |
| Final do primeiro turno | 05/10–03/11, com limite em 03/11 (30º dia) | Prazo ainda aberto na data de corte; não há base para presumir que todas as contas finais já foram enviadas. |
| Segundo turno | Prestação final complementar até 20 dias após o segundo turno | Prazo futuro na data de corte; dependerá de candidatura no segundo turno. |
| Dados abertos de candidatos | Recurso TSE 2026 ativo; atualização indicada como disponível dentro do arquivo | Recurso existe; metadados criados em 18/08 e atualizados em 21/08/2026. `Datastore active: false`; a página não informa a data efetiva de atualização do ZIP. O README orienta a usar `DT_GERACAO`/`HH_GERACAO` de cada arquivo e avisa que os arquivos estão em atualização constante (p. 1). A cópia e sua data efetiva devem ser verificadas antes de afirmar completude. |

Fontes: [recurso oficial de contas de candidatos 2026](https://dadosabertos.tse.jus.br/pt_BR/dataset/prestacao-de-contas-eleitorais-2026/resource/dc8c1c26-7df0-4d90-a6da-f567b3f6cc00), [conjunto oficial de contas 2026](https://dadosabertos.tse.jus.br/pt_BR/dataset/prestacao-de-contas-eleitorais-2026), [prazos TSE](https://www.tse.jus.br/comunicacao/noticias/2026/Setembro/faltam-27-dias-confira-os-principais-prazos-da-prestacao-de-contas-eleitoral), [Resolução TSE nº 23.607/2019 compilada](https://www.tse.jus.br/legislacao/compilada/res/2019/resolucao-no-23-607-de-17-de-dezembro-de-2019?texto=compilado).

## Procedimento prudente para um indicador de despesas declaradas

1. Definir a métrica: despesas contratadas brutas (`VR_DESPESA_CONTRATADA`) não são dívida, nem despesa paga.
2. Para fotografia final, usar somente entrega classificada como `Final`; selecionar a versão mais recente recebida com sucesso apenas se o leia-me e os campos/status do arquivo 2026 permitirem confirmar isso. Não somar entregas sucessivas como fatos econômicos distintos.
3. Excluir parciais e relatórios financeiros de uma base “final”; não converter a janela temporal curta ou o status de envio em finalização.
4. Tratar retificações como revisão da entrega correspondente, e não como linha/conta adicional, após verificar o tratamento que o arquivo 2026 atribui a elas.
5. Até confirmar que a versão pública inclui as finais e a versão retificadora válida, rotular o cálculo como parcial/provisório ou não o publicar como final.

Os itens 2–5 são recomendações de método para não misturar modalidades; a norma sustenta os prazos/modalidades, mas não substitui a checagem do leia-me e do status da entrega no recurso 2026.

## Fontes oficiais primárias

- [Resolução TSE nº 23.607/2019 — compilada](https://www.tse.jus.br/legislacao/compilada/res/2019/resolucao-no-23-607-de-17-de-dezembro-de-2019?texto=compilado)
- [Resolução TSE nº 23.752/2026](https://www.tse.jus.br/legislacao/compilada/res/2026/resolucao-no-23-752-de-26-de-fevereiro-de-2026)
- [TSE — prestação de contas das Eleições 2026](https://www.tse.jus.br/eleicoes/eleicoes-2026-content/prestacao-de-contas)
- [TSE — principais prazos das prestações de contas 2026](https://www.tse.jus.br/comunicacao/noticias/2026/Setembro/faltam-27-dias-confira-os-principais-prazos-da-prestacao-de-contas-eleitoral)
- [TSE — calendário eleitoral 2026](https://www.tse.jus.br/eleicoes/eleicoes-2026/calendario-eleitoral-2026)
- [Portal de Dados Abertos do TSE — Prestação de Contas Eleitorais 2026](https://dadosabertos.tse.jus.br/pt_BR/dataset/prestacao-de-contas-eleitorais-2026)
- [TSE — recurso de prestação de contas de candidatos 2026](https://dadosabertos.tse.jus.br/pt_BR/dataset/prestacao-de-contas-eleitorais-2026/resource/dc8c1c26-7df0-4d90-a6da-f567b3f6cc00)
- [TSE — README 2026 de despesas contratadas (membro `leiame_despesas-contratadas-candidatos.pdf`, no ZIP oficial de candidatos)](https://cdn.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2026.zip)
- [TSE — ZIP de dados de candidatos 2022 (fonte da fórmula antiga)](https://cdn.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2022.zip)
