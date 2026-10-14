# Análise financeira TSE 2022 — deputado federal, 1º turno

Versão de dados: `20261008T154908Z`.

## Escopo e método

População: 9.476 candidaturas APTO no snapshot; 1.154 candidaturas INAPTO levantadas separadamente. A situação do snapshot não é uma conclusão jurídica sobre a data da eleição.
Desfecho: votos nominais válidos do candidato / total oficial de votos válidos por UF (nominais + legenda). O denominador oficial foi reconciliado antes dos filtros de situação e tipo de prestação.
Exposição: VR_DESPESA_CONTRATADA em prestações Final, BRL, transformação log(1 + despesa); zeros observados preservados; ausência excluída da regressão. Principal: despesas deduplicadas; sensibilidade: todas as linhas. A regra compara os 53 campos TSE no mesmo snapshot e membro, excluindo auditoria; não prova identidade econômica.
Denominador oficial: 109.305.870 votos válidos — 105.014.357 nominais + 4.291.513 de legenda — nas 27 UFs. Origem congelada: `https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_partido_munzona/votacao_partido_munzona_2022.zip`, ZIP `data/raw/2022/20261008T154908Z/votacao_partido_munzona_2022.zip`, SHA-256 `4f6325c4a496cce00220e197ef3dd2dcd331c44b42e706194dd9e89294d68d9f`, 26.150.488 bytes.
Escopo da fonte: deputado federal, primeiro turno de 2022; votos nominais e de legenda incluídos.
Cobertura de votos em APTO: 9.476/9.476 com denominador e votos observados; 0 sem cobertura; 107 com zero voto nominal.
Validação do pipeline: approved; 0 contagens fatais. Reconciliações de linhas/valores de despesas e votos: sim/sim/sim/sim; votos nominais coincidem por UF: sim (27 UFs).
Modelo principal: GLM binomial/logit para participação fracionária, com erros-padrão robustos HC1. Modelo completo ajusta UF, partido, idade, sexo, raça e escolaridade; comparação reduzida ajusta UF e partido. Não se combina partido e federação.
A análise é associação, não causalidade; confundimento por qualidade do candidato, incumbência, apoio partidário, geografia e competitividade permanece possível. Sexo não feminino/masculino e ausência de sexo ficam fora apenas da interação; o modelo completo mantém categorias informadas.

## Cobertura, zeros e totais de despesas Final entre APTO

| Cenário | Total declarado (R$) | Candidatos com despesa Final | Total observado zero | Sem linha Final |
|---|---:|---:|---:|---:|
| Deduplicado (principal) | 3.076.142.628,75 | 9.204 | 791 | 272 |
| Todas as linhas (sensibilidade) | 3.104.677.701,68 | 9.204 | 791 | 272 |

## Demais tipos de prestação entre APTO

Os outros tipos são apresentados separados de `Final`; o critério não infere qual entrega foi recebida por último.

| Tipo | Candidatos com linha | Sem linha | Linhas todas | Total todas (R$) | Linhas deduplicadas | Total deduplicado (R$) | Linhas excluídas | Candidatos afetados |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Final | 9.204 | 272 | 1.117.066 | 3.104.677.701,68 | 1.095.391 | 3.076.142.628,75 | 21.675 | 1.977 |
| Parcial | 91 | 9.385 | 3.753 | 12.097.667,18 | 3.745 | 12.088.486,56 | 8 | 6 |
| Regularização da Omissão | 83 | 9.393 | 3.088 | 9.322.087,49 | 3.060 | 9.217.902,19 | 28 | 7 |
| Relatório Financeiro | 50 | 9.426 | 505 | 1.182.886,44 | 501 | 1.181.586,44 | 4 | 2 |

Modelos completos, interações e sensibilidades OLS usam 9.202 candidaturas com despesas Final, votos e controles completos; 274 APTO ficam fora desses modelos: 272 sem linha Final, 2 com algum controle ausente (sobreposição 0; campos: age_at_election=2). Zero de despesa e 107 votos nominais iguais a zero são mantidos; ausência de linha não vira zero.
O modelo de comparação com ajuste apenas por UF/partido, sem idade, usa N=9.204.
Entre APTO, preservar todas as ocorrências soma R$ 3.104.677.701,68; a base principal deduplicada soma R$ 3.076.142.628,75. Diferença: R$ 28.535.072,93; não é classificação de gasto indevido.

