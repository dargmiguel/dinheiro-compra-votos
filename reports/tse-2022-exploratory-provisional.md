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

## Custo exploratório por voto

O custo por voto é calculado somente para candidatos com despesa observada e votos nominais válidos maiores que zero. Zero de despesa observado produz R$ 0,00 por voto; despesa ausente continua fora do quociente. O CSV por candidato apresenta `custo_por_voto_reais`, com custo em reais por voto.

| Cenário | Candidatos com custo | Despesa dos pares completos | Votos dos pares completos | Custo agregado | Mediana | P90 | P99 |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 9.100 | R$ 3.092.766.046,77 | 103.816.598 | R$ 29,79 | R$ 43,11 | R$ 227,29 | R$ 1.042,57 |
| B | 9.100 | R$ 3.064.276.239,94 | 103.816.598 | R$ 29,52 | R$ 42,88 | R$ 227,17 | R$ 1.042,57 |

O custo agregado é `soma das despesas / soma dos votos` nos pares completos; não é a média simples do custo individual. Não há custo definido para candidato com despesa ausente ou com zero votos.
O valor agregado do CSV é **R$ 29,79 por voto** no cenário A e **R$ 29,52 por voto** no cenário B. O campo antigo em centavos por voto (2.979,07 centavos = R$ 29,79) foi removido para evitar a leitura errada de escala.

As diferenças A−B dependem do denominador. Entre todas as despesas observadas de candidatos `APTO` com entrega `Final`, a diferença é **R$ 28.535.072,93**. Nos 9.100 candidatos com despesa observada e votos positivos usados no custo por voto, é **R$ 28.489.806,83**. A diferença de **R$ 45.266,10** vem do A−B dos candidatos com votação observada igual a zero (107 candidatos), excluídos do recorte de custo; não há votos ausentes.

Para abrir os dados: `data/exploratory/2022/exploratory_report.md` traz o relatório completo; os CSVs estão em `data/exploratory/2022/` e os SVGs em `data/exploratory/2022/plots/`. Excel, LibreOffice Calc ou Google Sheets servem para inspeção; use a importação CSV com vírgula como separador e ponto como separador decimal. Os cabeçalhos agora estão em português.

Para uma leitura puramente agregada usando todo o voto observado do universo `APTO`, inclusive despesas de candidatos com zero votos, os quocientes seriam R$ 29,66 no cenário A e R$ 29,39 no cenário B. Essa leitura tem outra população de denominador e não substitui a regra por pares completos.

## Associação entre despesas e votação por UF

Spearman foi calculado entre candidatos dentro de cada UF, separadamente nos cenários A e B. São usados pares com despesa e votação observadas; zeros observados permanecem incluídos e apenas ausências são excluídas. O custo por voto não é usado para explicar votos nem entra na associação.

Cobertura: **9.204 pares completos em cada cenário**, distribuídos por **27 de 27 UFs** com coeficiente definido. Há 272 despesas ausentes, 791 despesas observadas iguais a zero e 107 candidatos com votação observada igual a zero; esses zeros permanecem na correlação. O coeficiente varia de **0,722880 a 0,856801** no cenário A e de **0,722059 a 0,857010** no cenário B. A variação de Spearman entre B e A (`B − A`) vai de **−0,002723 a +0,000209**; diminui em 23 UFs e aumenta em 4. O maior deslocamento absoluto é **0,002723** (AP). Todas as associações por UF deste recorte são positivas, mas descritivas; isso não identifica causalidade nem escolhe o tratamento correto das repetições.

| UF | Pares A/B | Spearman A | Spearman B | Δ Spearman (B−A) |
|---|---:|---:|---:|---:|
| AC | 122 | 0,854004 | 0,853977 | −0,000027 |
| AL | 144 | 0,856801 | 0,857010 | +0,000209 |
| AM | 137 | 0,745740 | 0,744649 | −0,001091 |
| AP | 122 | 0,758030 | 0,755307 | −0,002723 |
| BA | 651 | 0,745040 | 0,744293 | −0,000747 |
| CE | 325 | 0,807492 | 0,807562 | +0,000070 |
| DF | 193 | 0,793193 | 0,792530 | −0,000663 |
| ES | 180 | 0,826587 | 0,824303 | −0,002284 |
| GO | 334 | 0,763749 | 0,763615 | −0,000134 |
| MA | 311 | 0,788846 | 0,788648 | −0,000198 |
| MG | 993 | 0,792175 | 0,792232 | +0,000057 |
| MS | 147 | 0,778547 | 0,778184 | −0,000363 |
| MT | 147 | 0,853917 | 0,853715 | −0,000202 |
| PA | 281 | 0,784209 | 0,783526 | −0,000683 |
| PB | 175 | 0,783294 | 0,783090 | −0,000204 |
| PE | 399 | 0,777498 | 0,777636 | +0,000138 |
| PI | 142 | 0,804026 | 0,802331 | −0,001695 |
| PR | 573 | 0,792704 | 0,792257 | −0,000447 |
| RJ | 977 | 0,722880 | 0,722059 | −0,000821 |
| RN | 164 | 0,808563 | 0,807921 | −0,000642 |
| RO | 139 | 0,815481 | 0,815121 | −0,000360 |
| RR | 135 | 0,824214 | 0,822871 | −0,001343 |
| RS | 498 | 0,732349 | 0,732136 | −0,000213 |
| SC | 284 | 0,737360 | 0,736419 | −0,000941 |
| SE | 142 | 0,761607 | 0,760969 | −0,000638 |
| SP | 1.346 | 0,788043 | 0,787376 | −0,000667 |
| TO | 143 | 0,796510 | 0,795796 | −0,000714 |

`exploratory_uf_associations.csv` mantém também a correlação de Pearson como medida descritiva complementar, além das contagens, zeros, ausências, totais e medianas. O gráfico `plots/exploratory_uf_spearman_by_scenario.svg` compara Spearman por UF e mostra o número de pares completos nas dicas dos pontos. Coeficientes indefinidos seriam deixados em branco quando houvesse menos de dois pares ou variância nula.

Também são gerados:

- `plots/exploratory_expense_vs_votes_a.svg`;
- `plots/exploratory_expense_vs_votes_b.svg`;
- `plots/exploratory_uf_spearman_by_scenario.svg`;
- `plots/exploratory_distributions.svg`;
- `plots/exploratory_uf_expense_totals.svg`;
- `exploratory_scenario_comparison.csv`, com valores A/B e custo por voto por candidato;
- `exploratory_cost_per_vote.csv`, com o custo agregado e percentis por cenário;
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

O conjunto completo tem **19 testes aprovados**, incluindo:

- geração dos dois cenários e comparação dos mesmos candidatos;
- zero de despesa com votos positivos e custo zero;
- voto zero e despesa ausente sem conversão em zero;
- marcação exploratória e preservação da base bloqueada;
- junção por chave quando a ordem difere e rejeição de duplicatas, comprimentos ou chaves incompatíveis;
- média de postos correta em empates de Spearman.
