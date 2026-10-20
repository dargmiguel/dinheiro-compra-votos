# Guia dos relatórios e artefatos

Este diretório contém relatórios narrativos, tabelas, especificações de recortes, diagnósticos e saídas exploratórias do estudo do TSE 2022. Este índice explica o papel de cada arquivo e indica por onde começar. O mapa do código e do restante do repositório está em [`docs/repository-guide.md`](../docs/repository-guide.md); a reprodução está em [`docs/pilot-2022-reproduction.md`](../docs/pilot-2022-reproduction.md).

## Por onde começar

1. Leia [`tse-2022-financial-analysis.md`](tse-2022-financial-analysis.md) para os resultados principais, modelo, limitações e análises secundárias.
2. Consulte [`tse-2022-deduplication-analysis.md`](tse-2022-deduplication-analysis.md) para a decisão de deduplicação e a sensibilidade com todas as linhas.
3. Para valores e cobertura de receitas, despesas contratadas e pagamentos, use [`tse-2022-financial-distribution.md`](tse-2022-financial-distribution.md) e os dicionários correspondentes.
4. Para reproduzir, siga [`docs/pilot-2022-reproduction.md`](../docs/pilot-2022-reproduction.md), não comandos adivinhados a partir de scripts isolados.

## Recortes e vocabulário essenciais

Os resultados são do recorte de candidaturas a deputado federal no primeiro turno de 2022. No snapshot congelado, há **9.476 candidaturas APTO**; as **1.154 INAPTO** são inventariadas separadamente. A distribuição financeira usa **9.204 candidaturas APTO com despesa contratada final observada**. O modelo principal usa **9.202** candidaturas com despesa, votos, denominador oficial e controles completos. Os denominadores mudam por pergunta e estão definidos em cada relatório e arquivo de recorte.

A exposição principal é a **despesa contratada declarada**, não pagamento e não necessariamente dinheiro público. **Receita financeira, despesa contratada e pagamento declarado são fluxos distintos**; não se deve tratar um como substituto do outro. Ausência de registro não é zero observado. A deduplicação principal remove apenas linhas exatamente iguais nos 53 campos originais dentro do mesmo snapshot e membro de origem; os relatórios de sensibilidade preservam todas as ocorrências. O denominador de votos válidos por UF inclui votos nominais e votos de legenda.

As estimativas e comparações são descritivas ou associativas. Não demonstram causalidade, eficiência, desperdício, irregularidade, comportamento de eleitores individuais nem que a despesa foi financiada exclusivamente com recursos públicos.

## 1. Resultado principal, denominadores e diagnósticos

| Arquivo | O que contém / como usar |
|---|---|
| [`tse-2022-financial-analysis.md`](tse-2022-financial-analysis.md) | Relatório principal: escopo, população, cobertura, deduplicação, modelos de participação nos votos válidos, cenários padronizados, sexo, eleições, raça/cor, diagnósticos e limitações. É a referência narrativa para os resultados publicados. |
| [`tse-2022-readme-summary.svg`](tse-2022-readme-summary.svg) | Resumo visual dos principais resultados, incorporado ao README. É uma síntese de resultados publicados, não uma análise independente. |
| [`tse-2022-financial-analysis.json`](tse-2022-financial-analysis.json) | Versão estruturada das contagens, resultados, modelos, diagnósticos, predições e metadados da execução; não é um estudo ou recorte alternativo. |
| [`tse-2022-financial-model-estimates.csv`](tse-2022-financial-model-estimates.csv) | Coeficientes e incerteza dos modelos. GLM na escala logit; coeficientes OLS na escala do desfecho indicada. |
| [`tse-2022-predicted-expense-scenarios.csv`](tse-2022-predicted-expense-scenarios.csv) | Predições padronizadas em níveis de despesa selecionados, com intervalos e tamanho da amostra. Associações de população padronizadas, não predições individuais nem efeitos causais. |
| [`tse-2022-vote-denominator-by-uf.csv`](tse-2022-vote-denominator-by-uf.csv) | Uma linha por UF: votos nominais válidos, votos válidos de legenda e total oficial usado no denominador. A fonte é o membro nacional `BRASIL`; não somar também os membros estaduais. |
| [`tse-2022-apto-expenses-by-type.csv`](tse-2022-apto-expenses-by-type.csv) | Despesas APTO por tipo de prestação (`Final`, `Parcial`, regularização e relatório financeiro), comparando todas as linhas e linhas deduplicadas. A exposição principal usa `Final`. |
| [`tse-2022-inapto-expenses-by-type.csv`](tse-2022-inapto-expenses-by-type.csv) | Inventário descritivo separado para INAPTO; não integra a regressão principal. |
| [`tse-2022-model-calibration-deciles.csv`](tse-2022-model-calibration-deciles.csv) | Observado versus ajustado por decis na própria amostra; diagnóstico interno, não validação externa. |
| [`tse-2022-model-influence-top-candidates.csv`](tse-2022-model-influence-top-candidates.csv) | Observações com maiores medidas de influência e estatísticas associadas. Limiares são diagnósticos; candidaturas não foram removidas automaticamente. |
| [`tse-2022-top-one-percent-expense-sensitivity.csv`](tse-2022-top-one-percent-expense-sensitivity.csv) | Sensibilidade do coeficiente da despesa à exclusão do extremo superior P99; documenta influência da cauda, não identifica valores errados. |
| [`tse-2022-sex-interaction-curve.csv`](tse-2022-sex-interaction-curve.csv) | Predições ajustadas por sexo ao longo do suporte comum de despesas, com intervalos e diferenças em pontos percentuais. Comparação associativa. |

