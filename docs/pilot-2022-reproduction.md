# Piloto TSE 2022: reprodução

Este piloto consolida, em escopo Brasil / todas as UFs, candidaturas a deputado federal, despesas contratadas declaradas e votação nominal do primeiro turno de 2022. O escopo não inclui 2026, redes sociais, dashboard ou modelo preditivo.

## Fontes congeladas

`data/inventory-2022.json` registra os três recursos oficiais do TSE e seus identificadores de recurso. O comando de aquisição baixa os ZIPs originais sem alterar o conteúdo e cria um manifesto em `data/manifests/` com URL, identificador do recurso, horário de download, `ETag`, `Last-Modified`, tamanho, SHA-256 e `version_id`.

Os arquivos brutos e a base derivada não entram no Git por tamanho. O manifesto e o relatório de leiaute entram no Git para permitir auditoria do snapshot local.

## Comandos

Na raiz do repositório, com Python 3.11+:

```text
python -m tse_pilot inventory --data-root data
python -m tse_pilot acquire --data-root data
python -m tse_pilot refresh --manifest data/manifests/manifest-<snapshot>.json
python -m tse_pilot inspect --manifest data/manifests/manifest-<snapshot>.json --output data/layout-2022.json
python -m tse_pilot run --manifest data/manifests/manifest-<snapshot>.json --output data/derived/2022
python -m tse_pilot report --data-root data --output reports/tse-2022-pilot-exploratory.md
python -m tse_pilot duplicates --database data/derived/2022/pilot.sqlite --output reports/tse-2022-duplicate-diagnostics.json
```

`refresh` recalcula tamanho e SHA-256 dos arquivos já congelados e completa o `version_id` sem baixar novamente. `inspect` abre somente amostras dos membros tabulares para registrar encoding, delimitador e colunas; também lista todos os membros do ZIP. `run` lê os ZIPs selecionados por streaming e cria a base SQLite e os CSVs derivados. `duplicates` compara preservar/remover repetições exatas apenas como diagnóstico.

## Seleção e granularidade

- Candidaturas: membros por UF de `consulta_cand_2022_<UF>.csv`.
- Despesas: somente `despesas_contratadas_candidatos_2022_<UF>.csv`, por UF.
- Votos: membros por UF de `votacao_candidato_munzona_2022_<UF>.csv`, por município, zona e indicador de voto em trânsito.
- Membros `BR` e `BRASIL` são registrados como excluídos no diagnóstico. Pela nomenclatura e pela coexistência com arquivos por UF, são tratados como possíveis agregados ou recortes sobrepostos; a regra conservadora não os mistura aos arquivos por UF.
- O filtro final mantém `ANO_ELEICAO`/`AA_ELEICAO = 2022`, turno `1` e `DS_CARGO = Deputado Federal`.
- A unidade canônica de candidato é `SQ_CANDIDATO`.
- A unidade de despesa canônica é a linha de origem `(source_member, source_row)`; `SQ_DESPESA` é uma referência documental que pode aparecer em várias linhas de itens do mesmo documento.
- A unidade de voto é `(SQ_CANDIDATO, CD_MUNICIPIO, NR_ZONA, ST_VOTO_EM_TRANSITO)`.

## Medidas

A medida de gasto é a soma de `VR_DESPESA_CONTRATADA` em todas as linhas selecionadas de despesas contratadas, convertida para centavos de real sem ponto flutuante. A inspeção real encontrou `SQ_DESPESA` repetido em linhas diferentes do mesmo documento, com descrições e valores distintos; essas linhas não são deduplicadas. Isso mede despesa contratada declarada, não despesa paga. A medida de votação é a soma de `QT_VOTOS_NOMINAIS_VALIDOS` nos registros de município/zona.

A base mantém ausência distinta de zero:

- sem registro de despesa: `expense_observation = absent` e valor vazio;
- registro de despesa cujo total é zero: `expense_observation = observed_zero`;
- sem registro de voto: `vote_observation = absent`;
- registros de voto com total válido zero: `vote_observation = observed_zero`.

## Artefatos

Em `data/derived/2022/`:

- `pilot.sqlite`: tabelas canônicas, duplicidades e violações de relacionamento;
- `candidates_canonical.csv`: uma linha por candidato federal canônico;
- `expense_aggregate.csv`: despesas agregadas por candidato;
- `vote_aggregate.csv`: votos agregados por candidato;
- `analytical_base.csv`: junção à esquerda da tabela de candidatos com as duas agregações;
- `validation.json`: status, contagens, evidências, fontes selecionadas e reconciliações.

A base analítica somente é escrita quando não há erro crítico. Cada execução remove primeiro os artefatos aprovados anteriores (`candidates_canonical.csv`, `expense_aggregate.csv`, `vote_aggregate.csv` e `analytical_base.csv`), para que uma execução bloqueada não deixe resultados antigos disponíveis como atuais. Duplicidade, campo essencial inválido, valor ausente de medida ou referência a candidato inexistente bloqueia a aprovação. Nenhum registro é deduplicado silenciosamente.

## Testes e auditoria

```text
python -m unittest discover -s tests -v
```

Os testes cobrem o manifesto, detecção do leiaute TSE, separação de ausência e zero, bloqueio por duplicidade e não multiplicação da junção final. A validação real deve ser lida em `data/derived/2022/validation.json`; um relatório exploratório só deve ser gerado quando o status for `approved`.
