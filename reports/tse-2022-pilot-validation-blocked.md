# Piloto TSE 2022: validação bloqueada

## Snapshot e escopo

- Manifesto: `20261008T154908Z`.
- Escopo: Brasil / todas as UFs; 27 arquivos por UF para cada fonte.
- Filtro: eleição 2022, primeiro turno, `DS_CARGO = Deputado Federal`.
- Recursos: candidaturas, despesas contratadas e votação nominal por município/zona.
- Não foram usados dados de 2026, redes sociais ou modelos preditivos.

## Leiaute e granularidade estabelecidos

- Candidato: `SQ_CANDIDATO`.
- Voto: `(SQ_CANDIDATO, CD_MUNICIPIO, NR_ZONA, ST_VOTO_EM_TRANSITO)`; medida `QT_VOTOS_NOMINAIS_VALIDOS`.
- Despesa: a linha de origem `(source_member, source_row)`; `SQ_DESPESA` é uma referência documental, não uma chave de linha.
- A inspeção encontrou 49.744 referências `SQ_DESPESA` com mais de uma linha. Há casos em que o mesmo documento reúne itens diferentes, com descrições e valores diferentes. Essas linhas foram preservadas e não foram deduplicadas.
- Os membros `BR` e `BRASIL` foram excluídos do processamento canônico e registrados no diagnóstico para evitar sobreposição com os 27 arquivos por UF.

## Resultado real da validação

| Fonte | Linhas lidas | Linhas selecionadas | Linhas canônicas antes do bloqueio |
|---|---:|---:|---:|
| Candidaturas | 29.292 | 10.630 | 10.630 |
| Despesas contratadas | 2.200.603 | 1.139.275 | 1.117.401 |
| Votos nominais | 9.296.166 | 3.756.403 | 3.756.403 |

As regras de campos, valores monetários, valores de votos, candidatos inexistentes e duplicidades na votação não encontraram erro. O bloqueio ocorreu em despesas:

- `duplicate_expense_rows`: **21.874**;
- exemplo: `despesas_contratadas_candidatos_2022_AC.csv`, linhas **1410** e **1411**, candidato `10001642332`, `SQ_DESPESA = 51789637`, mesma assinatura da linha completa;
- o diagnóstico registra a linha repetida e a linha original em `data/derived/2022/validation.json`;
- o SQLite preserva as evidências em `expense_duplicates` e não as converte em uma soma aprovada.

## Decisão de segurança

A base analítica **não foi aprovada** e não foi emitida. Não há `analytical_base.csv`, `expense_aggregate.csv` nem `vote_aggregate.csv` no snapshot bloqueado. Remover as 21.874 linhas, somá-las novamente ou tratá-las como erro de transmissão exige uma regra externa validada contra o leiaute/documentação do TSE; nenhuma dessas ações foi aplicada.

O próximo passo necessário é resolver a semântica dessas repetições exatas com evidência oficial ou uma versão de origem que diferencie atualização, parcela e lançamento. Até lá, qualquer custo por voto seria potencialmente enviesado.