## Modelos estimados

| Modelo | N | Família | Desfecho | Controles |
|---|---:|---|---|---|
| deduplicado_completo | 9.202 | logit fracionário (GLM Binomial) | participação de votos fracionária | UF, partido, idade na data da eleição, sexo, raça, escolaridade |
| todas_as_linhas_completo | 9.202 | logit fracionário (GLM Binomial) | participação de votos fracionária | UF, partido, idade na data da eleição, sexo, raça, escolaridade |
| deduplicado_uf_partido | 9.204 | logit fracionário (GLM Binomial) | participação de votos fracionária | UF, partido |
| deduplicado_interacao_sexo | 9.202 | logit fracionário (GLM Binomial) | participação de votos fracionária | UF, partido, idade na data da eleição, sexo, raça, escolaridade; interação despesa×mulher |
| todas_as_linhas_interacao_sexo | 9.202 | logit fracionário (GLM Binomial) | participação de votos fracionária | UF, partido, idade na data da eleição, sexo, raça, escolaridade; interação despesa×mulher |
| deduplicado_ols_participacao | 9.202 | OLS de sensibilidade | vote_share | UF, partido, idade na data da eleição, sexo, raça, escolaridade |
| deduplicado_votos_brutos_log1p | 9.202 | OLS de sensibilidade | log1p_nominal_votes | UF, partido, idade na data da eleição, sexo, raça, escolaridade |
Diagnósticos: 7/7 convergiram e todas as matrizes passaram a verificação de posto. Adequação, calibração e influência estão detalhadas abaixo; não há validação externa.

Na amostra completa, 9.202 candidaturas com sexo informado como feminino/masculino entram na interação; 0 com outra categoria/ausente ficam fora apenas dessa comparação.
No GLM completo, o coeficiente de `log1p(despesa)` foi 0,948 (IC 95% HC1 0,910 a 0,985) no cenário deduplicado e 0,949 (0,912 a 0,986) com todas as linhas. Ambos indicam associação positiva ajustada na escala logit; isso não demonstra que mais despesa cause mais votos.
Com ajuste somente por UF/partido, sem idade (N=9.204), o coeficiente de `log1p(despesa)` foi 0,972 (IC 95% HC1 0,935 a 1,008).
Na interação planejada, a diferença de inclinação mulheres–homens foi 0,195 na escala logit (IC 95% HC1 0,120 a 0,269). É uma diferença associativa, não causal.
Consulte `tse-2022-financial-model-estimates.csv` para todos os coeficientes e valores-p. GLM está em escala logit; OLS está em escala linear do desfecho informado. As estimativas são associativas, não causais.


## Participação prevista em níveis comparáveis de despesa

As previsões são médias padronizadas: fixa-se a despesa no nível indicado e calcula-se a participação de votos prevista para cada candidatura da distribuição comum de controles completos, depois se tira a média. São associações ajustadas, não previsões causais nem resultados eleitorais individuais. ICs de 95% pontuais pelo método delta, usando a covariância sanduíche HC1; não são intervalos para candidaturas individuais. A diferença entre cenários é apresentada em pontos percentuais como diferença de estimativas pontuais, sem IC próprio.

| Despesa contratada | Deduplicado: participação prevista (IC 95%) | Todas as linhas: participação prevista (IC 95%) | Diferença todas − deduplicado (p.p.) |
|---|---:|---:|---:|
| R$ 15.000,26 (Q25) | 0,0548% (0,0403–0,0694%) | 0,0551% (0,0404–0,0697%) | 0,00022 |
| R$ 65.138,05 (Mediana) | 0,1560% (0,1318–0,1803%) | 0,1562% (0,1319–0,1805%) | 0,00016 |
| R$ 299.927,00 (Q75) | 0,4296% (0,3985–0,4607%) | 0,4286% (0,3977–0,4596%) | -0,00098 |

