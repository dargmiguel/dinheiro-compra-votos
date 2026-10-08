# Inventário de situações e entregas — TSE 2022

**Status:** evidência descritiva; não libera a base financeira.

## Snapshot e fontes

- Manifesto: `20261008T154908Z`.
- Candidaturas: `consulta_cand_2022_<UF>.csv`, somente os 27 membros por UF; `BR` e `BRASIL` não entram na contagem canônica.
- Contas: `receitas_candidatos_2022_<UF>.csv` e `despesas_contratadas_candidatos_2022_<UF>.csv`, também somente por UF.
- Filtros: eleição 2022, primeiro turno (`NR_TURNO`/`ST_TURNO = 1`) e `DS_CARGO = Deputado Federal`.
- Chave de candidato: `SQ_CANDIDATO`.
- Identidade de entrega usada no inventário: `(SQ_CANDIDATO, SQ_PRESTADOR_CONTAS, TP_PRESTACAO_CONTAS normalizado, DT_PRESTACAO_CONTAS)`.
- Linhas repetidas dentro da mesma entrega não aumentam a contagem de entregas.

O arquivo de contas observado tem `DT_GERACAO = 04/10/2026` e `HH_GERACAO = 15:00:25` em todas as 10.420 identidades de entrega encontradas. Isso identifica o snapshot de extração, não a data em que a prestação foi entregue.

## Situação das candidaturas

O universo de candidaturas contém **10.630 `SQ_CANDIDATO` únicos**:

| Código | Situação | Candidatos | Regra proposta |
|---:|---|---:|---|
| `12` | `APTO` | 9.476 | Incluir no universo principal financeiro, preservando a situação e o resultado do turno como dimensões. |
| `3` | `INAPTO` | 1.154 | Excluir da análise principal; manter em uma tabela/relatório de auditoria, sem apagar do inventário. |

A regra proposta é usar `CD_SITUACAO_CANDIDATURA = 12` (`APTO`) como definição operacional de candidatura válida para a análise principal. Não usar “eleito”, “não eleito” ou “suplente” como critério de validade.

`CD_SIT_TOT_TURNO` deve permanecer como resultado, não como filtro:

| Código | Resultado | Candidatos |
|---:|---|---:|
| `2` | `ELEITO POR QP` | 335 |
| `3` | `ELEITO POR MÉDIA` | 178 |
| `4` | `NÃO ELEITO` | 5.213 |
| `5` | `SUPLENTE` | 4.244 |
| `-1` | `#NULO` | 660 |

Os 660 resultados `#NULO` pertencem aos registros `INAPTO` no snapshot. Há 2 candidatos `INAPTO` com resultado eleitoral `ELEITO POR QP`; por isso a situação da candidatura não deve ser inferida pelo resultado do turno.

A regra é uma proposta operacional, não uma afirmação jurídica sobre elegibilidade. Antes da aprovação da base, deve ser confirmada a data de referência da situação e o tratamento de alterações posteriores.

## Uma ou várias entregas

A união dos registros de receitas e despesas contratadas encontrou **10.420 candidatos com registros de contas**. Cada um tem exatamente **uma** identidade de entrega segundo a chave acima; não foi encontrado candidato com duas combinações distintas de identificador, tipo normalizado e data.

Os **210 candidatos restantes** do universo de candidaturas não aparecem nesses dois conjuntos de contas no snapshot: 48 são `APTO` e 162 são `INAPTO`. Isso significa “sem linha nos conjuntos consultados”, não “gasto zero” nem prova de inexistência de prestação em outro sistema.