## 2. Deduplicação e qualidade da fonte

| Arquivo | O que contém / ressalva |
|---|---|
| [`tse-2022-deduplication-analysis.md`](tse-2022-deduplication-analysis.md) | Protocolo e resultado da deduplicação exata, reconciliações e contraste com todas as linhas. Repetições exatas são uma decisão de mensuração, não evidência de irregularidade ou desperdício. |
| [`tse-2022-duplicate-diagnostics.json`](tse-2022-duplicate-diagnostics.json) | Diagnóstico estruturado, totais, grupos de duplicatas e referências às linhas de origem. |
| [`tse-2022-dedup-exclusions.csv`](tse-2022-dedup-exclusions.csv) | Auditoria linha a linha das ocorrências excluídas pela regra de igualdade exata; inclui linha mantida e assinatura. Não é uma lista de denúncias. |
| [`tse-2022-candidate-delivery-inventory.md`](tse-2022-candidate-delivery-inventory.md) | Inventário descritivo de status das candidaturas e tipos de entrega. Não aprova nem libera, por si só, a base financeira. |
| [`tse-2022-candidate-reconciliation.md`](tse-2022-candidate-reconciliation.md) | Diagnóstico histórico de comparação entre linhas deduplicadas e todas as linhas, com casos e perguntas ainda em aberto naquele estágio. Leia como trilha de decisão, não como substituto do relatório final nem como validação econômica independente. |

## 3. Distribuição financeira e fontes de recursos

### Receitas, despesas contratadas e pagamentos

| Arquivo | O que contém / como usar |
|---|---|
| [`tse-2022-financial-distribution.md`](tse-2022-financial-distribution.md) | Comparação descritiva de receitas financeiras, despesas contratadas e pagamentos declarados, com cobertura e grupos. As tabelas de partidos referem-se às despesas de candidaturas filiadas, não ao orçamento dos diretórios partidários. |
| [`tse-2022-financial-distribution-totals.csv`](tse-2022-financial-distribution-totals.csv) | Totais por fluxo, medida e classe de fonte, com denominadores de cobertura e participação. Denominadores podem diferir entre linhas. |
| [`tse-2022-financial-distribution-by-party.csv`](tse-2022-financial-distribution-by-party.csv) | Totais e medianas de despesa contratada por partido das candidaturas, com população e cobertura. |
| [`tse-2022-financial-distribution-by-group.csv`](tse-2022-financial-distribution-by-group.csv) | Receitas, despesas, cobertura e resultados por sexo/raça-cor. O agregado pretas+pardas se sobrepõe às categorias separadas; não é uma categoria exclusiva adicional. |
| [`tse-2022-financial-distribution-dictionary.csv`](tse-2022-financial-distribution-dictionary.csv) | Definições dos campos das tabelas de distribuição, centavos, coberturas, medianas e ausências. Leia antes de comparar colunas. |
| [`summarize-tse-2022-financial-distribution.py`](summarize-tse-2022-financial-distribution.py) | Script que recompõe as tabelas de distribuição a partir das saídas tabulares existentes e da base analítica. O procedimento completo e seus pré-requisitos estão na documentação de reprodução. |

### Classificação de receitas e pagamentos

