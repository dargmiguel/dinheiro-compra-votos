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

A regressão usa 9.202 candidaturas com despesas Final observadas, votos e controles completos; 274 APTO ficam fora: 272 sem linha Final, 2 com algum controle ausente (sobreposição 0; campos: age_at_election=2). Zero de despesa e 107 votos nominais iguais a zero são mantidos; ausência de linha não vira zero.
Entre APTO, preservar todas as ocorrências soma R$ 3.104.677.701,68; a base principal deduplicada soma R$ 3.076.142.628,75. Diferença: R$ 28.535.072,93; não é classificação de gasto indevido.

## Modelos estimados

| Modelo | N | Família | Desfecho | Controles |
|---|---:|---|---|---|
| deduplicado_completo | 9.202 | quasi-binomial/logit para resposta fracionária | participação de votos fracionária | UF, partido, idade na data da eleição, sexo, raça, escolaridade |
| todas_as_linhas_completo | 9.202 | quasi-binomial/logit para resposta fracionária | participação de votos fracionária | UF, partido, idade na data da eleição, sexo, raça, escolaridade |
| deduplicado_uf_partido | 9.202 | quasi-binomial/logit para resposta fracionária | participação de votos fracionária | UF, partido, idade na data da eleição |
| deduplicado_interacao_sexo | 9.202 | quasi-binomial/logit para resposta fracionária | participação de votos fracionária | UF, partido, idade na data da eleição, sexo, raça, escolaridade; interação despesa×mulher |
| todas_as_linhas_interacao_sexo | 9.202 | quasi-binomial/logit para resposta fracionária | participação de votos fracionária | UF, partido, idade na data da eleição, sexo, raça, escolaridade; interação despesa×mulher |
| deduplicado_ols_participacao | 9.202 | OLS de sensibilidade | vote_share | UF, partido, idade na data da eleição, sexo, raça, escolaridade |
| deduplicado_votos_brutos_log1p | 9.202 | OLS de sensibilidade | log1p_nominal_votes | UF, partido, idade na data da eleição, sexo, raça, escolaridade |
Diagnóstico dos modelos: 7/7 convergiram; verificações de posto completo passaram. Deviance/AIC dos GLMs e R²/RMSE das sensibilidades OLS estão no JSON.

Na amostra completa, 9.202 candidaturas com sexo informado como feminino/masculino entram na interação; 0 com outra categoria/ausente ficam fora apenas dessa comparação.
No GLM completo, o coeficiente de `log1p(despesa)` foi 0,948 (IC 95% HC1 0,910 a 0,985) no cenário deduplicado e 0,949 (0,912 a 0,986) com todas as linhas. Ambos indicam associação positiva ajustada na escala logit; isso não demonstra que mais despesa cause mais votos.
Na interação planejada, a diferença de inclinação mulheres–homens foi 0,195 na escala logit (IC 95% HC1 0,120 a 0,269). É uma diferença associativa, não causal.
Consulte `tse-2022-financial-model-estimates.csv` para todos os coeficientes e valores-p. GLM está em escala logit; OLS está em escala linear do desfecho informado. As estimativas são associativas, não causais.

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
