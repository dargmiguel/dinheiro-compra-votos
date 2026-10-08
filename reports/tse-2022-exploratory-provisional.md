# Análise exploratória provisória — TSE 2022

> **EXPLORATÓRIA / PROVISÓRIA. Não é base financeira aprovada.**

## Comando separado

A análise é gerada por um comando que não chama `run_pipeline`, não altera `data/derived/2022/` e só aceita uma validação cujo estado esteja `blocked` exclusivamente por `duplicate_expense_rows`:

```text
python -m tse_pilot explore \
  --manifest data/manifests/manifest-20261008T154908Z.json \
  --validation data/derived/2022/validation.json \
  --output data/exploratory/2022
```

Os artefatos são gerados em `data/exploratory/2022/`, diretório separado e ignorado pelo Git. O marcador `exploratory_only`, `approval_status = blocked` e `not_approved = true` é gravado em `exploratory_metadata.json`.

## População

A população é formada por candidatos com `CD_SITUACAO_CANDIDATURA = 12` (`APTO`) no snapshot de candidaturas gerado após a eleição. Não é uma reconstrução da situação no dia da votação.

| Categoria | Candidatos |
|---|---:|
| Registros de deputado federal no snapshot | 10.630 |
| `APTO`, incluídos | 9.476 |
| `INAPTO`, fora da população principal | 1.154 |

Os `INAPTO` não são apagados do inventário; ficam fora apenas da população exploratória. Situação eleitoral (`eleito`, `não eleito`, `suplente`) não é usada como filtro de validade.

## Medidas e recorte

- Despesas: somente `TP_PRESTACAO_CONTAS = Final`.
- Nome da medida: **despesas contratadas declaradas no snapshot**.
- Não afirmar equivalência com `Gastos Financeiros`.
- Votos: soma de `QT_VOTOS_NOMINAIS_VALIDOS`.
- Ausência permanece ausente.
- Zero observado permanece zero.
- Pontos ausentes não são convertidos em zero para os gráficos.
- Os eixos dos gráficos usam `log10(1 + x)` somente para visualização; CSVs mantêm os valores originais.

No recorte `Final` de candidatos `APTO`:

| Observação | Candidatos |
|---|---:|
| Despesa observada | 9.204 |
| Despesa observada igual a zero | 791 |
| Despesa ausente | 272 |
| Voto observado | 9.476 |
| Voto observado igual a zero | 107 |
| Voto ausente | 0 |

Foram processadas 1.117.066 linhas financeiras `Final` para a população `APTO`.

## Cenários

### A — preservar todas as linhas

Mantém todas as linhas `Final` observadas para candidatos `APTO`.

- Total: **R$ 3.104.677.701,68**
- Mediana por candidato com despesa observada: **R$ 65.633,02**
- Percentil 90: **R$ 1.099.850,41**
- Percentil 99: **R$ 2.974.256,90**

### B — remover somente repetições completas exatas

Mantém a primeira ocorrência de cada assinatura completa e remove apenas ocorrências posteriores textualmente idênticas. Isso é um cenário de sensibilidade, não uma decisão de deduplicação.

- Total: **R$ 3.076.142.628,75**
- Mediana por candidato com despesa observada: **R$ 65.342,28**
- Percentil 90: **R$ 1.093.172,83**
- Percentil 99: **R$ 2.938.949,67**

### Diferença

- Repetições completas exatas no recorte: **21.675** ocorrências excedentes.
- Diferença total A − B: **R$ 28.535.072,93**.
- Candidatos com valores diferentes: **1.977 de 9.476**.
- Diferença relativa do total B sobre A: aproximadamente **0,9189%**.

Maiores diferenças absolutas observadas:

| SQ_CANDIDATO | Candidato | UF | Diferença | Relativa a A | Repetições |
|---|---|---|---:|---:|---:|
| `60001603454` | Denis Anderson da Rocha Bezerra | CE | R$ 560.938,05 | 20,7571% | 178 |
| `130001607568` | Weliton Fernandes Prado | MG | R$ 551.249,38 | 18,9108% | 162 |
| `190001596770` | Soraya Alencar dos Santos | RJ | R$ 521.366,60 | 20,8648% | 79 |
| `190001605591` | Luiz Antonio de Souza Teixeira Junior | RJ | R$ 429.228,50 | 34,3724% | 299 |
| `190001619522` | Daniela Moté de Souza Carneiro | RJ | R$ 335.534,42 | 10,8921% | 74 |

A estabilidade de 7.499 candidatos entre os cenários é apenas uma medida de sensibilidade. Não prova que preservar ou remover seja correto.

## Associações descritivas por UF

O comando gera `exploratory_uf_associations.csv` com duas linhas por UF, uma para cada cenário. Para cada UF são preservados:

- população de candidatos `APTO`;
- despesas observadas, zeros e ausências;
- votos observados, zeros e ausências;
- número de pares completos;
- totais e medianas;
- correlação de Pearson entre despesa e votos nos pares completos.

A correlação inclui zeros observados e exclui somente ausências. É uma associação descritiva, não uma estimativa causal e não foi usada para selecionar cenário.

Também são gerados:

- `plots/exploratory_expense_vs_votes_a.svg`;
- `plots/exploratory_expense_vs_votes_b.svg`;
- `plots/exploratory_distributions.svg`;
- `plots/exploratory_uf_expense_totals.svg`;
- `exploratory_scenario_comparison.csv`, com valores A/B por candidato;
- `exploratory_candidates.csv`, com população, situação, observações e votos;
- `exploratory_scenario_a_preserve_all.csv`;
- `exploratory_scenario_b_remove_exact_repeats.csv`.

## Bloqueios mantidos

A base financeira aprovada continua bloqueada. O comando exploratório:

- exige `validation.json` bloqueado;
- recusa validações com falhas críticas além de `duplicate_expense_rows`;
- não cria `analytical_base.csv`;
- não cria `expense_aggregate.csv` aprovado;
- não cria `vote_aggregate.csv` aprovado;
- não remove nem substitui artefatos de `data/derived/2022/`;
- não transforma a soma do cenário A ou B em base aprovada.

A entrega `Final` foi reconhecida pelo campo textual `TP_PRESTACAO_CONTAS`. O comando não determina se é a última entrega recebida com sucesso, não trata retificações como substituições e não calcula dívida, despesas pagas, estimáveis ou exclusões de DRD.

## Testes

A suíte tem **12 testes aprovados**, incluindo:

- geração simultânea dos dois cenários;
- preservação de zero observado;
- preservação de ausência;
- marcação explícita como `exploratory_only`;
- ausência de artefatos com nomes de base aprovada;
- recusa de execução quando `validation.json` está `approved`;
- preservação de um artefato sentinela no diretório de produção.