## Comparação mulheres–homens dentro do suporte comum

A curva usa apenas despesas dentro da interseção das faixas P5–P95 dos dois grupos: R$ 0,00 a R$ 1.478.858,13. Em cada nível, fixa-se a despesa e alterna-se o sexo na mesma distribuição de controles; os ICs de 95% são pontuais e pelo método delta/HC1.
Na codificação, homens são a referência (indicador `female=0`); `log1p(despesa)` é a inclinação associativa masculina e `expense_x_female` acrescenta a diferença de inclinação para mulheres na escala logit. A inclinação feminina é a soma dos dois coeficientes. Como o logit inverso é não linear, o coeficiente de interação não equivale a uma porcentagem de gasto necessária; compare as curvas previstas.

| Despesa (R$) | Homens: participação prevista (IC 95%) | Mulheres: participação prevista (IC 95%) | Diferença mulheres − homens (p.p.) |
|---:|---:|---:|---:|
| 0,00 | 0,00% (0,00–0,00%) | 0,00% (0,00–0,00%) | -0,00 |
| 73.942,91 | 0,20% (0,16–0,23%) | 0,09% (0,06–0,13%) | -0,10 |
| 147.885,81 | 0,31% (0,27–0,34%) | 0,17% (0,13–0,21%) | -0,14 |
| 221.828,72 | 0,40% (0,36–0,44%) | 0,23% (0,19–0,28%) | -0,17 |
| 295.771,63 | 0,49% (0,45–0,53%) | 0,29% (0,24–0,34%) | -0,20 |
| 369.714,53 | 0,57% (0,52–0,61%) | 0,35% (0,30–0,40%) | -0,22 |
| 443.657,44 | 0,64% (0,60–0,69%) | 0,40% (0,35–0,45%) | -0,24 |
| 517.600,35 | 0,72% (0,67–0,77%) | 0,46% (0,40–0,51%) | -0,26 |
| 591.543,25 | 0,79% (0,74–0,84%) | 0,51% (0,45–0,56%) | -0,28 |
| 665.486,16 | 0,86% (0,80–0,92%) | 0,56% (0,50–0,62%) | -0,30 |
| 739.429,06 | 0,93% (0,87–0,99%) | 0,61% (0,55–0,68%) | -0,32 |
| 813.371,97 | 1,00% (0,93–1,06%) | 0,67% (0,60–0,73%) | -0,33 |
| 887.314,88 | 1,06% (0,99–1,14%) | 0,72% (0,65–0,79%) | -0,35 |
| 961.257,78 | 1,13% (1,05–1,21%) | 0,77% (0,69–0,85%) | -0,36 |
| 1.035.200,69 | 1,19% (1,11–1,28%) | 0,82% (0,74–0,90%) | -0,37 |
| 1.109.143,60 | 1,26% (1,17–1,35%) | 0,87% (0,78–0,96%) | -0,39 |
| 1.183.086,50 | 1,32% (1,23–1,42%) | 0,92% (0,83–1,02%) | -0,40 |
| 1.257.029,41 | 1,38% (1,28–1,48%) | 0,98% (0,87–1,08%) | -0,41 |
| 1.330.972,32 | 1,45% (1,34–1,55%) | 1,03% (0,92–1,14%) | -0,42 |
| 1.404.915,22 | 1,51% (1,39–1,62%) | 1,08% (0,96–1,20%) | -0,43 |
| 1.478.858,13 | 1,57% (1,45–1,69%) | 1,13% (1,01–1,25%) | -0,44 |

## Adequação do ajuste e influência

RMSE e MAE medem o erro médio entre participação observada e ajustada, em pontos percentuais; a calibração agrupa as previsões em decis e compara médias observadas e previstas. São verificações dentro da própria amostra, não validação fora da amostra. Influência: distância de Cook, alavancagem e DFBETA do coeficiente de despesa. O limite Cook > 4/N é apenas uma triagem heurística; nenhum caso foi excluído automaticamente.

