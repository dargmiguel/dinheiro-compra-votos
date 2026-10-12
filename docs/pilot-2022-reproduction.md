# Piloto TSE 2022: reprodução

Este piloto consolida, em escopo Brasil / todas as UFs, candidaturas a deputado federal, despesas contratadas declaradas e votação nominal do primeiro turno de 2022. O escopo não inclui 2026, redes sociais, dashboard ou modelo preditivo.
Disponibilidade de dados de redes sociais **não é requisito para concluir o piloto de financiamento TSE 2022**. O piloto fecha a viabilidade apenas para candidaturas, prestações de contas e votação no TSE; a camada de atenção é posterior e condicional à disponibilidade, permissão e comparabilidade temporal de cada fonte. A ausência dessa camada não impede a conclusão do piloto financeiro, nem autoriza preencher cobertura desconhecida como zero.

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
python -m tse_pilot explore --manifest data/manifests/manifest-<snapshot>.json --validation data/derived/2022/validation.json --output data/exploratory/2022
```

`refresh` recalcula tamanho e SHA-256 dos arquivos já congelados e completa o `version_id` sem baixar novamente. `inspect` abre somente amostras dos membros tabulares para registrar encoding, delimitador e colunas; também lista todos os membros do ZIP. `run` lê os ZIPs selecionados por streaming e cria a base SQLite e os CSVs derivados. `duplicates` compara preservar/remover repetições exatas apenas como diagnóstico.

`explore` é separado de `run`: exige uma validação bloqueada apenas por `duplicate_expense_rows`, lê a população `APTO`, filtra `TP_PRESTACAO_CONTAS = Final` e emite somente artefatos marcados como exploratórios em `data/exploratory/2022/`. Não altera `data/derived/2022/` nem transforma a base bloqueada em aprovada. Os cenários A/B, ausências, zeros, gráficos e associações por UF ficam nesse diretório.

Os resultados do snapshot deste comando estão resumidos em `reports/tse-2022-exploratory-provisional.md`; os CSVs e SVGs completos permanecem em `data/exploratory/2022/` e são regeneráveis pelo comando.

`exploratory_uf_associations.csv` apresenta a correlação de Spearman por UF e cenário, usando candidatos com despesa e votação observadas; zeros observados permanecem na amostra e ausências são excluídas. `plots/exploratory_uf_spearman_by_scenario.svg` compara os coeficientes e as dicas dos pontos informam o número de pares completos por UF. São associações descritivas, não estimativas causais.

## Lendo os resultados exploratórios

- Comece por `reports/tse-2022-exploratory-provisional.md` para o resumo metodológico e os números principais.
- Abra `data/exploratory/2022/exploratory_report.md` para o relatório completo gerado pelo comando.
- Os CSVs detalhados ficam em `data/exploratory/2022/`; os gráficos SVG ficam em `data/exploratory/2022/plots/`.
- Os cabeçalhos dos CSVs são em português. CSVs mantêm ponto decimal para que os valores sejam numéricos; Excel/LibreOffice podem importar pelo assistente, com vírgula como separador de colunas e ponto decimal.
- Para explorar sem código, use Excel, LibreOffice Calc ou Google Sheets. Para consultas reproduzíveis, use Python/pandas (`read_csv(..., decimal=".")`) ou consulte `data/derived/2022/pilot.sqlite` com SQLite/DBeaver.

O custo por voto está em **reais por voto**. Exemplo: `29.79` significa R$ 29,79 por voto. Antes era emitido em centavos por voto (`2.979,07` centavos/voto), unidade que foi removida do CSV para evitar confusão. O custo agregado é `soma das despesas / soma dos votos` dos candidatos com despesa observada e votos maiores que zero; não é a média simples dos custos individuais.

## Seleção e granularidade

- Candidaturas: membros por UF de `consulta_cand_2022_<UF>.csv`.
- Despesas: somente `despesas_contratadas_candidatos_2022_<UF>.csv`, por UF.
- Votos: membros por UF de `votacao_candidato_munzona_2022_<UF>.csv`, por município, zona e indicador de voto em trânsito.
- Membros `BR` e `BRASIL` são registrados como excluídos no diagnóstico. Pela nomenclatura e pela coexistência com arquivos por UF, são tratados como possíveis agregados ou recortes sobrepostos; a regra conservadora não os mistura aos arquivos por UF.
- O filtro final mantém `ANO_ELEICAO`/`AA_ELEICAO = 2022`, turno `1` e `DS_CARGO = Deputado Federal`.
O recorte atual não aplica filtro de `TP_PRESTACAO_CONTAS` nem de situação da candidatura. No membro `BRASIL`, sob os mesmos filtros de eleição, turno e cargo, foram observados `Final` (1.131.581 linhas), `Parcial` (3.793), `Regularização da Omissão` (3.377) e `Relatório Financeiro` (524). Portanto, a medida atual inclui os quatro tipos observados e não deve ser chamada de `Gastos Financeiros` do DivulgaCandContas sem uma regra adicional validada. Os 10.630 candidatos são registros selecionados por eleição, turno e cargo, não necessariamente candidaturas válidas: a regra de situação (`CD_SITUACAO_CANDIDATURA`, `DS_SITUACAO_CANDIDATURA` ou `CD_SIT_TOT_TURNO`) ainda está pendente.
- A unidade canônica de candidato é `SQ_CANDIDATO`.
- A unidade de despesa canônica é a linha de origem `(source_member, source_row)`; `SQ_DESPESA` é uma referência documental que pode aparecer em várias linhas de itens do mesmo documento.
- A unidade de voto é `(SQ_CANDIDATO, CD_MUNICIPIO, NR_ZONA, ST_VOTO_EM_TRANSITO)`.

## Medidas

A medida de gasto é a soma de `VR_DESPESA_CONTRATADA` em todas as linhas selecionadas de despesas contratadas, convertida para centavos de real sem ponto flutuante. A inspeção real encontrou `SQ_DESPESA` repetido em linhas diferentes do mesmo documento, com descrições e valores distintos; essas linhas não são deduplicadas. Isso mede despesa contratada declarada, não despesa paga. A medida de votação é a soma de `QT_VOTOS_NOMINAIS_VALIDOS` nos registros de município/zona.

O leia-me oficial descreve uma medida diferente para dívida de campanha: a última entrega `Final` recebida com sucesso, com exclusões específicas, contraposta aos valores pagos. Essa definição não foi aplicada automaticamente ao piloto; a soma atual é diagnóstica e inclui todos os tipos de prestação observados. Retificações, sucesso de recebimento e prioridade entre entregas ainda exigem regra documental do TSE.

O inventário detalhado de situações, entregas, identificadores e medidas permitidas está em `reports/tse-2022-candidate-delivery-inventory.md`. Até a validação da regra de entrega, os únicos nomes seguros são “soma bruta declarada por entrega/tipo” e “cenários diagnósticos de repetição”; `Gastos Financeiros` e dívida não são nomes aprovados para a base.

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

Os testes cobrem o manifesto, detecção do leiaute TSE, separação de ausência e zero, bloqueio por duplicidade e não multiplicação da junção final. A validação real deve ser lida em `data/derived/2022/validation.json`. O comando `report` exige estado `approved`; já `explore` aceita apenas o bloqueio exclusivo por `duplicate_expense_rows` e marca todos os artefatos como provisórios, sem aprovar a base.
