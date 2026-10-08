# Conciliação de candidatos — TSE 2022

**Status:** a aprovação da base financeira permanece bloqueada. Este relatório separa revisão técnica do pipeline, evidência oficial de referência e evidência independente.

## Objetivo e escopo

A investigação compara, por candidato a deputado federal no primeiro turno de 2022, dois cenários diagnósticos para as 21.874 repetições exatas:

- **preservar todas as linhas:** linhas canônicas mais as linhas marcadas como repetição exata;
- **remover repetições exatas:** somente as linhas canônicas usadas pelo diagnóstico.

A igualdade é textual em todos os campos do leiaute. `source_member` e `source_row` preservam a origem física, mas não definem a identidade econômica da despesa. Nenhum cenário foi aprovado, e a escolha não usa votos nem correlação gasto-voto.

## Fonte congelada e comparabilidade

A fonte é o recurso oficial de prestação de contas de candidatos de 2022, recurso CKAN `e45493d5-75df-4ccf-a4b4-7b1f5213577d`, no ZIP preservado pelo manifesto `20261008T154908Z`:

- URL: `https://cdn.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2022.zip`;
- SHA-256: `d706fa9abaa8e00a222a4bdafc310bc198b8c8f2dd55a31c4177847344967bc4`;
- tamanho: `474699288` bytes;
- `ETag`: `"1c4b5618-65d07ece19dcc"`;
- `Last-Modified`: `Sun, 04 Oct 2026 18:28:00 GMT`;
- membro oficial de referência: `despesas_contratadas_candidatos_2022_BRASIL.csv`;
- filtros: `AA_ELEICAO = 2022`, `ST_TURNO = 1`, `DS_CARGO = Deputado Federal`.

O membro `BRASIL` é outra representação oficial dentro do mesmo ZIP e da mesma publicação; portanto, a comparação abaixo é uma **conciliação oficial de referência**, não uma auditoria independente. O DivulgaCandContas foi consultado apenas pelos controles visíveis. A interface mostrou `Entrega Final`, `Data de entrega` e separou `Gastos Financeiros` de `Gastos Estimáveis` para a amostra pública de ABER JOÁS TOFANELLI (SP), com R$ 152.885,00 financeiros, R$ 0,00 estimáveis, aplicação `2.8.37` e atualização da home em `08/10/2026 14:42`. Ao repetir o fluxo para a amostra deste relatório, a interface retornou HTTP 429 e uma página pública `#/504` antes de exibir cartões; nenhum valor foi inferido dessa tentativa. O procedimento e a limitação estão em `docs/research/tse-2022-conciliacao-publica-candidatos.md`.

## Amostra documentada

A amostra combina alto impacto absoluto, alto impacto relativo e controles sem repetição exata. Os identificadores `SQ_CANDIDATO`, nomes, números e UFs vêm das tabelas canônicas locais; o valor relativo é `diferença / preservar todas as linhas`.

| Papel | SQ_CANDIDATO | Candidato — número / UF | Linhas repetidas | Documentos afetados | Remover exatas | Preservar todas | Diferença | Impacto relativo |
|---|---|---|---:|---:|---:|---:|---:|---:|
| Alto absoluto | `60001603454` | Denis Anderson da Rocha Bezerra — 4000 / CE | 178 | 26 | R$ 2.141.449,89 | R$ 2.702.387,94 | R$ 560.938,05 | 20,7571% |
| Alto absoluto | `130001607568` | Weliton Fernandes Prado — 9090 / MG | 162 | 21 | R$ 2.363.750,62 | R$ 2.915.000,00 | R$ 551.249,38 | 18,9108% |
| Alto relativo | `60001668481` | Benjamim Bezerra de Menezes Neto — 1422 / CE | 3 | 1 | R$ 74.650,00 | R$ 120.000,00 | R$ 45.350,00 | 37,7917% |
| Alto relativo | `250001717155` | Solange Aparecida Ferreira dos Santos — 3642 / SP | 2 | 1 | R$ 3.200,00 | R$ 5.000,00 | R$ 1.800,00 | 36,0000% |
| Alto relativo | `210001596115` | Neiva Amador — 1954 / RS | 3 | 2 | R$ 5.387,05 | R$ 8.387,05 | R$ 3.000,00 | 35,7694% |
| Controle | `100001614966` | Fábio Henrique Dias de Macedo — 1919 / MA | 0 | 0 | R$ 3.276.530,90 | R$ 3.276.530,90 | R$ 0,00 | 0,0000% |
| Controle | `250001610668` | Luiz Paulo Teixeira Ferreira — 1398 / SP | 0 | 0 | R$ 3.263.156,41 | R$ 3.263.156,41 | R$ 0,00 | 0,0000% |
| Controle | `190001619524` | Danielle Dytz da Cunha — 4477 / RJ | 0 | 0 | R$ 3.205.558,61 | R$ 3.205.558,61 | R$ 0,00 | 0,0000% |

