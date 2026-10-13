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