| Cenário | RMSE (p.p.) | MAE (p.p.) | Maior diferença de calibração por decil (p.p.) | Cook > 4/N | Maior Cook | Maior alavancagem | Maior valor absoluto de DFBETA da despesa |
|---|---:|---:|---:|---:|---:|---:|---:|
| deduplicado_completo | 0,54 | 0,17 | 0,09 | 1 (limite 0,0004) | 0,0013 | 0,4110 | 0,4148 |
| todas_as_linhas_completo | 0,54 | 0,17 | 0,09 | 1 (limite 0,0004) | 0,0013 | 0,4092 | 0,4017 |

A sensibilidade abaixo remove somente candidaturas acima do P99 da despesa deduplicada, para verificar a estabilidade da inclinação de despesa. A amostra principal permanece intacta; a regra não identifica erro nem gasto indevido. As listas de calibração por decil e os 10 casos de maior Cook por cenário estão nos CSVs de diagnóstico.

| Cenário | Corte P99 (R$) | Excluídos na sensibilidade | N após corte | Coeficiente principal | Coeficiente sem cauda (IC 95% HC1) | Mudança |
|---|---:|---:|---:|---:|---:|---:|
| deduplicado | 2.938.976,94 | 92 | 9.110 | 0,948 | 0,946 (0,907–0,985) | -0,002 |
| todas_as_linhas | 2.938.976,94 | 92 | 9.110 | 0,949 | 0,947 (0,908–0,986) | -0,002 |

Arquivos: `tse-2022-predicted-expense-scenarios.csv`, `tse-2022-sex-interaction-curve.csv`, `tse-2022-model-calibration-deciles.csv`, `tse-2022-model-influence-top-candidates.csv` e `tse-2022-top-one-percent-expense-sensitivity.csv`. As curvas mostram médias previstas ajustadas; toda interpretação é associativa.


## Análise secundária acrescentada após os primeiros resultados: despesas e eleição

Esta análise secundária não substitui a análise principal de participação de votos. Eleito é definido pelos códigos oficiais 2 (ELEITO POR QP) e 3 (ELEITO POR MÉDIA); códigos 4 (NÃO ELEITO) e 5 (SUPLENTE) são não eleitos. Códigos ausentes, nulos ou outros não são forçados a nenhuma classe.
No recorte APTO com votos observados, 512 candidaturas têm código oficial eleito e 8.964 têm código não eleito; 0 têm código ausente/outro. A amostra completa usada nos modelos contém 510 eleitos e 8.692 não eleitos (9.202 candidaturas).
Foram excluídas da amostra completa de eleição 274 candidaturas com código oficial classificável por falta de despesa Final ou controle (272 sem despesa Final; 2 com controle ausente; sobreposição: 0); contagens de resultados no universo APTO com votos observados: código 2: 334, código 3: 178, código 4: 4.720, código 5: 4.244. Códigos fora da classificação: nenhum.
Comparação descritiva usa apenas as observações completas com resultado classificável; custo por voto é despesa declarada dividida por votos nominais, portanto fica indefinido para voto zero e não entra como preditor. A tabela mostra deduplicado e todas as linhas.

| Resultado | Base | N | Despesa média (R$) | Despesa mediana (R$) | N com votos positivos | N com custo indefinido por voto zero | Custo médio por voto (R$) | Custo mediano por voto (R$) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| eleitos | deduplicado | 510 | 1.870.634,12 | 1.881.139,39 | 510 | 0 | 23,03 | 17,79 |
| eleitos | todas_as_linhas | 510 | 1.897.720,77 | 1.901.988,18 | 510 | 0 | 23,32 | 18,14 |
| nao_eleitos | deduplicado | 8.692 | 243.811,43 | 52.996,07 | 8.588 | 104 | 110,19 | 46,75 |
| nao_eleitos | todas_as_linhas | 8.692 | 245.504,06 | 53.346,88 | 8.588 | 104 | 110,54 | 46,93 |

Modelos logísticos binários: log(1 + despesa contratada) com controles acordados — UF, partido, idade na eleição, sexo, raça e escolaridade — e erros-padrão HC1. Números abaixo são OR por unidade de log(1 + R$), não por real; votos/custo por voto não entram no modelo.

