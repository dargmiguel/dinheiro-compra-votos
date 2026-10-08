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

## Revisão metodológica da medida financeira

O pipeline atual filtra eleição, primeiro turno e `DS_CARGO = Deputado Federal`, mas não filtra `TP_PRESTACAO_CONTAS`. No membro oficial `despesas_contratadas_candidatos_2022_BRASIL.csv`, os registros selecionados distribuem-se em `Final` (1.131.581), `Parcial` (3.793), `Regularização da Omissão` (3.377) e `Relatório Financeiro` (524). A soma diagnóstica atual inclui os quatro tipos.

Isso não equivale automaticamente a `Gastos Financeiros` do DivulgaCandContas. O leia-me oficial descreve, para dívida de campanha, a última entrega `Final` recebida com sucesso, com exclusões específicas e comparação entre valores contratados e pagos. A regra de sucesso, retificação e prioridade entre entregas ainda não foi definida para este piloto. A seleção de candidaturas também ainda não aplica situação de candidatura; os 10.630 registros são o universo filtrado por eleição, turno e cargo.

Ausência permanece distinta de zero: sem linha é `absent`; linha observada com valor zero é `observed_zero`. Nenhum desses estados foi convertido silenciosamente.

## Diagnóstico sem aprovação de tratamento

As duas colunas abaixo são apenas cenários contábeis para medir o impacto da decisão, não bases aprovadas:

- **remover repetições exatas:** mantém as 1.117.401 linhas canônicas;
- **preservar todas as linhas:** soma as 1.117.401 linhas canônicas com as 21.874 linhas repetidas.

| Cenário | Total de despesas contratadas |
|---|---:|
| Remover repetições exatas | R$ 3.137.087.110,15 |
| Preservar todas as linhas | R$ 3.166.000.111,80 |
| Diferença | R$ 28.913.001,65 |

A diferença equivale a aproximadamente 0,9132% do total preservando todas as linhas. A comparação não foi usada para escolher um tratamento.

| UF | Repetições exatas | Candidatos afetados | Diferença |
|---|---:|---:|---:|
| AC | 356 | 14 | R$ 165.406,15 |
| AL | 239 | 34 | R$ 783.181,17 |
| AM | 1.146 | 41 | R$ 292.236,53 |
| AP | 211 | 30 | R$ 418.364,51 |
| BA | 1.033 | 124 | R$ 2.541.830,39 |
| CE | 1.003 | 79 | R$ 2.301.328,19 |
| DF | 206 | 40 | R$ 229.728,38 |
| ES | 324 | 66 | R$ 722.263,34 |
| GO | 1.076 | 80 | R$ 697.256,92 |
| MA | 473 | 73 | R$ 1.579.774,59 |
| MG | 1.891 | 189 | R$ 1.624.751,21 |
| MS | 112 | 28 | R$ 355.439,70 |
| MT | 567 | 47 | R$ 256.065,67 |
| PA | 431 | 60 | R$ 1.408.166,86 |
| PB | 205 | 39 | R$ 297.035,01 |
| PE | 1.062 | 77 | R$ 1.604.019,29 |
| PI | 235 | 44 | R$ 1.061.343,89 |
| PR | 678 | 128 | R$ 760.432,38 |
| RJ | 3.298 | 164 | R$ 4.524.076,50 |
| RN | 238 | 39 | R$ 380.098,47 |
| RO | 285 | 51 | R$ 430.776,56 |
| RR | 208 | 29 | R$ 245.495,30 |
| RS | 1.759 | 123 | R$ 1.712.905,85 |
| SC | 519 | 67 | R$ 555.138,58 |
| SE | 167 | 24 | R$ 709.341,91 |
| SP | 3.981 | 302 | R$ 2.965.982,37 |
| TO | 171 | 34 | R$ 290.561,93 |

No total, **2.026 candidatos** e **6.682 documentos** aparecem associados a pelo menos uma repetição exata. Os 49.744 documentos com múltiplas linhas distintas são uma categoria diferente: vários itens do mesmo `SQ_DESPESA` não foram classificados como duplicação.

## Conciliação oficial comparável

O ZIP oficial também contém `despesas_contratadas_candidatos_2022_BRASIL.csv`. Aplicando exatamente os mesmos filtros (`AA_ELEICAO = 2022`, `ST_TURNO = 1`, `DS_CARGO = Deputado Federal`) ao membro oficial agregado:

- 1.139.275 linhas;
- 10.420 candidatos distintos;
- R$ 3.166.000.111,80.

Esse total coincide exatamente com o cenário que preserva todas as linhas por UF. É uma conciliação forte de completude contra outro membro oficial do mesmo ZIP e do mesmo snapshot, mas **não é uma auditoria independente**: não prova que as linhas repetidas sejam economicamente distintas nem autoriza deduplicação.

## Teste de segurança da execução bloqueada

O conjunto de testes contém **10 testes**, todos aprovados. O teste `test_blocked_run_removes_approved_artifacts_from_prior_run` executa primeiro uma base aprovada em diretório temporário, depois uma execução bloqueada no mesmo diretório e verifica que `candidates_canonical.csv`, `expense_aggregate.csv`, `vote_aggregate.csv` e `analytical_base.csv` são removidos. Assim, uma execução bloqueada não deixa artefatos aprovados de uma execução anterior disponíveis como atuais.

## Recomendação técnica

Manter o bloqueio. A conciliação oficial favorece o cenário de preservar todas as linhas como representação do arquivo publicado, mas ainda não resolve se as repetições idênticas são lançamentos legítimos, duplicação de publicação ou efeito de atualização. Falta documentação oficial que defina a identidade econômica da linha repetida e uma validação externa que diferencie esses casos. Nenhum tratamento deve ser escolhido pela associação gasto/votos.