| Tipo de entrega | Candidatos | Linhas de despesas contratadas | Datas observadas | Identificadores `SQ_PRESTADOR_CONTAS` |
|---|---:|---:|---|---:|
| `Final` | 10.146 | 1.131.581 | 04/10/2022 a 22/07/2026; 586 datas distintas | 10.146 |
| `Parcial` | 110 | 3.793 | 09/09/2022 a 10/11/2022; 23 datas distintas | 110 |
| `Regularização da Omissão` | 103 | 3.377 | 17/04/2023 a 26/09/2026; 94 datas distintas | 103 |
| `Relatório Financeiro` | 61 | 524 | 09/08/2022 a 18/11/2022; 30 datas distintas | 61 |
| **Total** | **10.420** | **1.139.275** | — | **10.420** |

`TP_PRESTACAO_CONTAS` e `DT_PRESTACAO_CONTAS` são campos da entrega. `DT_GERACAO`/`HH_GERACAO` identificam a extração do arquivo e não devem ser usados como data da prestação.

### Entregas da amostra da investigação

| SQ_CANDIDATO | Candidato | Tipo | Data da prestação | SQ_PRESTADOR_CONTAS | Geração do arquivo |
|---|---|---|---|---|---|
| `60001603454` | Denis Anderson da Rocha Bezerra — 4000/CE | Final | 28/11/2022 | `3763822984` | 04/10/2026 15:00:25 |
| `130001607568` | Weliton Fernandes Prado — 9090/MG | Final | 18/11/2022 | `3772983872` | 04/10/2026 15:00:25 |
| `60001668481` | Benjamim Bezerra de Menezes Neto — 1422/CE | Final | 30/01/2023 | `3798304008` | 04/10/2026 15:00:25 |
| `250001717155` | Solange Aparecida Ferreira dos Santos — 3642/SP | Final | 23/04/2024 | `3805376192` | 04/10/2026 15:00:25 |
| `210001596115` | Neiva Amador — 1954/RS | Final | 28/10/2022 | `3732507612` | 04/10/2026 15:00:25 |
| `100001614966` | Fábio Henrique Dias de Macedo — 1919/MA | Final | 20/11/2022 | `3783863914` | 04/10/2026 15:00:25 |
| `250001610668` | Luiz Paulo Teixeira Ferreira — 1398/SP | Final | 16/11/2022 | `3779873628` | 04/10/2026 15:00:25 |
| `190001619524` | Danielle Dytz da Cunha — 4477/RJ | Final | 15/11/2022 | `3786149118` | 04/10/2026 15:00:25 |

O candidato usado como exemplo de linha repetida, `SQ_CANDIDATO = 10001642332`, também tem uma única entrega identificada: `Final`, `23/05/2023`, `SQ_PRESTADOR_CONTAS = 3793673279`.

## O que está duplicado exatamente

A regra de duplicidade do diagnóstico compara **todos os campos da linha `layout_1`**, sem ignorar fornecedor, documento, entrega, candidato, descrição ou valor. `source_member` e `source_row` são a localização física da ocorrência; não são usados para declarar identidade econômica.

Resultado do snapshot:

- 21.874 ocorrências excedentes de linhas completas idênticas;
- 9.318 grupos de assinatura repetida;
- 2.026 candidatos afetados;
- 6.682 referências de `SQ_DESPESA` afetadas;
- 49.744 valores válidos de `SQ_DESPESA` com mais de uma linha **distinta** — categoria diferente e não classificada como repetição exata.

Exemplo verificável manualmente:

- arquivo: `despesas_contratadas_candidatos_2022_AC.csv`;
- linhas físicas: 1410 e 1411, incluindo o cabeçalho na linha 1;
- candidato: `SQ_CANDIDATO = 10001642332`, número 1555, Flaviano Flavio Baptista de Melo;
- prestação: `Final`, `DT_PRESTACAO_CONTAS = 23/05/2023`, `SQ_PRESTADOR_CONTAS = 3793673279`;
- fornecedor: CPF `75311917253`, Marcos Antonio Ferreira de Oliveira;
- documento: `Nota Fiscal`, número `13607E15076`;
- origem: `20360000`, Serviços próprios prestados por terceiros;
- `SQ_DESPESA = 51789637`;
- `DT_DESPESA = 16/08/2022`;
- descrição: `PREST DE SERV DE COORDENADOR ELEIÇÃO 2022`;
- valor: `R$ 2.200,00` em ambas as linhas.