Os dois cenários são diagnósticos sobre o snapshot bloqueado. O primeiro candidato, por exemplo, tem 178 ocorrências adicionais iguais, mas isso não demonstra que elas sejam indevidas; mede apenas o quanto a decisão alteraria seu total.

## Comparação com o membro oficial `BRASIL`

Para cada candidato, foi aplicado o mesmo filtro de eleição, turno e cargo ao membro `despesas_contratadas_candidatos_2022_BRASIL.csv`. A coluna “total oficial de referência” é a soma publicada de `VR_DESPESA_CONTRATADA` nesse membro, sem deduplicação adicional.

| SQ_CANDIDATO | Linhas no membro BRASIL | Total oficial de referência | Cenário preservando todas | Diferença |
|---|---:|---:|---:|---:|
| `60001603454` | 693 | R$ 2.702.387,94 | R$ 2.702.387,94 | R$ 0,00 |
| `130001607568` | 1.654 | R$ 2.915.000,00 | R$ 2.915.000,00 | R$ 0,00 |
| `60001668481` | 8 | R$ 120.000,00 | R$ 120.000,00 | R$ 0,00 |
| `250001717155` | 5 | R$ 5.000,00 | R$ 5.000,00 | R$ 0,00 |
| `210001596115` | 9 | R$ 8.387,05 | R$ 8.387,05 | R$ 0,00 |
| `100001614966` | 54 | R$ 3.276.530,90 | R$ 3.276.530,90 | R$ 0,00 |
| `250001610668` | 813 | R$ 3.263.156,41 | R$ 3.263.156,41 | R$ 0,00 |
| `190001619524` | 428 | R$ 3.205.558,61 | R$ 3.205.558,61 | R$ 0,00 |

A igualdade é esperada: o membro `BRASIL` e os membros por UF pertencem à mesma publicação e ao mesmo snapshot. Ela confirma que preservar todas as linhas reproduz a representação agregada do arquivo, mas não confirma a identidade econômica das repetições nem resolve qual entrega o DivulgaCandContas usa.

## Impacto relativo e interpretação

- Maior impacto absoluto da amostra: Denis Anderson da Rocha Bezerra, R$ 560.938,05, 20,7571% do cenário preservado.
- Segundo maior impacto absoluto: Weliton Fernandes Prado, R$ 551.249,38, 18,9108%.
- Maior impacto relativo: Benjamim Bezerra de Menezes Neto, 37,7917%; em seguida Solange Aparecida Ferreira dos Santos, 36,0000%, e Neiva Amador, 35,7694%.
- Os três controles não mudam entre cenários.

Esses números servem para dimensionar risco de mensuração. Não são evidência para escolher preservar ou remover linhas e não foram relacionados a votos.

## Revisão metodológica

### Prestações parciais, finais e regularizações

A documentação oficial define `TP_PRESTACAO_CONTAS` como tipo de entrega e descreve, para a dívida de campanha, a última entrega `Final` recebida com sucesso, com exclusões próprias e comparação entre contratadas e pagas. Isso não equivale à soma bruta de todas as linhas.

No snapshot oficial, sob os filtros do piloto, a distribuição observada no membro `BRASIL` foi:

| `TP_PRESTACAO_CONTAS` | Linhas |
|---|---:|
| `Final` | 1.131.581 |
| `Parcial` | 3.793 |
| `Regularização da Omissão` | 3.377 |
| `Relatório Financeiro` | 524 |
| **Total** | **1.139.275** |