| Cenário | N | Eleitos | Não eleitos | OR da despesa | IC 95% | p |
|---|---:|---:|---:|---:|---:|---:|
| eleicao_deduplicado | 9.202 | 510 | 8.692 | 11,685 | 9,230–14,793 | <0,0001 |
| eleicao_todas_as_linhas | 9.202 | 510 | 8.692 | 11,884 | 9,353–15,101 | <0,0001 |

Proporção eleita por quartil de despesa deduplicada dentro de cada UF; empates recebem ordem determinística por classificação sequencial. CSV traz contagens por faixa/UF. A associação é observacional, não causal. Despesas são declaradas contratadas e não são necessariamente recursos públicos.

| UF | Faixa de despesa dentro da UF | Candidaturas | Eleitos | Proporção eleita |
|---|---:|---:|---:|---:|
| AC | Q1 | 30 | 0 | 0,00% |
| AC | Q2 | 31 | 0 | 0,00% |
| AC | Q3 | 30 | 0 | 0,00% |
| AC | Q4 | 31 | 8 | 25,81% |
| AL | Q1 | 36 | 0 | 0,00% |
| AL | Q2 | 36 | 0 | 0,00% |
| AL | Q3 | 36 | 1 | 2,78% |
| AL | Q4 | 36 | 8 | 22,22% |
| AM | Q1 | 34 | 0 | 0,00% |
| AM | Q2 | 34 | 0 | 0,00% |
| AM | Q3 | 34 | 0 | 0,00% |
| AM | Q4 | 35 | 8 | 22,86% |
| AP | Q1 | 30 | 0 | 0,00% |
| AP | Q2 | 31 | 1 | 3,23% |
| AP | Q3 | 30 | 1 | 3,33% |
| AP | Q4 | 31 | 6 | 19,35% |
| BA | Q1 | 162 | 0 | 0,00% |
| BA | Q2 | 163 | 0 | 0,00% |
| BA | Q3 | 163 | 0 | 0,00% |
| BA | Q4 | 163 | 38 | 23,31% |
| CE | Q1 | 81 | 0 | 0,00% |
| CE | Q2 | 81 | 0 | 0,00% |
| CE | Q3 | 81 | 0 | 0,00% |
| CE | Q4 | 82 | 22 | 26,83% |
| DF | Q1 | 48 | 0 | 0,00% |
| DF | Q2 | 48 | 0 | 0,00% |
| DF | Q3 | 48 | 0 | 0,00% |
| DF | Q4 | 48 | 8 | 16,67% |
| ES | Q1 | 45 | 0 | 0,00% |
| ES | Q2 | 45 | 0 | 0,00% |
| ES | Q3 | 45 | 1 | 2,22% |
| ES | Q4 | 45 | 9 | 20,00% |
| GO | Q1 | 83 | 0 | 0,00% |
| GO | Q2 | 84 | 0 | 0,00% |
| GO | Q3 | 83 | 1 | 1,20% |
| GO | Q4 | 84 | 16 | 19,05% |
| MA | Q1 | 77 | 0 | 0,00% |
| MA | Q2 | 78 | 0 | 0,00% |
| MA | Q3 | 78 | 0 | 0,00% |
| MA | Q4 | 78 | 18 | 23,08% |
| MG | Q1 | 248 | 0 | 0,00% |
| MG | Q2 | 248 | 0 | 0,00% |
| MG | Q3 | 248 | 0 | 0,00% |
| MG | Q4 | 249 | 53 | 21,29% |
| MS | Q1 | 36 | 0 | 0,00% |
| MS | Q2 | 37 | 0 | 0,00% |
| MS | Q3 | 37 | 0 | 0,00% |
| MS | Q4 | 37 | 8 | 21,62% |
| MT | Q1 | 36 | 0 | 0,00% |
| MT | Q2 | 37 | 0 | 0,00% |
| MT | Q3 | 37 | 0 | 0,00% |
| MT | Q4 | 37 | 8 | 21,62% |
| PA | Q1 | 70 | 0 | 0,00% |
| PA | Q2 | 70 | 0 | 0,00% |
| PA | Q3 | 70 | 0 | 0,00% |
| PA | Q4 | 71 | 17 | 23,94% |
| PB | Q1 | 43 | 0 | 0,00% |
| PB | Q2 | 44 | 0 | 0,00% |
| PB | Q3 | 44 | 0 | 0,00% |
| PB | Q4 | 44 | 12 | 27,27% |
| PE | Q1 | 99 | 0 | 0,00% |
| PE | Q2 | 100 | 0 | 0,00% |
| PE | Q3 | 100 | 1 | 1,00% |
| PE | Q4 | 100 | 24 | 24,00% |
| PI | Q1 | 35 | 0 | 0,00% |
| PI | Q2 | 36 | 0 | 0,00% |
| PI | Q3 | 35 | 0 | 0,00% |
| PI | Q4 | 36 | 10 | 27,78% |
| PR | Q1 | 143 | 0 | 0,00% |
| PR | Q2 | 143 | 0 | 0,00% |
| PR | Q3 | 143 | 0 | 0,00% |
| PR | Q4 | 144 | 29 | 20,14% |
| RJ | Q1 | 244 | 0 | 0,00% |
| RJ | Q2 | 244 | 0 | 0,00% |
| RJ | Q3 | 244 | 2 | 0,82% |
| RJ | Q4 | 245 | 44 | 17,96% |
| RN | Q1 | 41 | 0 | 0,00% |
| RN | Q2 | 41 | 0 | 0,00% |
| RN | Q3 | 41 | 1 | 2,44% |
| RN | Q4 | 41 | 7 | 17,07% |
| RO | Q1 | 34 | 0 | 0,00% |
| RO | Q2 | 35 | 1 | 2,86% |
| RO | Q3 | 35 | 0 | 0,00% |
| RO | Q4 | 35 | 7 | 20,00% |
| RR | Q1 | 33 | 0 | 0,00% |
| RR | Q2 | 34 | 0 | 0,00% |
| RR | Q3 | 34 | 1 | 2,94% |
| RR | Q4 | 34 | 7 | 20,59% |
| RS | Q1 | 124 | 0 | 0,00% |
| RS | Q2 | 125 | 0 | 0,00% |
| RS | Q3 | 124 | 1 | 0,81% |
| RS | Q4 | 125 | 30 | 24,00% |
| SC | Q1 | 71 | 0 | 0,00% |
| SC | Q2 | 71 | 0 | 0,00% |
| SC | Q3 | 71 | 0 | 0,00% |
| SC | Q4 | 71 | 16 | 22,54% |
| SE | Q1 | 35 | 0 | 0,00% |
| SE | Q2 | 36 | 0 | 0,00% |
| SE | Q3 | 35 | 0 | 0,00% |
| SE | Q4 | 36 | 8 | 22,22% |
| SP | Q1 | 336 | 0 | 0,00% |
| SP | Q2 | 336 | 0 | 0,00% |
| SP | Q3 | 336 | 1 | 0,30% |
| SP | Q4 | 337 | 68 | 20,18% |
| TO | Q1 | 35 | 0 | 0,00% |
| TO | Q2 | 36 | 0 | 0,00% |
| TO | Q3 | 36 | 0 | 0,00% |
| TO | Q4 | 36 | 8 | 22,22% |