| Arquivo | O que contém / como usar |
|---|---|
| [`tse-2022-funding-source-recut.json`](tse-2022-funding-source-recut.json) | Especificação do recorte de fontes: população, arquivos/UFs, chaves, códigos de fonte/natureza, denominadores e política para ausência. |
| [`tse-2022-funding-source-candidates.csv`](tse-2022-funding-source-candidates.csv) | Uma linha por candidatura de referência, com presença e valores de receitas/pagamentos por classe e natureza. Valores são em centavos; presença de linha é distinta de valor informado. |
| [`tse-2022-funding-source-summary.csv`](tse-2022-funding-source-summary.csv) | Agregação por fluxo e classe de fonte, com cobertura, registros, valores e denominadores alternativos de participação. |
| [`tse-2022-funding-source-dictionary.csv`](tse-2022-funding-source-dictionary.csv) | Dicionário dos arquivos por candidatura e resumo. Distingue receita declarada, pagamento declarado e despesa contratada. |

A cobertura de pagamentos é 8.363/9.204; 841 candidaturas sem linha de pagamento não são tratadas como pagamento zero. A cobertura de receita financeira é 8.858/9.204; 346 sem linha financeira não são imputadas como zero. Fontes pública e privada podem coexistir na mesma candidatura. Os campos de pagamento não rastreiam a fungibilidade do dinheiro nem ligam um pagamento a uma receita específica.

## 4. Resultado eleitoral secundário

A classificação de eleitos usa os códigos oficiais 2 e 3; não eleitos, 4 e 5. Estes arquivos respondem a perguntas secundárias distintas do modelo de participação nos votos válidos.

| Arquivo | O que contém / como usar |
|---|---|
| [`tse-2022-election-expense-comparison.csv`](tse-2022-election-expense-comparison.csv) | Comparação descritiva de despesas por resultado e cenário; a métrica de despesa por voto exclui candidaturas sem votos positivos e não é o preditor do modelo principal. |
| [`tse-2022-election-expense-models.csv`](tse-2022-election-expense-models.csv) | Coeficientes de modelos logísticos para resultado eleitoral, com erros robustos e intervalos; interpretação associativa. |
| [`tse-2022-election-rate-by-uf-expense-band.csv`](tse-2022-election-rate-by-uf-expense-band.csv) | Taxa de eleição por quartil de despesa dentro de cada UF. Não confundir esses quartis com as faixas fixas abaixo. |
| [`tse-2022-election-powerbi-candidates.csv`](tse-2022-election-powerbi-candidates.csv) | Exportação tabular por candidatura para Power BI, com resultado, UF, despesas e faixa fixa. Não é um dashboard ou arquivo `.pbix`. |
| [`tse-2022-election-powerbi-summary.csv`](tse-2022-election-powerbi-summary.csv) | Exportação agregada por geografia e faixa fixa de despesa, com denominador e numerador de eleitos. |
| [`tse-2022-election-powerbi-dictionary.csv`](tse-2022-election-powerbi-dictionary.csv) | Dicionário das duas exportações tabulares. |
| [`tse-2022-election-powerbi-recut.json`](tse-2022-election-powerbi-recut.json) | Especificação reproduzível do recorte: 9.202 candidaturas incluídas, 510 eleitos, 274 excluídas por falta de despesa/controles, e limites fixos em R$50 mil, R$200 mil e R$1 milhão. |

## 5. Temporalidade das despesas

São descrições por data declarada da despesa, não análises causais do efeito do momento do gasto. O campo temporal utilizado é `DT_DESPESA`, não a data de pagamento, de prestação ou de geração do arquivo.

| Arquivo | O que contém / como usar |
|---|---|
| [`tse-2022-expense-temporal-recut.json`](tse-2022-expense-temporal-recut.json) | Especificação de população, `Final`, data da despesa, janela de 2022, dia da eleição e cenários deduplicado/todas as linhas. Define ausências, inválidos e datas fora do ano. |
| [`tse-2022-expense-temporal-monthly.csv`](tse-2022-expense-temporal-monthly.csv) | Contagens de linhas/candidaturas e valores por mês, cenário e base de despesa. |
| [`tse-2022-expense-temporal-relative-to-election.csv`](tse-2022-expense-temporal-relative-to-election.csv) | Totais antes, no dia e depois de 02/10/2022, conforme data declarada da despesa. Contagens de candidaturas entre períodos não são necessariamente aditivas. |
| [`tse-2022-expense-temporal-date-quality.csv`](tse-2022-expense-temporal-date-quality.csv) | Contabiliza datas válidas de 2022, fora de 2022, ausentes ou inválidas e informa o que entra nas tabelas temporais. |
| [`tse-2022-expense-temporal-dictionary.csv`](tse-2022-expense-temporal-dictionary.csv) | Dicionário, unidades (linhas versus candidaturas) e semântica de datas dos três CSVs temporais. |