O pipeline atual filtra eleição, turno e cargo, mas **não filtra `TP_PRESTACAO_CONTAS`**. Portanto, sua medida diagnóstica atual soma linhas dos quatro tipos observados. Isso é tecnicamente reproduzível e está explicitado, mas ainda não é uma medida aprovada nem pode ser chamada automaticamente de “Gastos Financeiros” do DivulgaCandContas. A amostra de oito candidatos aparece como `Final` no membro `BRASIL`, mas essa coincidência local não resolve a regra para todos os candidatos.

A decisão pendente é escolher, com regra oficial documentada, entre pelo menos: última `Final` recebida com sucesso; estratificação por tipo; ou outra definição explicitamente compatível com o comparativo público. Retificações, sucesso de recebimento e prioridade temporal ainda não estão identificados por uma regra aprovada neste piloto.

### Candidaturas válidas

A seleção atual mantém registros com `AA_ELEICAO = 2022`, `ST_TURNO = 1` e `DS_CARGO = Deputado Federal`. Ela ainda não aplica uma regra de situação da candidatura, como `CD_SITUACAO_CANDIDATURA`, `DS_SITUACAO_CANDIDATURA` ou `CD_SIT_TOT_TURNO`. Logo, os 10.630 registros canônicos não devem ser descritos como “candidaturas válidas” sem qualificar que são registros selecionados pelo cargo/eleição/turno.

Antes da aprovação analítica, deve ser definida e documentada a regra de elegibilidade do universo: campo de situação, momento da situação e tratamento de candidaturas substituídas, inaptas ou com votação registrada. A diferença entre a contagem local e a contagem exibida na interface também não deve ser resolvida por suposição de versão.

### Ausência versus zero

A regra implementada preserva a distinção:

- sem linha de despesa: `expense_observation = absent`, valor vazio;
- linha de despesa com valor observado igual a zero: `expense_observation = observed_zero`;
- sem linha de voto: `vote_observation = absent`;
- linha de voto com quantidade válida igual a zero: `vote_observation = observed_zero`.

Nenhuma ausência é transformada em zero. Campos monetários ausentes ou marcadores oficiais de ausência bloqueiam a validação; duplicidades e relacionamentos desconhecidos também bloqueiam.

## Fonte independente: resultado da tentativa

Não foi obtido, nesta execução, um total independente por candidato para os oito casos da amostra. O acesso público direto ao DivulgaCandContas foi iniciado pelos controles visíveis, mas a interface retornou HTTP 429 antes de mostrar os candidatos; não foram usados endpoints internos, inspeção de rede, scraping ou contorno de bloqueio. O único valor observado diretamente na UI foi o controle metodológico de ABER JOÁS TOFANELLI, documentado no relatório de pesquisa.

Assim, a evidência disponível é suficiente para:

1. confirmar que a interface pública separa gastos financeiros, gastos estimáveis, tipo e data de entrega;
2. confirmar que o cenário preservando todas as linhas reproduz o membro oficial agregado do mesmo ZIP;
3. quantificar exatamente o impacto potencial das duas escolhas na amostra.

Ela é insuficiente para:

1. provar que uma repetição exata é uma despesa econômica legítima ou uma duplicação indevida;
2. provar que a soma de todas as linhas equivale ao total do comparativo público em escala;
3. escolher uma regra de prestação, retificação ou candidatura válida;
4. aprovar a base financeira.

## Recomendação técnica

Manter o bloqueio da base financeira. O código está tecnicamente revisável: a aquisição é manifestada, as linhas e suas origens são preservadas, as regras críticas têm 10 testes aprovados e a execução bloqueada remove artefatos aprovados anteriores. A pendência é metodológica e semântica, não uma falha técnica identificada que impeça a revisão do código.

Não deduplicar automaticamente. Não escolher o tratamento pela associação com votos. O próximo passo concreto é enviar a pergunta pronta em `reports/pergunta-tse-repeticoes-e-conciliacao.md` e obter do TSE a regra de identidade da linha, a política de entregas/retificações e a definição que liga `VR_DESPESA_CONTRATADA` ao comparativo público.

## Fontes

- [Relatório de semântica das repetições](../docs/research/tse-2022-despesas-repeticoes.md)
- [Conciliação pública e tentativa no DivulgaCandContas](../docs/research/tse-2022-conciliacao-publica-candidatos.md)
- [Manifesto congelado](../data/manifests/manifest-20261008T154908Z.json)
- [Relatório de validação bloqueada](tse-2022-pilot-validation-blocked.md)
