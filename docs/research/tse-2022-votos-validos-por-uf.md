# Total de votos válidos para Deputado Federal por UF — TSE 2022, 1º turno

**Data da consulta:** 2026-10-13.
**Data da pesquisa:** 2026-10-13. Esta nota registrou a seleção da fonte antes da integração; depois, o ZIP foi congelado no manifesto `20261008T154908Z`, validado no pipeline e exportado por UF para o relatório final.

## Conclusão

A fonte mais direta é o recurso oficial **Votação em partido por município e zona**, do conjunto [Resultados - 2022](https://dadosabertos.tse.jus.br/dataset/resultados-2022). Ele publica totais por partido e circunscrição, incluindo votos nominais válidos e votos de legenda válidos; o arquivo permite somar esses componentes para obter o total de votos válidos de Deputado Federal. O próprio cadastro do recurso descreve cobertura para todas as UFs e 1º e 2º turnos, e aponta para o ZIP oficial abaixo. ([página do recurso](https://dadosabertos.tse.jus.br/dataset/resultados-2022/resource/ffb14f0e-85eb-4618-8031-7cb88f95e05e); [metadados CKAN](https://dadosabertos.tse.jus.br/api/3/action/resource_show?id=ffb14f0e-85eb-4618-8031-7cb88f95e05e))

**ZIP oficial:** [votacao_partido_munzona_2022.zip](https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_partido_munzona/votacao_partido_munzona_2022.zip).
**Membro nacional:** `votacao_partido_munzona_2022_BRASIL.csv`.
**Membros por UF:** `votacao_partido_munzona_2022_<UF>.csv` (por exemplo, `votacao_partido_munzona_2022_SP.csv`). O ZIP também contém `votacao_partido_munzona_2022_BR.csv`; não o some com `BRASIL` ou com membros estaduais. O nome nacional, exemplos de arquivos estaduais, bem como a lista de membros foram conferidos no ZIP oficial; a fonte para baixar e reproduzir essa inspeção é a URL CDN acima.

O CSV nacional tem registros por município/zona, cargo e agremiação, não uma linha única por UF. Seu cabeçalho contém os campos `ANO_ELEICAO`, `NR_TURNO`, `SG_UF`, `CD_CARGO`, `DS_CARGO`, `NR_PARTIDO`, `QT_VOTOS_LEGENDA_VALIDOS`, `QT_VOTOS_NOM_CONVR_LEG_VALIDOS`, `QT_TOTAL_VOTOS_LEG_VALIDOS` e `QT_VOTOS_NOMINAIS_VALIDOS`, entre outros. Esses nomes foram verificados no cabeçalho do membro nacional extraído da fonte oficial. O arquivo usa CSV delimitado por ponto e vírgula e valores entre aspas.

## Recorte e agregação recomendados

1. Use **um** universo completo: o membro `_BRASIL.csv` e `SG_UF` para agrupar as 27 UFs, **ou** os 27 membros estaduais individualmente. Nunca some o membro nacional com os membros por UF nem com o membro `BR`.
2. Filtre `ANO_ELEICAO = 2022`, `NR_TURNO = 1` e `CD_CARGO = 6` (confira também `DS_CARGO = 'Deputado Federal'`). A eleição cobre 1º e 2º turnos, de modo que o filtro explícito de turno é necessário. A descrição oficial do conjunto distingue os resultados dos cargos proporcionais por UF e orienta usar o leia-me incluído nos arquivos para interpretar leiautes. ([conjunto oficial](https://dadosabertos.tse.jus.br/dataset/resultados-2022); [recurso oficial](https://dadosabertos.tse.jus.br/dataset/resultados-2022/resource/ffb14f0e-85eb-4618-8031-7cb88f95e05e))
3. Por UF, some em cada linha elegível `QT_VOTOS_NOMINAIS_VALIDOS + QT_TOTAL_VOTOS_LEG_VALIDOS`, abrangendo todos os municípios/zonas e partidos uma única vez. O pipeline também verifica em cada linha que `QT_TOTAL_VOTOS_LEG_VALIDOS = QT_VOTOS_LEGENDA_VALIDOS + QT_VOTOS_NOM_CONVR_LEG_VALIDOS` e não soma o total junto com os dois componentes.
4. Como reconciliação, some `QT_VOTOS_NOMINAIS_VALIDOS` separadamente no arquivo **Votação nominal por município e zona** para o mesmo ano, turno, cargo e UF e compare com o componente nominal do arquivo partidário. O TSE publica este recurso nominal separado e cobre os mesmos turnos; não adicione esse total de novo ao total válido calculado na etapa 3. ([recurso oficial de votação nominal](https://dadosabertos.tse.jus.br/dataset/resultados-2022/resource/40fdcf49-256a-4c81-87cf-711545bd1528); [ZIP nominal](https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_2022.zip))

O TSE explica na definição oficial de [quociente eleitoral](https://www.tse.jus.br/servicos-eleitorais/glossario/termos/quociente-eleitoral) que, na eleição proporcional, votos de partido/coligação correspondem à soma de votos nominais e votos de legenda; brancos e nulos não entram nessa soma. Isso é compatível com agregar as colunas de votos nominais válidos e de legenda válida, sem incluir campos de votos anulados. ([Glossário do TSE](https://www.tse.jus.br/servicos-eleitorais/glossario/termos/quociente-eleitoral))

### Regra de conferência e cautelas

- Antes de somar, inspecione registros que compartilhem partido–município–zona–cargo–turno: cada linha do recurso é uma observação a preservar, e uma chave repetida não autoriza descartar uma ocorrência sem regra documentada. Não junte o membro `_BRASIL.csv` com arquivos estaduais. Filtre `CD_CARGO` e `DS_CARGO` em conjunto para conferir o recorte.
**Cautela de leiaute:** a nota de pesquisa inferiu a relação entre o total de legenda e os dois componentes a partir dos nomes dos campos. No congelamento, a igualdade foi verificada linha a linha e o componente nominal reconciliado por UF contra a votação nominal por candidato. Não foi possível inspecionar o PDF `leiame.pdf` diretamente; portanto, a documentação não atribui ao leia-me uma definição não verificada.
- Usar `QT_TOTAL_VOTOS_LEG_VALIDOS` **uma vez por linha**, e não um arquivo detalhado mais um arquivo agregado do mesmo nível; não agregar `QT_VOTOS_LEGENDA_VALIDOS` junto com `QT_TOTAL_VOTOS_LEG_VALIDOS`.
- O recurso CKAN diz que o ZIP é atualizado frequentemente em função de mudanças na situação de registro de candidaturas decorrentes de julgamentos. Registre a data de obtenção e preserve o ZIP usado para que o resultado seja reprodutível; o metadado do recurso consultado não fornece hash oficial. ([recurso CKAN](https://dadosabertos.tse.jus.br/dataset/resultados-2022/resource/ffb14f0e-85eb-4618-8031-7cb88f95e05e); [API do recurso](https://dadosabertos.tse.jus.br/api/3/action/resource_show?id=ffb14f0e-85eb-4618-8031-7cb88f95e05e))

## Fontes primárias

- [Portal de Dados Abertos do TSE — Resultados - 2022](https://dadosabertos.tse.jus.br/dataset/resultados-2022)
- [Recurso TSE — Votação em partido por município e zona](https://dadosabertos.tse.jus.br/dataset/resultados-2022/resource/ffb14f0e-85eb-4618-8031-7cb88f95e05e)
- [Metadados oficiais CKAN — resource_show](https://dadosabertos.tse.jus.br/api/3/action/resource_show?id=ffb14f0e-85eb-4618-8031-7cb88f95e05e)
- [ZIP TSE — votação em partido por município e zona, 2022](https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_partido_munzona/votacao_partido_munzona_2022.zip)
- [Recurso TSE — Votação nominal por município e zona](https://dadosabertos.tse.jus.br/dataset/resultados-2022/resource/40fdcf49-256a-4c81-87cf-711545bd1528)
- [ZIP TSE — votação nominal por município e zona, 2022](https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_2022.zip)
- [Glossário do TSE — quociente eleitoral](https://www.tse.jus.br/servicos-eleitorais/glossario/termos/quociente-eleitoral)
