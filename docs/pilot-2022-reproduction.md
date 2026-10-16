# Piloto TSE 2022: reprodução

Este piloto consolida, em escopo Brasil / todas as UFs, candidaturas a deputado federal, despesas contratadas declaradas e votação nominal do primeiro turno de 2022. O escopo não inclui 2026, redes sociais, dashboard ou modelo preditivo.
Disponibilidade de dados de redes sociais **não é requisito para concluir o piloto de financiamento TSE 2022**. O piloto fecha a viabilidade apenas para candidaturas, prestações de contas e votação no TSE; a camada de atenção é posterior e condicional à disponibilidade, permissão e comparabilidade temporal de cada fonte. A ausência dessa camada não impede a conclusão do piloto financeiro, nem autoriza preencher cobertura desconhecida como zero.

## Fontes congeladas

`data/inventory-2022.json` registra os quatro recursos oficiais do TSE, inclusive o total partidário por município/zona usado para formar o denominador oficial com votos nominais e de legenda. O comando de aquisição baixa os ZIPs originais sem alterar o conteúdo e cria um manifesto em `data/manifests/` com URL, identificador do recurso, horário de download, `ETag`, `Last-Modified`, tamanho, SHA-256 e `version_id`.

O snapshot executado é `manifest-20261008T154908Z.json`. O ZIP de totais partidários mede 26.150.488 bytes e tem SHA-256 `4f6325c4a496cce00220e197ef3dd2dcd331c44b42e706194dd9e89294d68d9f`. Arquivos brutos e a base derivada não entram no Git; manifesto, layout e resultados agregados entram.

## Comandos