Artefatos: `tse-2022-election-expense-comparison.csv`, `tse-2022-election-expense-models.csv` e `tse-2022-election-rate-by-uf-expense-band.csv`.


## Análise secundária acrescentada após os primeiros resultados: raça/cor

A análise principal de votos permanece inalterada; raça/cor já era um controle categórico nela, mas isso não testa se a associação entre despesa e votação varia entre grupos. Esta análise binária adicional compara autodeclarações `BRANCA` com `PRETA`+`PARDA`. As demais categorias permanecem na base principal e são excluídas apenas desta comparação.
Entre as 9.476 candidaturas APTO estão 9.476 com votos observados. As categorias autodeclaradas, contadas antes da restrição por votos, são: AMARELA: 39, BRANCA: 4.795, INDÍGENA: 50, NÃO DIVULGÁVEL: 2, NÃO INFORMADO: 56, PARDA: 3.214, PRETA: 1.320, (ausente): 0. A comparação considera 9.329 candidaturas BRANCA/PRETA/PARDA: brancas 4.795, pretas+pardas 4.534. Fora dela, sem recodificação: AMARELA: 39, INDÍGENA: 50, NÃO DIVULGÁVEL: 2, NÃO INFORMADO: 56, (ausente): 0.
Das candidaturas binárias APTO, 9.329 têm voto/denominador observado; 0 foram excluídas por ausência de voto/denominador. A coorte completa pareada nas duas medidas de despesa e controles tem N=9.062: brancas 4.681, pretas+pardas 4.381. Das observadas, 267 não tinham uma das despesas Final e 0 tinham controle ausente; sobreposição 0.
A tabela descritiva usa essa mesma coorte em ambos os cenários. Medianas e intervalos interquartis resumem despesa contratada, votos nominais e participação nos votos válidos da UF. A proporção eleita tem como denominador somente resultados classificáveis (códigos 2, 3, 4 ou 5); ausentes/outros resultados aparecem à parte.

