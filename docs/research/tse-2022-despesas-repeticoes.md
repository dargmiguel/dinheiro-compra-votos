# Semântica das repetições em despesas contratadas de candidatos — TSE 2022

**Data da investigação:** 2026-10-08.  
**Pergunta:** o que o TSE documenta sobre as linhas de `despesas_contratadas_candidatos_2022_<UF>.csv` e o que pode (e não pode) ser concluído sobre as 21.874 repetições exatas observadas no recorte de deputado federal?

Este relatório separa **fatos oficiais** (documentação do TSE), **observações do snapshot congelado** (reprodutíveis a partir dos artefatos locais) e **inferências/limitações**. “Repetição exata” abaixo é apenas uma descrição de igualdade textual de todos os campos da linha; não é uma decisão de que a despesa deva ser removida.

## 1. Fonte e versão analisadas

A fonte é o recurso oficial **Prestação de contas de candidatos** do conjunto CKAN **Prestação de Contas Eleitorais — 2022**:

- página do conjunto: [Portal de Dados Abertos do TSE](https://dadosabertos.tse.jus.br/dataset/dadosabertos-tse-jus-br-dataset-prestacao-de-contas-eleitorais-2022);
- metadados CKAN consultados: [API `package_show`](https://dadosabertos.tse.jus.br/api/3/action/package_show?id=dadosabertos-tse-jus-br-dataset-prestacao-de-contas-eleitorais-2022);
- recurso: ID CKAN `e45493d5-75df-4ccf-a4b4-7b1f5213577d`, formato declarado `CSV`, escopo “Todas as UFs”, URL oficial do ZIP: [prestacao_de_contas_eleitorais_candidatos_2022.zip](https://cdn.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2022.zip).

O CKAN identifica a fonte como **Sistemas SPCE**, o escopo geopolítico como **Brasil** e informa que a data de geração fica disponível por arquivo. O metadado do conjunto registra criação em 2022-08-23 e modificação em 2026-08-21; o metadado do recurso registra atualização em 2022-09-05 e não fornece hash oficial nem `datastore` (`datastore_active: false`). Essas são propriedades dos metadados consultados, não uma garantia de imutabilidade do ZIP. ([página do recurso](https://dadosabertos.tse.jus.br/dataset/dadosabertos-tse-jus-br-dataset-prestacao-de-contas-eleitorais-2022/resource/e45493d5-75df-4ccf-a4b4-7b1f5213577d); [API CKAN](https://dadosabertos.tse.jus.br/api/3/action/package_show?id=dadosabertos-tse-jus-br-dataset-prestacao-de-contas-eleitorais-2022))

O artefato efetivamente usado é o ZIP preservado pelo projeto no manifesto `20261008T154908Z`:

- caminho: `data/raw/2022/20261008T154908Z/prestacao_de_contas_eleitorais_candidatos_2022.zip`;
- manifesto: `data/manifests/manifest-20261008T154908Z.json`;
- download registrado em `2026-10-08T15:49:08.932335Z`;
- tamanho: `474699288` bytes;
- ETag registrado: `"1c4b5618-65d07ece19dcc"`;
- `Last-Modified` HTTP registrado: `Sun, 04 Oct 2026 18:28:00 GMT`;
- SHA-256 local do ZIP: `d706fa9abaa8e00a222a4bdafc310bc198b8c8f2dd55a31c4177847344967bc4`.

No inventário/layout local, o membro `despesas_contratadas_candidatos_2022_BRASIL.csv` tem `1.343.964.030` bytes descomprimidos e usa `layout_1`; o ZIP contém também os membros por UF. A contagem abaixo usa **somente o membro BRASIL**, e não soma o membro BRASIL aos membros estaduais.

## 2. Fatos oficiais sobre o arquivo e os campos

O ZIP oficial contém `leiame_despesas-contratadas-candidatos.pdf`. A cópia preservada em `data/raw/2022/20261008T154908Z/prestacao_de_contas_eleitorais_candidatos_2022.zip:leiame_despesas-contratadas-candidatos.pdf` é a evidência primária usada aqui; o mesmo PDF está no ZIP distribuído pela [URL CDN oficial](https://cdn.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2022.zip).

### 2.1 Codificação, nulos e atualização

O leia-me oficial diz que:

- os arquivos usam codificação **Latin-1**;
- os campos são separados por `;` e ficam entre aspas, inclusive os numéricos;
- `#NULO` significa informação em branco; em campos numéricos, o correspondente é `-1`;
- `#NE` significa que a informação não era registrada naquele ano; em campos numéricos, o correspondente é `-3`;
- `UF` pode conter `BR` (nível nacional), `VT` (voto em trânsito) ou `ZZ` (exterior);
- os arquivos estão em processo constante de atualização/aperfeiçoamento e podem estar vazios ou conter erro temporário.

Esses pontos estão nas páginas 1–2 do `leiame_despesas-contratadas-candidatos.pdf`. Em particular, uma análise que conta valores numéricos `-1` como identificadores reais mistura o marcador oficial de nulo com um identificador.

### 2.2 Unidade da prestação e da despesa

Na seção `I DESPESA_CANDIDATO`, o TSE define:

- `CD_ELEICAO`: código único da eleição no âmbito da Justiça Eleitoral; cada turno possui código de eleição;
- `ST_TURNO`: último turno em que a candidata ou o candidato prestador de contas concorreu;
- `TP_PRESTACAO_CONTAS`: tipo de entrega, com `Final`, `Relatório Financeiro` e `Parcial` (na notação do arquivo preservado, esses valores aparecem textualmente);
- `SQ_PRESTADOR_CONTAS`: número sequencial do prestador gerado internamente para cada eleição;
- `SG_UF`, `SG_UE` e `NM_UE`: circunscrição e unidade eleitoral da candidatura;
- `SQ_CANDIDATO`: número sequencial interno do candidato/prestador. O leia-me afirma que ele pode ser usado como chave para cruzamento e **não é o número de campanha** (`NR_CANDIDATO`);
- `CD_TIPO_FORNECEDOR`, CPF/CNPJ e nomes: dados do fornecedor informados para a despesa;
- `DS_TIPO_DOCUMENTO`: tipo do comprovante, incluindo cupom fiscal, duplicata, fatura, nota fiscal, RPA, recibo e outro;
- `NR_DOCUMENTO`: número do documento de comprovação da despesa contratada declarada;
- `SQ_DESPESA`: sequencial de identificação do **registro da despesa contratada** declarado, gerado internamente pelos sistemas eleitorais;
- `DT_DESPESA`: data declarada da despesa contratada;
- `DS_DESPESA`: descrição declarada da aplicabilidade da despesa;
- `VR_DESPESA_CONTRATADA`: valor da despesa contratada, em reais, informado pelo prestador.

As definições acima estão nas páginas 3–9 do PDF oficial. O documento não diz que `SQ_DESPESA` é uma chave única global, que `NR_DOCUMENTO` identifica uma única linha, nem que linhas iguais devem ser colapsadas.
### 2.3 Sequência do leiaute (`layout_1`)

O inventário local (`data/layout-2022.json`, derivado do membro oficial e do seu `leiame`) registra `encoding: latin-1`, `delimiter: ";"` e a seguinte sequência de colunas. Preservar a sequência é importante: “linha completa” na seção 3 significa a tupla nessa ordem, sem descartar campos:

```text
DT_GERACAO; HH_GERACAO; AA_ELEICAO; CD_TIPO_ELEICAO; NM_TIPO_ELEICAO;
CD_ELEICAO; DS_ELEICAO; DT_ELEICAO; ST_TURNO; TP_PRESTACAO_CONTAS;
DT_PRESTACAO_CONTAS; SQ_PRESTADOR_CONTAS; SG_UF; SG_UE; NM_UE;
NR_CNPJ_PRESTADOR_CONTA; CD_CARGO; DS_CARGO; SQ_CANDIDATO; NR_CANDIDATO;
NM_CANDIDATO; NR_CPF_CANDIDATO; NR_CPF_VICE_CANDIDATO; NR_PARTIDO;
SG_PARTIDO; NM_PARTIDO; CD_TIPO_FORNECEDOR; DS_TIPO_FORNECEDOR;
CD_CNAE_FORNECEDOR; DS_CNAE_FORNECEDOR; NR_CPF_CNPJ_FORNECEDOR;
NM_FORNECEDOR; NM_FORNECEDOR_RFB; CD_ESFERA_PART_FORNECEDOR;
DS_ESFERA_PART_FORNECEDOR; SG_UF_FORNECEDOR; CD_MUNICIPIO_FORNECEDOR;
NM_MUNICIPIO_FORNECEDOR; SQ_CANDIDATO_FORNECEDOR; NR_CANDIDATO_FORNECEDOR;
CD_CARGO_FORNECEDOR; DS_CARGO_FORNECEDOR; NR_PARTIDO_FORNECEDOR;
SG_PARTIDO_FORNECEDOR; NM_PARTIDO_FORNECEDOR; DS_TIPO_DOCUMENTO;
NR_DOCUMENTO; CD_ORIGEM_DESPESA; DS_ORIGEM_DESPESA; SQ_DESPESA;
DT_DESPESA; DS_DESPESA; VR_DESPESA_CONTRATADA
```

O PDF é a autoridade para a definição semântica dos campos; `data/layout-2022.json` é a transcrição versionada pelo projeto da estrutura observada no ZIP congelado.


### 2.4 Definição oficial de um total relacionado

Na observação `I.1`, o TSE documenta a fórmula de **dívida de campanha** exibida no DivulgaCandContas: (1) somatório dos valores contratados das despesas na última entrega recebida com sucesso pelo SPCE-WEB do tipo `Final`, excluindo determinadas contas de DRD; menos (2) somatório dos valores pagos nessa mesma última entrega final, também com exclusões específicas. A fórmula e a lista de exclusões estão nas páginas 9–10 do [PDF oficial preservado no ZIP](https://cdn.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2022.zip).

Essa definição **não equivale** a “somar todas as linhas do membro BRASIL”: ela menciona a última entrega final recebida com sucesso, contrapõe contratadas e pagas e exclui contas de DRD. É, portanto, uma definição oficial útil para eventual comparação, mas não fornece neste snapshot um total numérico versionado por candidato que possa ser tratado como validação automática das repetições.

## 3. Observações no snapshot congelado

A leitura foi feita com delimitador `;` e `latin-1`, conforme o leia-me. O recorte de deputado federal foi definido pelo par oficial `CD_CARGO = 6` e `DS_CARGO = Deputado Federal`, ambos presentes nas linhas.

| Medida no membro `..._BRASIL.csv` | Resultado |
|---|---:|
| Linhas selecionadas (`CD_CARGO = 6`) | 1.139.275 |
| Linhas distintas quando a linha inteira é comparada campo a campo | 1.117.401 |
| Excesso de linhas em repetições exatas (`1.139.275 - 1.117.401`) | **21.874** |
| Grupos de linhas com a mesma linha completa repetida pelo menos uma vez | 9.318 |
| Valores distintos de `SQ_DESPESA` diferentes do marcador numérico `-1` | 951.314 |
| Valores válidos de `SQ_DESPESA` com mais de uma linha completa distinta | **49.744** |

“Linha inteira” significa igualdade de todos os campos do `layout_1`, sem remover colunas, normalizar texto, converter moeda ou escolher uma entrega. “Linha completa distinta” no último item usa o mesmo critério. O valor `SQ_DESPESA = -1` foi excluído dessa contagem porque o leia-me define `-1` como correspondente numérico de `#NULO`; se o marcador for incluído, há 49.745 valores de `SQ_DESPESA` com mais de uma linha distinta, mas essa não é uma contagem de identificadores válidos.

Os números acima descrevem o snapshot e o filtro, não um número oficial publicado pelo TSE. O TSE não publicou no metadado CKAN uma regra de deduplicação para esse arquivo.

### 3.1 Exemplo de repetição exata

No membro BRASIL há duas ocorrências textualmente iguais, entre outras, com estes campos:

| Campo | Valor nas duas ocorrências |
|---|---|
| `SQ_PRESTADOR_CONTAS` | `3783835505` |
| `SG_UF` / `SG_UE` | `AL` / `AL` |
| `SQ_CANDIDATO` | `20001614181` |
| `SQ_DESPESA` | `51008743` |
| `NR_DOCUMENTO` | `493` |
| `DT_DESPESA` | `21/09/2022` |
| `CD_ORIGEM_DESPESA` | `20140000` |
| `DS_DESPESA` | `PANFLETOS EM PAPEL COCHE 15X21 CM` |
| `VR_DESPESA_CONTRATADA` | `1743,75` |

Os demais campos da linha, inclusive a identificação da entrega (`TP_PRESTACAO_CONTAS`), candidato e fornecedor, também são iguais; por isso o par é contado como uma repetição de linha completa, e não apenas como duas linhas com o mesmo `SQ_DESPESA` ou documento. O fato observado não informa se a origem é duplicação de exportação, retificação, reprocessamento ou outra circunstância: o arquivo e o leia-me não fornecem essa explicação.

### 3.2 Exemplo de várias linhas do mesmo documento/`SQ_DESPESA`

Um contraexemplo importante está no candidato `SQ_CANDIDATO = 160001597847`, prestador `3742177582`, UF `PR`, com `SQ_DESPESA = 51841829` e `NR_DOCUMENTO = 180`. As linhas preservam o mesmo fornecedor, data `01/09/2022` e origem `20140000`, mas têm descrições e valores diferentes, por exemplo:

| `DS_DESPESA` | `VR_DESPESA_CONTRATADA` |
|---|---:|
| `CAIXA PERSONALIZADA` | `1890,00` |
| `ADESIVO VINIL - CORTE DE CONTORNO` | `115,00` |
| `BANNER/FAIXA PERSONALIZADA ACABAMENTO EM MADEIRA` | `34,00` |
| `BANNER/FAIXA PERSONALIZADA ACABAMENTO EM MADEIRA` | `20,00` |
| `BANNER/FAIXA PERSONALIZADA ACABAMENTO EM MADEIRA` | `84,00` |

Essas linhas **não** são repetições exatas. Elas mostram por que o mesmo `SQ_DESPESA` — e, neste exemplo, o mesmo número de documento — não basta para concluir que se trata de uma única linha econômica. O leia-me chama `SQ_DESPESA` de sequencial do registro e chama `NR_DOCUMENTO` de número do comprovante; não define uma regra para agregar itens de um comprovante, nem uma chave composta que resolva o caso.

## 4. O que os dados permitem concluir

### Fato observado

Há 21.874 ocorrências excedentes quando todas as colunas das 1.139.275 linhas selecionadas são comparadas exatamente. Há também 49.744 valores não nulos de `SQ_DESPESA` associados a mais de uma linha completa distinta. Os dois conjuntos não são a mesma coisa: o primeiro trata de igualdade da linha inteira; o segundo trata de um campo que pode aparecer em linhas com conteúdo econômico diferente.

### Inferência que não é sustentada

Não é possível, apenas com o leia-me e o CSV, afirmar que cada repetição exata é um lançamento indevido, nem que cada linha com o mesmo `SQ_DESPESA` é uma parcela, item, retificação ou duplicação. Também não é possível inferir que a última linha, a primeira linha, a soma ou a média seja a representação correta. A documentação não descreve a causa dessas ocorrências nem publica uma política de unicidade/deduplicação.

`TP_PRESTACAO_CONTAS` e `DT_PRESTACAO_CONTAS` são campos semânticos relevantes: o arquivo inclui entregas e o PDF define tipos de entrega. Porém, escolher a “última” entrega exige uma regra de sucesso/versão que não está codificada como uma decisão neste relatório e deve respeitar a definição oficial do total, caso o objetivo seja reproduzir o DivulgaCandContas. Igualdade de conteúdo não prova, por si só, equivalência de origem administrativa.

## 5. Totais oficiais, limitações e recomendação

### Comparação oficial disponível

O mesmo ZIP oficial contém `despesas_contratadas_candidatos_2022_BRASIL.csv`. Aplicando os mesmos filtros (`AA_ELEICAO = 2022`, `ST_TURNO = 1`, `DS_CARGO = Deputado Federal`) a esse membro agregado, a leitura produziu 1.139.275 linhas, 10.420 candidatos distintos e R$ 3.166.000.111,80. Esse total coincide com o cenário que preserva todas as linhas dos 27 membros por UF. É uma conciliação oficial comparável dentro do mesmo snapshot e publicação, mas não uma auditoria independente: não prova que as repetições exatas sejam economicamente distintas.

O leia-me também define a dívida de campanha como contratadas menos pagas na última entrega final recebida com sucesso, com exclusões específicas de DRD. Essa definição é diferente da soma bruta de `VR_DESPESA_CONTRATADA` usada nesta comparação; portanto, não foi apresentada como validação equivalente da dívida oficial.
### Limitações de reprodutibilidade

1. O CKAN não fornece hash oficial do recurso; o SHA-256 acima é do ZIP baixado pelo projeto. A URL CDN pode ser atualizada, razão pela qual o manifesto e o arquivo bruto são parte da evidência.
2. O `DT_GERACAO` observado nas linhas do membro congelado é `04/10/2026 15:00:25`, enquanto `AA_ELEICAO` é `2022`. Isso é compatível com o leia-me, que define `DT_GERACAO`/`HH_GERACAO` como data/hora da extração do arquivo; não deve ser reinterpretado como data da despesa.
3. Os resultados são do membro `BRASIL`, não uma soma independente de membros por UF. Uma extração futura deve registrar o membro, data/hora de geração e hash antes de comparar números.
4. O relatório não resolve candidatura substituída, retificação, entrega parcial/financeira/final, despesas pagas ou contas de DRD. Esses são recortes semânticos distintos do teste de igualdade textual.

### Recomendação

**Preservar o bloqueio atual e não deduplicar automaticamente.** Manter o ZIP bruto, o manifesto, o leia-me e as linhas originais; registrar a igualdade de linha completa como sinal de qualidade; e manter separada a análise de linhas distintas que compartilham `SQ_DESPESA` ou `NR_DOCUMENTO`. Só liberar um total agregado depois que houver uma regra documental e reproduzível para a entrega (`TP_PRESTACAO_CONTAS`), o status de sucesso/retificação e a correspondência com a definição oficial do TSE. Na ausência dessa evidência, remover ou escolher uma ocorrência poderia apagar uma despesa válida ou alterar o total declarado.

Esta recomendação não decide uma regra de deduplicação e não altera pipeline ou dados.

## Fontes primárias

- [Conjunto TSE — Prestação de Contas Eleitorais 2022](https://dadosabertos.tse.jus.br/dataset/dadosabertos-tse-jus-br-dataset-prestacao-de-contas-eleitorais-2022).
- [Recurso TSE — Prestação de contas de candidatos](https://dadosabertos.tse.jus.br/dataset/dadosabertos-tse-jus-br-dataset-prestacao-de-contas-eleitorais-2022/resource/e45493d5-75df-4ccf-a4b4-7b1f5213577d).
- [API CKAN `package_show` — metadados do conjunto](https://dadosabertos.tse.jus.br/api/3/action/package_show?id=dadosabertos-tse-jus-br-dataset-prestacao-de-contas-eleitorais-2022).
- [ZIP oficial CDN — prestação de contas de candidatos 2022](https://cdn.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2022.zip), incluindo `leiame_despesas-contratadas-candidatos.pdf`.
- [DivulgaCandContas — página oficial indicada pelo leia-me](https://divulgacandcontas.tse.jus.br/divulga/#/home) (a fórmula reproduzida neste relatório é a do PDF dentro do ZIP, não um valor obtido por essa página).
- Evidência congelada do projeto: `data/manifests/manifest-20261008T154908Z.json`, `data/layout-2022.json` e `data/raw/2022/20261008T154908Z/prestacao_de_contas_eleitorais_candidatos_2022.zip`.
