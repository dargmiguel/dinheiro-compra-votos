# Distribuição financeira e eleitoral — deputados federais, 2022

## Resumo

Na população APTO/Final com despesa observada há 9.204 candidatos. As receitas financeiras declaradas somam **R$ 3.053.147.587,19**: recursos públicos **R$ 2.696.891.459,34 (88.3315%)**, Outros Recursos **R$ 356.256.127,85 (11.6685%)** e não classificados **R$ 0,00** (421 candidatos registrados na classe). Separadamente, 421 candidatos têm total de receitas observado igual a zero; não há candidatos sem qualquer linha de receita. O denominador dos percentuais é o total de receitas financeiras desta população.

As despesas contratadas deduplicadas dos candidatos somam **R$ 3.076.142.628,75**. Os pagamentos declarados somam **R$ 3.033.236.464,43**, com linhas para 8.363/9.204 candidatos; não houve deduplicação adicional de pagamentos. São três medidas distintas: receita declarada, contratação declarada e pagamento declarado.

## Recortes e denominadores

- População-base: 2022, 1º turno, deputado federal, candidaturas APTO com ao menos uma linha Final de despesa contratada; N=9.204 de 9.476 APTO. 272 APTO não têm despesa Final observada.
- Resultado eleitoral disponível para 9.204/9.204; a proporção eleita divide eleitos pelo total de candidatos do grupo, sem condicionar à cobertura de receitas financeiras. É diferente do recorte de 9.202 do modelo eleitoral ajustado.
- Receitas financeiras: 8.858/9.204 candidatos (96,2408%) têm ao menos uma linha CD_NATUREZA=1. Os 346 sem qualquer linha financeira são excluídos das medianas de receita, não imputados como R$ 0.
- As medianas total, pública e Outros Recursos usam a mesma população dentro de cada grupo: candidatos com ao menos uma linha financeira. Para a mediana de fonte, componente sem linha é zero apenas na operação matemática da mediana comum; não é recebido observado de R$ 0. Os campos de ausência de linha e os zeros com linha financeira observada ficam separados.
- Medianas de despesa contratada usam todos os candidatos do grupo com despesa Final observada; valores observados iguais a zero continuam incluídos.
- Todos os 9.204 têm alguma linha de receita, embora 346 não tenham linha financeira. Há linha financeira pública para 7.713 candidatos e de Outros Recursos para 3.955; na coorte com qualquer receita financeira, 1.145 não têm linha pública e 4.903 não têm linha de Outros Recursos.
- Fonte: CD_FONTE 0/2 = público; CD_FONTE 1 = Outros Recursos; códigos restantes não classificados. CD_NATUREZA_RECEITA=1 = financeiro; 0 = estimável. Receitas estimáveis não entram nas medianas financeiras.

## Sexo, raça/cor e partidos

As tabelas por grupo apresentam candidatos, cobertura financeira, medianas de receitas na coorte com receita financeira observada, mediana de despesas contratadas e eleitos/total. Categorias de raça/cor ficam separadas; PRETAS + PARDAS é um agregado complementar sobreposto a PRETA e PARDA. “NÃO INFORMADO” e “NÃO DIVULGÁVEL” permanecem explícitas.

A tabela por partido descreve despesas contratadas dos candidatos, não contas de diretórios. `small_group_n_lt_30` sinaliza grupos com menos de 30 candidatos; não é teste de significância.

Despesas menores não significam menor orçamento recebido. Diferenças entre grupos são descritivas; não demonstram efeito causal. A fonte declarada de um pagamento não prova rastreamento de fungibilidade entre receita e despesa.

## Arquivos

- `tse-2022-financial-distribution-totals.csv`: totais, recortes, denominadores e cobertura.
- `tse-2022-financial-distribution-by-party.csv`: despesas contratadas por partido dos candidatos.
- `tse-2022-financial-distribution-by-group.csv`: sexo, categorias de raça/cor e agregado pretas+pardas.
- `tse-2022-financial-distribution-dictionary.csv`: definições e interpretação dos campos.
- `summarize-tse-2022-financial-distribution.py`: reprodução destes artefatos a partir dos arquivos existentes.