| Grupo | Despesa Final | N | Despesa mediana (Q25–Q75, R$) | Votos nominais mediana (Q25–Q75) | Votos válidos da UF: mediana (Q25–Q75) | Eleitos / classificáveis | Proporção eleita | Resultado ausente/outro |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Brancas | deduplicado | 4.681 | 92.358,53 (20.000,00–407.455,60) | 1.716 (478–8.321) | 0,0292% (0,0065–0,1689%) | 363/4.681 | 7,75% | 0 |
| Brancas | todas_as_linhas | 4.681 | 94.000,00 (20.000,00–408.559,75) | 1.716 (478–8.321) | 0,0292% (0,0065–0,1689%) | 363/4.681 | 7,75% | 0 |
| Pretas + pardas | deduplicado | 4.381 | 49.996,85 (11.560,00–205.251,50) | 818 (278–2.957) | 0,0179% (0,0050–0,0813%) | 139/4.381 | 3,17% | 0 |
| Pretas + pardas | todas_as_linhas | 4.381 | 50.000,00 (11.565,85–205.686,59) | 818 (278–2.957) | 0,0179% (0,0050–0,0813%) | 139/4.381 | 3,17% | 0 |

Interação ajustada: GLM Binomial/logit fracionário para participação de votos, com `log1p(despesa em R$)`, indicador pretas+pardas e interação entre os dois; referência: brancas. Controles: UF, partido, idade na eleição, sexo e escolaridade; erros-padrão HC1. Deduplicado é principal; todas as linhas, sensibilidade. Custo por voto não é preditor porque usa votos no denominador.

| Cenário | N | Interação despesa×pretas+pardas (logit) | IC 95% HC1 | p |
|---|---:|---:|---:|---:|
| deduplicado | 9.062 | 0,0222 | -0,0434–0,0879 | 0,5068 |
| todas_as_linhas | 9.062 | 0,0229 | -0,0425–0,0883 | 0,4920 |
O coeficiente de interação resume a diferença entre inclinações na escala logit; não é uma diferença causal nem uma mudança direta em pontos percentuais. Os demais coeficientes e seus intervalos estão no CSV.
No cenário deduplicado, o IC 95% inclui zero; estes dados não distinguem com clareza as inclinações dos grupos.
No cenário todas_as_linhas, o IC 95% inclui zero; estes dados não distinguem com clareza as inclinações dos grupos.

Curvas padronizadas usam os mesmos perfis de UF, partido, idade, sexo e escolaridade em ambos os grupos, mas apenas em faixas de despesa com suporte contextual pré-especificado. Sombras mostram ICs pontuais de 95% pelo método delta/HC1; não são intervalos individuais.
Suporte deduplicado: 74 células UF×partido elegíveis (N≥10 em cada grupo), cobrindo 38,3% das brancas e 31,8% das pretas+pardas. A maior cobertura de qualquer ponto candidato foi 24,9% e 21,2%, respectivamente; 0 pontos publicados.
Sem curva por suporte insuficiente: cobertura das células com suporte ficou abaixo de 80% em pelo menos um grupo. Não houve extrapolação.
Suporte todas_as_linhas: 74 células UF×partido elegíveis (N≥10 em cada grupo), cobrindo 38,3% das brancas e 31,8% das pretas+pardas. A maior cobertura de qualquer ponto candidato foi 24,9% e 20,5%, respectivamente; 0 pontos publicados.
Sem curva por suporte insuficiente: cobertura das células com suporte ficou abaixo de 80% em pelo menos um grupo. Não houve extrapolação.