Esse par é uma repetição de conteúdo completo. O diagnóstico não conclui se é duplicação de publicação, reprocessamento, retificação ou dois lançamentos legítimos. O par fica registrado em `reports/tse-2022-duplicate-diagnostics.json` com assinatura SHA-256 e `duplicate_of`.

Em contraste, o caso do Paraná com `SQ_CANDIDATO = 160001597847`, `SQ_DESPESA = 51841829` e `NR_DOCUMENTO = 180` possui várias linhas com descrições e valores diferentes. Essas linhas são itens distintos no diagnóstico, não repetições exatas.

## Medidas que o projeto consegue calcular

Com os campos e o snapshot atual, o projeto consegue calcular, separadamente:

1. **Soma bruta de `VR_DESPESA_CONTRATADA` por candidato e entrega**, sem afirmar que é `Gastos Financeiros`.
2. **Soma por tipo de entrega**, separando `Final`, `Parcial`, `Regularização da Omissão` e `Relatório Financeiro`.
3. **Cenário preservando todas as linhas** e **cenário removendo somente repetições exatas**, ambos apenas diagnósticos.
4. **Número de linhas, documentos, assinaturas repetidas e impacto absoluto/relativo** por candidato.
5. **Ausência versus zero**, mantendo candidato sem linha como `absent` e linha com valor zero como `observed_zero`.
6. **Soma de votos nominais válidos** na granularidade município/zona, sem converter ausência em zero.

O projeto **não consegue afirmar ainda**:

- qual entrega é a última recebida com sucesso;
- se uma regularização substitui, complementa ou deve ser somada à `Final`;
- se uma linha repetida é uma despesa econômica legítima;
- se `VR_DESPESA_CONTRATADA` corresponde exatamente a `Gastos Financeiros` do DivulgaCandContas;
- dívida líquida ou despesa paga, porque isso exige a seleção oficial da entrega e a combinação com `despesas_pagas`;
- total aprovado para regressão gasto-voto.

A definição segura neste estágio é: **despesa contratada declarada observada no snapshot, agregada por `SQ_CANDIDATO`, entrega e cenário de duplicidade**. Qualquer nome mais forte exigiria regra documental adicional.

## Como verificar manualmente

1. Abra `data/manifests/manifest-20261008T154908Z.json` e confirme URL, tamanho e SHA-256 do ZIP.
2. Abra o ZIP sem somar os membros `BR` ou `BRASIL` aos 27 arquivos por UF.
3. Para reproduzir o par exato, abra `despesas_contratadas_candidatos_2022_AC.csv` como texto/planilha com codificação Latin-1, separador `;` e aspas preservadas. Compare as linhas físicas 1410 e 1411 campo a campo.
4. Consulte `reports/tse-2022-duplicate-diagnostics.json` para a amostra de assinaturas, origem, linha original e linha repetida.
5. Execute:

   ```text
   python -m tse_pilot duplicates --database data/derived/2022/pilot.sqlite --output reports/tse-2022-duplicate-diagnostics.json
   ```

6. Leia `data/derived/2022/validation.json`: o status deve continuar `blocked` por `duplicate_expense_rows = 21874`; as demais regras críticas do snapshot não apresentaram falha fatal.
7. Confirme que não existem `analytical_base.csv`, `expense_aggregate.csv` ou `vote_aggregate.csv` no diretório derivado bloqueado.

## Estado de aprovação

A base financeira continua bloqueada. O inventário de situações e entregas reduz uma ambiguidade — cada candidato com contas nos dois conjuntos consultados tem uma única identidade de entrega no snapshot — mas não resolve a identidade econômica das linhas repetidas nem a semântica de `Gastos Financeiros`.