Na raiz do repositório, com Python 3.11.x e UV 0.9.15 ou superior. Instale o UV pelo [guia oficial](https://docs.astral.sh/uv/getting-started/installation/) e prepare o ambiente a partir do lock:

```text
uv sync --locked
uv run --locked python -m unittest discover -s tests -v
uv run --locked python -m tse_pilot inventory --data-root data
uv run --locked python -m tse_pilot acquire --data-root data
uv run --locked python -m tse_pilot freeze-votes --manifest data/manifests/manifest-<snapshot>.json
uv run --locked python -m tse_pilot inspect --manifest data/manifests/manifest-<snapshot>.json --output data/layout-2022.json
uv run --locked python -m tse_pilot run --manifest data/manifests/manifest-<snapshot>.json --output data/derived/2022
uv run --locked python -m tse_pilot analyze --database data/derived/2022/pilot.sqlite --validation data/derived/2022/validation.json --output reports
uv run --locked python -m tse_pilot expense-temporal --database data/derived/2022/pilot.sqlite --output reports
uv run --locked python -m tse_pilot funding-source --database data/derived/2022/pilot.sqlite --archive data/raw/2022/20261008T154908Z/prestacao_de_contas_eleitorais_candidatos_2022.zip --output reports
uv run --locked python -m tse_pilot duplicates --database data/derived/2022/pilot.sqlite --output reports/tse-2022-duplicate-diagnostics.json
```

`freeze-votes` congela incrementalmente o recurso oficial de total partidário no manifesto; `run` exige que ele esteja presente, filtra eleição 2022/turno 1/deputado federal e calcula o denominador por UF antes dos filtros `APTO` ou `Final`. O denominador usa o membro nacional `BRASIL` uma vez, nunca somado aos membros `BR`/UF. Confere legenda total contra seus dois componentes e reconcilia voto nominal oficial com a soma de votos válidos por candidato em cada UF.

`run` lê os ZIPs por streaming, preserva cada ocorrência original em `expense_occurrences` e materializa a base principal com deduplicação de linhas iguais nos 53 campos originais, dentro do mesmo snapshot e membro. `duplicates` mede exclusões, candidatos afetados e diferenças financeiras sem classificá-las como desperdício ou gasto indevido; também exporta cada ocorrência excluída e a referência mantida para `reports/tse-2022-dedup-exclusions.csv`.

`analyze` exige validação aprovada e denominadores reconciliados nas 27 UFs. Executa primeiro o GLM fracionário da análise principal de participação de votos e suas sensibilidades. Uma análise secundária, acrescentada após os primeiros resultados, classifica eleição pelos códigos oficiais 2 (`ELEITO POR QP`) e 3 (`ELEITO POR MÉDIA`), compara despesas/custo por voto, calcula proporções eleitas por quartil de despesa dentro da UF e estima modelos logísticos com UF, partido, idade, sexo, raça e escolaridade. Códigos 4 (`NÃO ELEITO`) e 5 (`SUPLENTE`) formam o grupo não eleito; códigos ausentes/nulos ou outros ficam excluídos e contados. Custo por voto não é preditor. A análise é associativa, não causal; despesa contratada declarada não significa necessariamente dinheiro público.

Depois dos resultados iniciais, `analyze` acrescenta uma comparação secundária de autodeclarações `BRANCA` contra `PRETA`+`PARDA`; `AMARELA`, `INDÍGENA`, `NÃO INFORMADO`, `NÃO DIVULGÁVEL` e ausentes ficam fora somente dessa comparação, preservados na base principal e contados separadamente. A interação entre grupo e `log1p(despesa)` usa os mesmos controles acordados; deduplicado é principal e todas as linhas, sensibilidade. Curvas dependem do suporte por UF×partido (N≥10 por grupo e cobertura mínima de 80%); protocolo pré-estimado em `docs/tse-2022-race-secondary-protocol.md`. Não há interpretação causal nem uso de custo por voto como preditor.
O comando também emite tabelas de associação por resultado, modelos de eleição e proporções por UF/faixa em `reports/`.

`analyze` também exporta faixas absolutas de despesa deduplicada (`até R$ 50 mil`, `acima de R$ 50 mil até R$ 200 mil`, `acima de R$ 200 mil até R$ 1 milhão` e `acima de R$ 1 milhão`) em `tse-2022-election-powerbi-summary.csv`, no Brasil e por UF. O denominador inclui apenas candidaturas APTO com resultado oficial 2/3/4/5, despesa Final disponível e as covariáveis completas do recorte dos modelos eleitorais; eleitos são códigos 2/3. `tse-2022-election-powerbi-candidates.csv` detalha cada candidatura desse recorte; `tse-2022-election-powerbi-dictionary.csv` define os campos e `tse-2022-election-powerbi-recut.json` registra faixas, filtros, numerador e denominador. Esses arquivos são exportações tabulares para Power BI, não um dashboard.

As proporções existentes por quartis ranqueados dentro da UF permanecem separadas em `tse-2022-election-rate-by-uf-expense-band.csv`; as novas faixas não substituem nem recalculam quartis.

`expense-temporal` reutiliza `expense_occurrences` e `expenses`, sem executar modelos: o cenário principal usa candidaturas APTO a deputado federal no 1º turno com prestação `Final` e a deduplicação já materializada; a sensibilidade usa todas as ocorrências do mesmo recorte. Usa apenas `DT_DESPESA` como data da despesa, sem confundi-la com `DT_PRESTACAO_CONTAS` ou `DT_GERACAO`. CSVs Power BI mostram totais mensais, contagens de linhas e candidatos, recorte antes/no dia/depois de 02/10/2022, e contagens/valores de datas ausentes, inválidas ou fora de 2022. Somente datas válidas dentro de 2022 entram nas séries mensais e relativas à eleição; as demais permanecem contabilizadas no CSV de qualidade e no JSON do recorte. Data de despesa não é data de pagamento.

O recorte temporal APTO/Final é o recorte financeiro: inclui linhas Final das candidaturas APTO a deputado federal no 1º turno que tenham despesa observada, sem exigir resultado eleitoral classificável, voto/denominador observado ou covariáveis completas. Na base atual, são 9.204 candidaturas com pelo menos uma linha Final. Ele difere do recorte completo do modelo eleitoral (N=9.202), que exige também votos e denominador observados, resultado oficial classificável (códigos 2–5) e controles completos (UF, partido, idade, sexo, raça e escolaridade), além de despesa nas duas representações. O modelo reduzido, ajustado apenas por UF e partido, usa N=9.204. Portanto, os totais temporais não devem ser interpretados como o N do modelo completo.

Arquivos: `tse-2022-expense-temporal-monthly.csv`, `tse-2022-expense-temporal-relative-to-election.csv`, `tse-2022-expense-temporal-date-quality.csv`, `tse-2022-expense-temporal-dictionary.csv` e `tse-2022-expense-temporal-recut.json`.

`funding-source` é uma exportação complementar: lê a base SQLite existente e o ZIP de contas congelado, sem alterar a base, reingerir dados ou executar modelos/`analyze`. O ZIP informado deve corresponder ao arquivo de origem registrado nas despesas da base. O comando exige os 27 arquivos estaduais de receitas e despesas pagas, exclui os agregados `BR`/`BRASIL` e não soma os arquivos de doador originário.

O recorte de referência são as candidaturas APTO a deputado federal no 1º turno de 2022 com ao menos uma despesa contratada `Final` observada na base deduplicada: 9.204 candidaturas. Receitas são ligadas por `SQ_CANDIDATO`; pagamentos, por `SQ_PRESTADOR_CONTAS`, cuja chave é lida das ocorrências de despesas e validada como única no recorte. Ambos os fluxos usam apenas prestação `Final`. O arquivo por candidatura mantém inclusive candidaturas sem linha de receita ou pagamento, com campos de cobertura distintos de valores monetários.

O leia-me oficial do ZIP define `CD_FONTE_RECEITA`/`CD_FONTE_DESPESA`: `0` Fundo Partidário e `2` Fundo Especial (públicos); `1` Outros Recursos (apresentado como privado/outros não públicos); `9`, ausências e códigos não mapeados ficam em `unclassified`. A classificação mantém o código e o rótulo originais. Nas receitas, `CD_NATUREZA_RECEITA=1` é financeiro e `0` estimável; ambos aparecem separados, e o percentual principal inclui as duas naturezas. `share_of_classified_flow_amount_pct` usa como denominador público + privado; `share_of_all_flow_amount_pct` usa todos os valores válidos, incluindo fonte não classificada. Pagamentos são `VR_PAGTO_DESPESA` por fonte declarada na linha paga; não representam pareamento/rastreio de uma receita específica nem substituem despesas contratadas.

No snapshot atual, os 9.204 candidatos de referência são parte dos 9.476 APTO; 272 APTO não têm linha Final de despesa contratada observada e ficam fora da comparação. As receitas têm 99.242 linhas para 9.204/9.204 candidatos (100%). Somam R$ 3.190.433.921,88: público (códigos 0+2), R$ 2.776.259.891,36; Outros Recursos (código 1), R$ 414.174.030,52; não classificado, 421 linhas / R$ 0,00. O percentual público principal é 87,0183% = R$ 2.776.259.891,36 ÷ (R$ 2.776.259.891,36 + R$ 414.174.030,52), denominador R$ 3.190.433.921,88. Só receitas financeiras (`CD_NATUREZA_RECEITA=1`), sem as estimáveis, resultam em 88,3315% público sobre R$ 3.053.147.587,19 classificados; as estimáveis ficam separadas (R$ 79.368.432,02 públicos; R$ 57.917.902,67 Outros Recursos).

Pagamentos têm 1.256.017 linhas para 8.363/9.204 candidatos (90,8627%); 841 não têm linha Final de pagamento ligada e não são tratados como valor zero. O total pago declarado é R$ 3.033.236.464,43: público, R$ 2.679.262.194,94 (88,3301% do total público + Outros Recursos); Outros Recursos, R$ 353.974.269,49; nenhuma linha de pagamento ficou sem classe de fonte. Cobertura por classe pode se sobrepor: um candidato pode declarar mais de uma fonte.

Arquivos: `tse-2022-funding-source-candidates.csv`, `tse-2022-funding-source-summary.csv`, `tse-2022-funding-source-dictionary.csv` e `tse-2022-funding-source-recut.json`.

## Lendo os resultados

- Comece por `reports/tse-2022-financial-analysis.md` para população, totais, previsões interpretáveis, interação por sexo, diagnósticos, INAPTO e limitações.
- `reports/tse-2022-vote-denominator-by-uf.csv` expõe os 27 totais oficiais por UF, valores nominais e de legenda e a referência do membro de origem.
- `reports/tse-2022-financial-model-estimates.csv` contém coeficientes e intervalos robustos; `reports/tse-2022-predicted-expense-scenarios.csv` mostra previsões por quartis de despesa comparáveis nos dois cenários.
- `reports/tse-2022-sex-interaction-curve.csv` contém curvas e ICs pontuais apenas na interseção das faixas P5–P95 de despesas de mulheres e homens.
- `reports/tse-2022-model-calibration-deciles.csv`, `reports/tse-2022-model-influence-top-candidates.csv` e `reports/tse-2022-top-one-percent-expense-sensitivity.csv` registram calibração em amostra, casos influentes e sensibilidade ao topo da distribuição.
- A análise secundária de eleição aparece depois dos primeiros resultados em `reports/tse-2022-financial-analysis.md`; os arquivos `tse-2022-election-expense-comparison.csv`, `tse-2022-election-expense-models.csv` e `tse-2022-election-rate-by-uf-expense-band.csv` contêm comparações descritivas, coeficientes e proporções por UF/faixa.
- A análise racial e seus limites aparecem como seção secundária posterior em `reports/tse-2022-financial-analysis.md`; `tse-2022-race-population-counts.csv`, `tse-2022-race-group-descriptives.csv`, `tse-2022-race-interaction-coefficients.csv`, `tse-2022-race-interaction-curve.csv`, `tse-2022-race-curve-support.csv` e `tse-2022-race-support-by-uf-party.csv` trazem grupos, descrições, interação e cobertura; os SVGs documentam as curvas (ou a supressão por falta de suporte).
- A comparação eleitoral observada por raça/cor e a decisão de não publicar ajustes por falta de suporte comum estão no mesmo relatório; população, modelos pretendidos e regra de supressão estão pré-especificados em `docs/tse-2022-race-election-secondary-protocol.md`.
- `reports/tse-2022-duplicate-diagnostics.json` registra ocorrências excluídas, candidatos afetados e impacto financeiro no universo completo.
- `reports/tse-2022-dedup-exclusions.csv` lista todas as ocorrências excluídas, membro/linha de origem, referência à ocorrência mantida, candidatura, despesa e valor em centavos.
- A exploração anterior está em `reports/tse-2022-exploratory-provisional.md`; não deve ser interpretada como o resultado ajustado do protocolo.
- Para inspecionar linhas de despesas manualmente, use o DB Browser for SQLite conforme as consultas abaixo.


## Seleção e granularidade

- Candidaturas: `consulta_cand_2022_<UF>.csv`/`consulta_cand_2022_BRASIL.csv`, filtradas para ano 2022, primeiro turno e deputado federal.
- Despesas contratadas: `despesas_contratadas_candidatos_2022_<UF>.csv`; cada linha preserva membro e número da linha de origem.
- Votos nominais: `votacao_candidato_munzona_2022_<UF>.csv`, por candidato, município, zona e indicador de voto em trânsito.
- Denominador: somente `votacao_partido_munzona_2022_BRASIL.csv`, sem somar membros sobrepostos `BR` ou por UF; seleciona 2022, turno 1, cargo 6/deputado federal e soma votos nominais válidos com o total de legenda.
- Os agregados são reconciliados por UF: o nominal oficial deve igualar a soma nominal por candidato e a cobertura deve conter as 27 UFs. A fonte completa oficial precede filtros `APTO` e `Final`.
- A unidade canônica de candidato é `SQ_CANDIDATO`; a despesa preserva origem `(snapshot_id, source_member, source_row)`; `SQ_DESPESA` não identifica por si só uma linha de item.
- A unidade de voto do arquivo individual é `(SQ_CANDIDATO, CD_MUNICIPIO, NR_ZONA, ST_VOTO_EM_TRANSITO)`.

## Medidas

A medida de gasto soma `VR_DESPESA_CONTRATADA` em centavos inteiros. O tratamento principal mantém uma ocorrência por grupo exatamente igual nos 53 campos originais do TSE, dentro do mesmo snapshot e membro de origem. Os quatro campos de auditoria não participam da comparação. Uma igualdade apenas em `SQ_DESPESA` ou `NR_DOCUMENTO` não é suficiente. A decisão é metodológica, sem confirmação oficial da identidade econômica das repetições; a diferença financeira não é chamada de desperdício ou gasto indevido. A medida não representa despesa paga.

`expense_occurrences` e o ZIP original preservam todas as linhas. `expense_dedup_exclusions` registra cada ocorrência excluída e a referência da ocorrência mantida. A análise `Final`/`APTO` mantém todas as linhas como sensibilidade e informa totais e diferenças separados do universo completo.

O leia-me oficial descreve uma medida específica para dívida de campanha que considera entrega `Final` bem-sucedida e contrapõe valores pagos. Esta análise usa apenas o rótulo textual `Final` para a medida contratada; não afirma que seja a última prestação bem-sucedida. Os demais tipos são exibidos separadamente.

O inventário de situações e entregas continua disponível em `reports/tse-2022-candidate-delivery-inventory.md`; ele não altera a população, medida ou denominador já fixados no protocolo.

A base mantém ausência distinta de zero:

- sem registro de despesa: `expense_observation = absent` e valor vazio;
- registro de despesa cujo total é zero: `expense_observation = observed_zero`;
- sem registro de voto: `vote_observation = absent`;
- registros de voto com total válido zero: `vote_observation = observed_zero`.

## Artefatos

Em `data/derived/2022/`:

- `pilot.sqlite`: candidaturas, votos, base principal deduplicada e tabela intacta `expense_occurrences` com todas as linhas e referências;
- `expense_dedup_exclusions`: cada ocorrência excluída e a ocorrência mantida do mesmo grupo;
- `candidates_canonical.csv`: uma linha por candidato federal canônico;
- `expense_aggregate.csv`: despesas da base principal agregadas por candidato;
- `vote_aggregate.csv`: votos agregados por candidato;
- `analytical_base.csv`: junção à esquerda da tabela de candidatos com as duas agregações;
- `validation.json`: status, regra de deduplicação, contagens, evidências, fontes e reconciliações.
- `vote_denominator_by_uf.csv`: votos nominais, votos de legenda, total válido oficial e membro de origem por UF;

### Consultar despesas linha a linha no SQLite

`pilot.sqlite` contém `expense_occurrences`: uma linha para cada uma das 1.139.275 despesas selecionadas das 27 UFs, incluindo todas as repetições. As 53 colunas oficiais permanecem como texto, junto de `_source_archive`, `_source_member`, `_source_row` (número do registro CSV, incluindo o cabeçalho como linha 1) e `_row_signature`. A tabela `expenses` contém o tratamento principal; `expense_dedup_exclusions` permite auditar as linhas não incluídas nele.

Para abrir sem alterar o banco:

1. Abra o DB Browser for SQLite.
2. Escolha **Open Database** e selecione `data/derived/2022/pilot.sqlite`.
3. Em **Browse Data**, escolha a tabela `expense_occurrences`; use o filtro para `SQ_CANDIDATO` e `SQ_DESPESA`.
4. Para ordenar ou comparar campos, use **Execute SQL** com uma consulta abaixo. Não use **Write Changes** para esta inspeção.

Exemplo verificado de igualdade exata no membro AL:

```sql
SELECT _source_member, _source_row, SQ_CANDIDATO, SQ_DESPESA,
       NR_DOCUMENTO, DS_DESPESA, VR_DESPESA_CONTRATADA, _row_signature
FROM expense_occurrences
WHERE SQ_CANDIDATO = '20001614181' AND SQ_DESPESA = '51008743'
ORDER BY _source_row;
```

Para comparar itens distintos que compartilham o mesmo sequencial e documento:

```sql
SELECT _source_member, _source_row, SQ_CANDIDATO, SQ_DESPESA,
       NR_DOCUMENTO, DS_DESPESA, VR_DESPESA_CONTRATADA
FROM expense_occurrences
WHERE SQ_CANDIDATO = '160001597847'
  AND SQ_DESPESA = '51841829'
  AND _source_row BETWEEN 91 AND 95
ORDER BY _source_row;
```

Para consultar as ocorrências que foram excluídas da base principal, mantendo os campos originais e as referências da ocorrência mantida:

```sql
SELECT o.SQ_CANDIDATO, o.SQ_DESPESA, o.NR_DOCUMENTO, o.DS_DESPESA,
       o.VR_DESPESA_CONTRATADA,
       o._source_member AS membro_excluido,
       o._source_row AS linha_excluida,
       x.kept_source_member AS membro_mantido,
       x.kept_source_row AS linha_mantida,
       x.snapshot_id
FROM expense_dedup_exclusions x
JOIN expense_occurrences o
  ON o._source_member = x.source_member
 AND o._source_row = x.source_row
WHERE o.SQ_CANDIDATO = '10001642332'
  AND o.SQ_DESPESA = '51789637';
```

Essa tabela só recebe ocorrências cuja igualdade foi verificada nos 53 campos originais, no mesmo snapshot e membro. `_row_signature` é um índice de busca, não substitui a comparação dos campos.

```sql
SELECT snapshot_id, source_member, source_row, kept_source_member,
       kept_source_row, sq_candidate, sq_expense, amount_centavos
FROM expense_dedup_exclusions
ORDER BY sq_candidate, source_member, source_row;
```

Somente erros das validações já existentes (campos inválidos, valores ausentes, chaves duplicadas nas tabelas correspondentes ou referência a candidato inexistente) bloqueiam a base. Repetições idênticas nos 53 campos, no mesmo snapshot/membro, são excluídas do tratamento principal e registradas para auditoria; não causam bloqueio. ZIP e `expense_occurrences` permanecem intactos.

## Testes e auditoria

```text
uv run --locked python -m unittest discover -s tests -v
```

Os testes exercitam o denominador oficial com legenda, controles, sensibilidades de despesas e desfecho, interação por sexo, grupos raciais/exclusões e supressão de curvas sem suporte, denominadores de eleição, distinção entre zero e ausência e levantamento de despesas INAPTO. `analyze` recusa uma validação bloqueada ou denominadores sem cobertura e reconciliação das 27 UFs.