| Cenário | Despesa (R$) | Brancas: participação prevista (IC 95%) | Pretas+pardas: participação prevista (IC 95%) | Cobertura brancas | Cobertura pretas+pardas |
|---|---:|---:|---:|---:|---:|

![Curva raça/cor — despesas deduplicadas](tse-2022-race-interaction-curve-deduplicado.svg)

![Curva raça/cor — todas as linhas](tse-2022-race-interaction-curve-todas-as-linhas.svg)

A tabela de suporte apresenta contagens, faixas P10–P90 e proporção da coorte por UF, partido e célula UF×partido; a tabela de suporte por ponto registra a cobertura usada para aceitar ou suprimir cada ponto. Diferenças são associações ajustadas, não efeitos causais ou prova de discriminação. Despesa declarada contratada não significa pagamento efetivo nem recurso necessariamente público.
A comparação financeira com 2026 permanece adiada. Depois de 3 de novembro, verificar novamente disponibilidade e cobertura das prestações `Final`; a data não aprova automaticamente a base.

Artefatos: `tse-2022-race-population-counts.csv`, `tse-2022-race-group-descriptives.csv`, `tse-2022-race-interaction-coefficients.csv`, `tse-2022-race-interaction-curve.csv`, `tse-2022-race-curve-support.csv` e `tse-2022-race-support-by-uf-party.csv`.

## INAPTO — levantamento separado por tipo de prestação

Entre 1.154 candidaturas INAPTO, 992 têm ao menos uma ocorrência e 162 não têm linha de despesa na base. A tabela usa ocorrências intactas e também mostra o cenário deduplicado; não mistura INAPTO à regressão APTO.

| Tipo | Candidatos com linha | Sem linha | Linhas todas | Linhas zero | Total todas (R$) | Linhas deduplicadas | Total deduplicado (R$) | Linhas excluídas | Candidatos afetados |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Final | 942 | 212 | 14.515 | 687 | 38.261.274,82 | 14.356 | 37.998.012,02 | 159 | 34 |
| Parcial | 19 | 1.135 | 40 | 15 | 126.858,50 | 40 | 126.858,50 | 0 | 0 |
| Regularização da Omissão | 20 | 1.134 | 289 | 18 | 302.225,69 | 289 | 302.225,69 | 0 | 0 |
| Relatório Financeiro | 11 | 1.143 | 19 | 10 | 29.410,00 | 19 | 29.410,00 | 0 | 0 |

## Pagamentos e limitações

não integrado: 29 membros de despesas pagas estão no ZIP congelado; não há tabela de pagamentos na base derivada, e essa integração complementar não bloqueia a análise contratada.
- A situação APTO é a registrada no snapshot; não prova elegibilidade jurídica na data da eleição.
- Despesas são valores declarados contratados, não pagamentos efetivos.
- Deduplicar igualdade integral nas 53 colunas originais é uma escolha metodológica; não confirma identidade econômica das repetições.
- Todas as linhas permanecem como sensibilidade. Diferença não significa desperdício ou irregularidade.
- Modelos observacionais não estimam efeito causal; qualidade do candidato, incumbência, apoio, geografia e competitividade podem confundir a associação.
- Votos por UF são agregados eleitorais; os resultados não descrevem decisões individuais de eleitores.

## Reprodução

```sh
python -m tse_pilot analyze --database data/derived/2022/pilot.sqlite --validation data/derived/2022/validation.json --output reports
```

A saída JSON registra contagens, modelos, metadados de execução e limitações; os coeficientes e o levantamento INAPTO também são arquivos CSV.
