# Piloto TSE 2022: reprodução

Este piloto consolida, em escopo Brasil / todas as UFs, candidaturas a deputado federal, despesas contratadas declaradas e votação nominal do primeiro turno de 2022. O escopo não inclui 2026, redes sociais, dashboard ou modelo preditivo.
Disponibilidade de dados de redes sociais **não é requisito para concluir o piloto de financiamento TSE 2022**. O piloto fecha a viabilidade apenas para candidaturas, prestações de contas e votação no TSE; a camada de atenção é posterior e condicional à disponibilidade, permissão e comparabilidade temporal de cada fonte. A ausência dessa camada não impede a conclusão do piloto financeiro, nem autoriza preencher cobertura desconhecida como zero.

## Fontes congeladas

`data/inventory-2022.json` registra os quatro recursos oficiais do TSE, inclusive o total partidário por município/zona usado para formar o denominador oficial com votos nominais e de legenda. O comando de aquisição baixa os ZIPs originais sem alterar o conteúdo e cria um manifesto em `data/manifests/` com URL, identificador do recurso, horário de download, `ETag`, `Last-Modified`, tamanho, SHA-256 e `version_id`.

O snapshot executado é `manifest-20261008T154908Z.json`. O ZIP de totais partidários mede 26.150.488 bytes e tem SHA-256 `4f6325c4a496cce00220e197ef3dd2dcd331c44b42e706194dd9e89294d68d9f`. Arquivos brutos e a base derivada não entram no Git; manifesto, layout e resultados agregados entram.

## Comandos

Na raiz do repositório, com Python 3.11+:

```text
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m tse_pilot inventory --data-root data
python -m tse_pilot acquire --data-root data
python -m tse_pilot freeze-votes --manifest data/manifests/manifest-<snapshot>.json
python -m tse_pilot inspect --manifest data/manifests/manifest-<snapshot>.json --output data/layout-2022.json
python -m tse_pilot run --manifest data/manifests/manifest-<snapshot>.json --output data/derived/2022
python -m tse_pilot analyze --database data/derived/2022/pilot.sqlite --validation data/derived/2022/validation.json --output reports
python -m tse_pilot duplicates --database data/derived/2022/pilot.sqlite --output reports/tse-2022-duplicate-diagnostics.json
```

`freeze-votes` congela incrementalmente o recurso oficial de total partidário no manifesto; `run` exige que ele esteja presente, filtra eleição 2022/turno 1/deputado federal e calcula o denominador por UF antes dos filtros `APTO` ou `Final`. O denominador usa o membro nacional `BRASIL` uma vez, nunca somado aos membros `BR`/UF. Confere legenda total contra seus dois componentes e reconcilia voto nominal oficial com a soma de votos válidos por candidato em cada UF.

`run` lê os ZIPs por streaming, preserva cada ocorrência original em `expense_occurrences` e materializa a base principal com deduplicação de linhas iguais nos 53 campos originais, dentro do mesmo snapshot e membro. `duplicates` mede exclusões, candidatos afetados e diferenças financeiras sem classificá-las como desperdício ou gasto indevido; também exporta cada ocorrência excluída e a referência mantida para `reports/tse-2022-dedup-exclusions.csv`.

`analyze` exige validação aprovada e denominadores reconciliados nas 27 UFs. Executa o GLM fracionário principal e sensibilidades; emite relatório com previsões padronizadas e diagnósticos, denominadores por UF, coeficientes, comparação por sexo, arquivos de influência/calibração e levantamento de INAPTO em `reports/`.
`explore` permanece como diagnóstico exploratório anterior, separado da análise principal. Os resultados definitivos são gerados por `analyze` e não dependem dos gráficos exploratórios.

## Lendo os resultados

- Comece por `reports/tse-2022-financial-analysis.md` para população, totais, previsões interpretáveis, interação por sexo, diagnósticos, INAPTO e limitações.
- `reports/tse-2022-vote-denominator-by-uf.csv` expõe os 27 totais oficiais por UF, valores nominais e de legenda e a referência do membro de origem.
- `reports/tse-2022-financial-model-estimates.csv` contém coeficientes e intervalos robustos; `reports/tse-2022-predicted-expense-scenarios.csv` mostra previsões por quartis de despesa comparáveis nos dois cenários.
- `reports/tse-2022-sex-interaction-curve.csv` contém curvas e ICs pontuais apenas na interseção das faixas P5–P95 de despesas de mulheres e homens.
- `reports/tse-2022-model-calibration-deciles.csv`, `reports/tse-2022-model-influence-top-candidates.csv` e `reports/tse-2022-top-one-percent-expense-sensitivity.csv` registram calibração em amostra, casos influentes e sensibilidade ao topo da distribuição.
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
python -m unittest discover -s tests -v
```

Os testes também exercitam o denominador oficial com legenda, controles, sensibilidades de despesas e desfecho, interação por sexo, distinção entre zero e ausência e levantamento de despesas INAPTO. `analyze` recusa uma validação bloqueada ou denominadores sem cobertura e reconciliação das 27 UFs.
