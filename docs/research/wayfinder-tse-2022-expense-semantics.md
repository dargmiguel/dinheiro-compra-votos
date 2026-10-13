# Semântica de despesas e seleção de prestação — TSE 2022

**Ticket:** [Research issue #5](https://github.com/dargmiguel/dinheiro-compra-votos/issues/5)  
**Escopo:** documentação oficial TSE sobre linhas idênticas, seleção da entrega financeira e relação entre despesas contratadas e “Gastos Financeiros” no DivulgaCandContas.

## Resposta curta

1. **Linhas completas idênticas:** não encontrei regra oficial que declare que linhas de despesas integralmente iguais sejam publicações duplicadas ou despesas separadas, nem regra de unicidade/deduplicação para o arquivo. A documentação define os campos, mas não resolve a semântica da repetição exata. Portanto, essa evidência não autoriza escolher remover ou preservar ocorrências.
2. **Seleção de entrega:** para a fórmula oficial de **dívida de campanha** no leia-me das despesas contratadas de candidatos 2022, o TSE manda considerar a **última entrega do tipo `Final` recebida com sucesso pelo SPCE-WEB**. O leia-me não equivale a “última linha do CSV”, “última tentativa” ou simplesmente maior data de geração. A Resolução TSE nº 23.607/2019 regula quando uma retificadora é válida e como a parcial pode ser corrigida após o início do prazo das contas finais; ela não fornece uma chave de deduplicação de registros exportados.
3. **“Gastos Financeiros”:** não encontrei documentação TSE que declare que o valor bruto de `VR_DESPESA_CONTRATADA` é idêntico ao campo/indicador apresentado como “Gastos Financeiros” no DivulgaCandContas. O leia-me distingue contratadas de pagas e define dívida como diferença entre somas de determinados registros; não se deve tratar esses conceitos como equivalentes sem uma definição oficial adicional.

## 1. Linhas idênticas

O leia-me oficial `leiame_despesas-contratadas-candidatos.pdf`, distribuído no ZIP TSE de prestação de contas de candidatos 2022, identifica `SQ_DESPESA` como sequencial interno do registro de despesa contratada e `NR_DOCUMENTO` como número do documento comprobatório. Descreve também os campos de entrega, despesa, fornecedor e valor. **Não** declara que a tupla de todos os campos seja única; tampouco afirma que duas linhas com conteúdo integralmente igual sejam duas publicações da mesma despesa, duas despesas independentes ou um erro de extração. Não define política de eliminação de duplicatas.

Assim, documentação e CSV não permitem determinar o significado administrativo de uma repetição completa apenas pela igualdade textual. Também não foi encontrada uma regra oficial que escolha uma ocorrência pela primeira/última posição no arquivo, ou que autorize somá-las, descartá-las ou consolidá-las. Esta constatação é ausência de definição nas fontes examinadas, não afirmação de que o TSE nunca tenha regra interna não publicada.

**Fontes:** [conjunto oficial TSE — Prestação de Contas Eleitorais 2022](https://dadosabertos.tse.jus.br/dataset/dadosabertos-tse-jus-br-dataset-prestacao-de-contas-eleitorais-2022), incluindo o [ZIP oficial de prestação de contas dos candidatos](https://cdn.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2022.zip) e o leia-me nele contido. O inventário de campos e a leitura do leia-me estão registrados no relatório anterior do projeto [Semântica das repetições em despesas contratadas de candidatos — TSE 2022](tse-2022-despesas-repeticoes.md), §§ 2.2 e 4; trata-se da mesma documentação primária, não de uma regra adicional.

## 2. Entrega financeira: status, retificações e precedência

### Critério explícito do leia-me

Na observação I.1 do leia-me de despesas contratadas, o TSE descreve a dívida de campanha publicada no DivulgaCandContas como:

- somatório dos valores contratados das despesas **na última entrega recebida com sucesso pelo SPCE-WEB do tipo `Final`**, com exclusões especificadas para determinadas contas de DRD;
- menos o somatório dos valores pagos **nessa mesma última entrega final recebida com sucesso**, também sujeito às exclusões especificadas.

Isto dá evidência explícita sobre a precedência para **essa fórmula**: exigência de recebimento bem-sucedido, restrição ao tipo `Final`, uso da última entrega bem-sucedida dentro desse critério e alinhamento de contratadas e pagas à mesma entrega. Tentativa não recebida com sucesso não satisfaz o critério. O texto não transforma a data/hora de geração do CSV em identificador de entrega nem prescreve “a linha mais recente vence”.

A fórmula documentada é específica da dívida de campanha. Ela não afirma que todos os indicadores do DivulgaCandContas, nem todas as consultas de despesas, sejam computados do mesmo modo.

### Regra legal sobre parcial, final e retificadora

A [Resolução TSE nº 23.607/2019, texto compilado](https://www.tse.jus.br/legislacao/compilada/res/2019/resolucao-no-23-607-de-17-de-dezembro-de-2019) disciplina apresentação e retificação da prestação. Conforme art. 71, a retificação é permitida nas hipóteses de cumprimento de diligência que altere informação inicialmente prestada ou, voluntariamente, para corrigir erro material detectado antes do pronunciamento técnico. O próprio artigo prevê consequências e avaliação judicial da validade da retificadora. O § 2º determina que, iniciado o prazo para contas finais, a prestação parcial não pode mais ser retificada: alterações devem ser feitas por retificação das contas finais, com nota explicativa. A versão compilada deve ser lida com atenção ao contexto temporal: o leia-me é a fonte específica para a fórmula de 2022; a resolução é a fonte normativa para o procedimento.

Essas regras dão significado à retificação como correção processual sob condições, mas **não** dizem que cada registro de uma versão anterior deve ser deduplicado por conteúdo, nem estabelecem que qualquer linha coincidente entre entregas represente a mesma despesa. Para reproduzir a fórmula citada no leia-me, o critério documentado é a última entrega `Final` recebida com sucesso — não a união de todas as entregas. Para uma decisão geral sobre todas as linhas ou campos de entrega de um CSV, a documentação examinada não publica política adicional de seleção.

**Fontes:** leia-me do arquivo oficial listado na seção 1; [Resolução TSE nº 23.607/2019](https://www.tse.jus.br/legislacao/compilada/res/2019/resolucao-no-23-607-de-17-de-dezembro-de-2019), em especial arts. 47 e 71.

## 3. Despesas contratadas e “Gastos Financeiros”

A fonte TSE oferece arquivos separados de despesas **contratadas** e despesas **pagas**. O leia-me das contratadas descreve `VR_DESPESA_CONTRATADA` como o valor contratado informado pelo prestador. Já a regra da dívida de campanha usa duas parcelas distintas — contratadas e pagas — na última entrega final recebida com sucesso, com exclusões próprias. Portanto:

- somar `VR_DESPESA_CONTRATADA` não é, por si só, aplicar a fórmula oficial da dívida de campanha;
- o total bruto de despesas contratadas não é intercambiável com o total de despesas pagas;
- não encontrei, nas fontes oficiais examinadas, definição que iguale o nome “Gastos Financeiros” a essa coluna ou ao somatório bruto das despesas contratadas.

O portal do conjunto 2022 identifica a origem dos dados como sistemas SPCE e publica o ZIP de candidatos, mas seus metadados não definem “Gastos Financeiros”. A notícia institucional do TSE sobre o DivulgaCandContas informa que o sistema permite consulta pública de arrecadação e gastos das campanhas, sem fornecer uma identidade entre aquela expressão e `VR_DESPESA_CONTRATADA`. O leia-me define a fórmula da dívida, não uma equivalência de rótulos de interface.

**Conclusão delimitada:** a equivalência entre despesas contratadas e “Gastos Financeiros” não foi estabelecida nas fontes consultadas. Isso não prova que os valores necessariamente diferem; indica que não há suporte documental aqui para declará-los iguais. Seria necessário documento técnico oficial que defina o indicador do DivulgaCandContas e sua relação com as tabelas de contratadas/pagas.

**Fontes:** [conjunto oficial TSE — 2022](https://dadosabertos.tse.jus.br/dataset/dadosabertos-tse-jus-br-dataset-prestacao-de-contas-eleitorais-2022); [ZIP oficial dos candidatos e leia-me](https://cdn.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2022.zip); [notícia oficial do TSE sobre o DivulgaCandContas em 2022](https://www.tse.jus.br/comunicacao/noticias/2022/Agosto/divulgacandcontas-consulte-arrecadacoes-e-gastos-de-campanhas-nas-eleicoes-2022).

## Limites desta conclusão

- O TSE fornece os campos e a fórmula para dívida de campanha, mas o material localizado não especifica o significado de linhas completas idênticas.
- A regra da última entrega bem-sucedida é diretamente documentada para a fórmula de dívida, não extrapolada a toda métrica ou endpoint.
- A busca por uma equivalência textual entre “Gastos Financeiros” e o somatório de contratadas não encontrou definição oficial; a ausência de resultado é limitada ao material pesquisado.
- Este relatório não escolhe regra de remoção ou preservação, não altera dados/implementação e não atualiza o status do ticket.