## 6. Raça/cor: análises secundárias e suporte

O contraste binário pré-especificado é candidaturas **BRANCA** versus **PRETA + PARDA**. Amarela, indígena, não divulgável, não informada e ausente permanecem visíveis na contagem da população, mas não entram nesse contraste. As curvas ajustadas só são liberadas com suporte suficiente; a cobertura observada não atingiu o limite pré-definido de 80%.

| Arquivo | O que contém / como usar |
|---|---|
| [`tse-2022-race-population-counts.csv`](tse-2022-race-population-counts.csv) | Contagens por categoria original e indicador de inclusão no contraste binário. |
| [`tse-2022-race-group-descriptives.csv`](tse-2022-race-group-descriptives.csv) | Descritivas por grupo/cenário: candidaturas, cobertura, quartis de despesas/votos, resultados e denominadores. |
| [`tse-2022-race-interaction-coefficients.csv`](tse-2022-race-interaction-coefficients.csv) | Coeficientes dos modelos de interação, com erro robusto HC1 e intervalos; não autorizam interpretação causal. |
| [`tse-2022-race-interaction-curve.csv`](tse-2022-race-interaction-curve.csv) | Predições, incerteza e critérios de suporte ao longo dos valores de despesa; consulte `publication_flag` e as tabelas de suporte antes de interpretar. |
| [`tse-2022-race-curve-support.csv`](tse-2022-race-curve-support.csv) | Diagnóstico do suporte por valor de despesa, grupos, células e cobertura. |
| [`tse-2022-race-support-by-uf-party.csv`](tse-2022-race-support-by-uf-party.csv) | Contagens e intervalos de suporte por combinação UF×partido, usados no gate de sobreposição. |
| [`tse-2022-race-interaction-curve-deduplicado.svg`](tse-2022-race-interaction-curve-deduplicado.svg) | Figura diagnóstica do cenário deduplicado; informa que a curva não foi exibida por cobertura insuficiente. |
| [`tse-2022-race-interaction-curve-todas-as-linhas.svg`](tse-2022-race-interaction-curve-todas-as-linhas.svg) | Mesmo diagnóstico para a sensibilidade com todas as linhas. |

O protocolo e os critérios completos estão em [`docs/tse-2022-race-secondary-protocol.md`](../docs/tse-2022-race-secondary-protocol.md) e [`docs/tse-2022-race-election-secondary-protocol.md`](../docs/tse-2022-race-election-secondary-protocol.md). Os artefatos de coeficientes/suporte não devem ser resumidos como uma curva ajustada publicada quando o gate a suprimiu.

## 7. Artefato explicitamente exploratório

- [`tse-2022-exploratory-provisional.md`](tse-2022-exploratory-provisional.md) — análise exploratória e provisória, não é o resultado principal. Usa votos nominais sem o denominador oficial completo com votos de legenda e não usa os controles finais. Consulte apenas como registro do desenvolvimento; não misture suas métricas com as estimativas finais.

## 8. Pacote visual do carrossel TSE 2022

O pacote visual mantido é a [versão 4](linkedin-carousel-2022/v4/POWERBI-IMPORT.md), com [PDF final](linkedin-carousel-2022/v4/carrossel-final.pdf), SVGs e prévias. As tabelas de apoio ficam em [`linkedin-carousel-2022/data/`](linkedin-carousel-2022/data/); a geometria cartográfica necessária ao renderizador está em `v4/apoio/`. Não há outras versões do carrossel mantidas no repositório.

## Leitura aprofundada recomendada

Depois do relatório principal, avance para deduplicação e denominador; em seguida, leia os diagnósticos do modelo, resultados eleitorais secundários, distribuição financeira, classificação de fontes, temporalidade e protocolos de raça/cor. Deixe o relatório exploratório provisório por último. Para explicações sobre cada módulo do código, testes, dados versionados e reprodução, consulte o [guia do repositório](../docs/repository-guide.md).
