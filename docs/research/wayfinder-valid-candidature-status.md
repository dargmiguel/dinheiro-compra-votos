# Situação da candidatura e referência temporal — Eleições 2022

**Ticket:** [#8](https://github.com/dargmiguel/dinheiro-compra-votos/issues/8)  
**Data da pesquisa:** 2026-10-13

## Resposta curta

`CD_SITUACAO_CANDIDATURA = 12` acompanhado de `DS_SITUACAO_CANDIDATURA = APTO` informa a situação da candidatura no retrato/extração representado pelo arquivo consultado; não é um campo de situação “no dia da eleição”. A tabela de candidaturas 2022 inclui `DT_GERACAO` e `HH_GERACAO` (marcadores de geração do arquivo) e os atributos de eleição/turno, mas não inclui uma data efetiva de início/fim da situação, data de julgamento, histórico de decisões ou uma situação com referência temporal eleitoral. O metadado do conjunto informa que a extração é identificável por arquivo e que a atualização é diária. TSE também informou que, durante o período eleitoral de 2022, os dados de candidaturas no DivulgaCandContas eram atualizados de hora em hora. Portanto, a publicação pode refletir eventos processuais posteriores à votação; o código 12 num arquivo pós-eleição **não reconstrói** o status vigente na data da votação.

A Lei das Eleições confirma por que “status na eleição” não pode ser reduzido ao código da tabela: o art. 16-A permite atos de campanha ao candidato cujo registro esteja *sub judice*, mantendo seu nome na urna enquanto nessa condição, mas condiciona a validade dos votos ao deferimento do registro por instância superior. “Apto” num snapshot e “podia concorrer/teve votos apurados naquele momento” não são afirmações intercambiáveis.

## Campos e referências temporais

O leiaute do arquivo oficial `consulta_cand_2022_<UF>.csv` lista os campos abaixo. O recurso disponibilizado pelo TSE é o arquivo [Candidatos 2022, recurso CKAN `435145fd-bc9d-446a-ac9d-273f585a0bb9`](https://dadosabertos.tse.jus.br/dataset/candidatos-2022/resource/435145fd-bc9d-446a-ac9d-273f585a0bb9), distribuído como [ZIP oficial](https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2022.zip).

| Campo | O que documenta/identifica | Uso e limite temporal |
|---|---|---|
| `ANO_ELEICAO` | Ano da eleição; 2022 no recorte | Identifica o ciclo, não a data em que uma situação foi válida. |
| `CD_ELEICAO`, `DS_ELEICAO`, `DT_ELEICAO` | Código, descrição e data da eleição | Delimitam a eleição correspondente. `DT_ELEICAO` é a data da eleição, não a data de julgamento/registro. |
| `NR_TURNO` | Número do turno | Deve ser explícito no recorte; turno não data a situação processual. |
| `CD_CARGO`, `DS_CARGO` | Código e descrição do cargo | Definem o cargo do recorte, não validade jurídica. |
| `SG_UF`, `SG_UE`, `NM_UE` | Unidade/circunscrição eleitoral | Localiza o registro; não é chave temporal. |
| `SQ_CANDIDATO` | Identificador sequencial interno do candidato | Identifica a candidatura na tabela para cruzamento; não contém histórico de decisões. |
| `CD_SITUACAO_CANDIDATURA`, `DS_SITUACAO_CANDIDATURA` | Código e descrição da situação da candidatura no dado | São os campos apropriados para descrever o estado informado pela versão consultada. `12`/`APTO` é observado no arquivo e também exposto nos sistemas TSE, mas não é uma observação datada da situação no dia da eleição. |
| `CD_SIT_TOT_TURNO`, `DS_SIT_TOT_TURNO` | Código e descrição da situação/resultado na totalização do turno | Refere-se ao resultado eleitoral/totalização, não é substituto de situação do registro da candidatura nem uma data de julgamento. Não filtrar validade jurídica por “eleito”, “não eleito” ou “suplente”. |
| `DT_GERACAO`, `HH_GERACAO` | Data/hora de geração do arquivo, conforme instruções do arquivo TSE | Referência temporal do snapshot publicado. Deve ser preservada junto do arquivo, mas não informa quando o status começou ou terminou. |

O arquivo oficial não oferece em seu leiaute status temporal versionado nem, na tabela básica de candidaturas, campos que registrem cada ato processual e sua data. Seus valores de status são, portanto, fotografia do estado disponível na geração daquela extração. A edição da fonte muda a fotografia; a tabela não é, por si só, um log de alterações.

## Status processual, recurso e alterações posteriores

1. O TSE informa no metadado CKAN que o conjunto “Candidatos - 2022” tem **frequência de atualização diária** e que a **data de geração está disponível por arquivo**; a descrição diz que os arquivos contêm registros dos sistemas CAND, Candex e DivulgaCand. Isso descreve publicação/extração, não uma data de corte histórica para cada candidatura.
2. A notícia oficial do TSE de julho de 2022 (“Eleições 2022: dados de candidaturas são atualizados de hora em hora no DivulgaCandContas”) registra periodicidade horária para a divulgação durante o período eleitoral. É evidência de que a informação divulgada era atualizável, não de que um arquivo posterior preserve cada versão horária.
3. A Lei nº 9.504/1997, art. 16-A, explicita a categoria de registro *sub judice*: pode haver campanha e nome na urna enquanto pendente, com validade dos votos condicionada a decisão superior. Assim, uma decisão ainda pendente na votação pode ser resolvida posteriormente, e a situação publicada após o julgamento pode divergir da situação que prevalecia no dia do pleito.
4. O TSE descreve candidaturas *sub judice* como podendo continuar na disputa enquanto houver recurso; sua matéria oficial de 2026 diferencia “Concorrendo” da situação de registro “Indeferido em prazo recursal ou com recurso”. Isso demonstra que participação/concorrência e situação do registro são dimensões distintas. A classificação pública específica deve ser lida no sistema/documento da época, não projetada retroativamente a partir de `APTO`.
5. O registro de candidatos pode ser substituído (Lei nº 9.504/1997, art. 13). Em dados identificados por pessoa/candidatura, a substituição não deve ser interpretada como atualização do status da mesma linha sem conferir identidade, número sequencial e processo; o material consultado não fornece uma tabela de eventos que reconstrua as relações de substituição no tempo.

**Representação no dado:** mudanças de estado aparecem, no máximo, como valores diferentes de `CD_SITUACAO_CANDIDATURA` / `DS_SITUACAO_CANDIDATURA` em extrações publicadas em momentos diferentes; a fonte e as instruções disponíveis não documentam que o arquivo conserve versões anteriores ou que indique a data precisa da mudança. Detalhes/razões complementares constam em recurso separado do TSE, [Candidatos – Informações complementares 2022, recurso `f26933f5-ca6d-4251-a49c-7bc077dbf250`](https://dadosabertos.tse.jus.br/dataset/candidatos-2022/resource/f26933f5-ca6d-4251-a49c-7bc077dbf250), que precisa ser consultado para identificar informações adicionais; sua existência não é histórico temporal por si só.

## Conclusão para a pergunta analítica

- Para um universo operacional de registros que o **snapshot escolhido** marca como aptos, pode-se filtrar `CD_SITUACAO_CANDIDATURA = 12` e exigir concordância com a descrição `APTO`, sempre registrando o ZIP/membro, `DT_GERACAO`/`HH_GERACAO`, data de obtenção e hash. Isso nomeia corretamente a população como “registros classificados como APTO no snapshot”, não “legalmente elegíveis no dia da eleição”.
- Use `ANO_ELEICAO`, `NR_TURNO`, `CD_ELEICAO`/`DT_ELEICAO`, cargo e circunscrição para definir o universo da eleição/turno; use `SQ_CANDIDATO` para a unidade/ligação do registro. Esses campos definem a qual candidatura e eleição o registro se refere, mas não transformam o estado corrente do snapshot em estado histórico.
- `CD_SIT_TOT_TURNO` e sua descrição são resultado de totalização e devem permanecer separados de situação do registro.
- **A situação histórica na data da votação não pode ser reconstruída a partir de um único snapshot pós-eleitoral do arquivo aberto.** A documentação pública consultada não fornece histórico de status com datas de vigência nem atos processuais completos relacionados à mesma chave para reconstruir esse estado. Sem capturas contemporâneas preservadas ou dados/processos oficiais com datas e encadeamento de decisões por candidatura, a resposta temporal é indeterminável. Não se infere elegibilidade legal de `12` ou de qualquer outro código isolado.

## Fontes primárias

- [TSE, Candidatos – 2022, conjunto de dados](https://dadosabertos.tse.jus.br/dataset/candidatos-2022); [metadados CKAN `package_show`](https://dadosabertos.tse.jus.br/api/3/action/package_show?id=candidatos-2022) (frequência diária, data de geração por arquivo, recurso principal e URL oficial).
- [TSE, recurso oficial Candidatos 2022](https://dadosabertos.tse.jus.br/dataset/candidatos-2022/resource/435145fd-bc9d-446a-ac9d-273f585a0bb9); [ZIP de candidaturas 2022](https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2022.zip), contendo `consulta_cand_2022_<UF>.csv` e instruções/leia-me.
- [TSE, notícia oficial: dados de candidaturas atualizados de hora em hora no DivulgaCandContas](https://www.tse.jus.br/comunicacao/noticias/2022/Julho/eleicoes-2022-dados-de-candidaturas-sao-atualizados-de-hora-em-hora-no-divulgacandcontas-875984).
- [Lei nº 9.504/1997, texto compilado oficial no Planalto, arts. 13 e 16-A](https://www.planalto.gov.br/ccivil_03/leis/L9504compilado.htm#art16a).
- [TSE, “Candidatura ‘sub judice’: entenda como funciona” (2026)](https://www.tse.jus.br/comunicacao/noticias/2026/Setembro/candidatura-sub-judice-entenda-como-funciona).
- [TSE, DivulgaCandContas](https://divulgacandcontas.tse.jus.br/), divulgação de registros e contas; e [TSE, recurso de informações complementares 2022](https://dadosabertos.tse.jus.br/dataset/candidatos-2022/resource/f26933f5-ca6d-4251-a49c-7bc077dbf250).
- Estrutura observada no ZIP congelado do projeto: `data/layout-2022.json` (layout `consulta_cand_2022`, campos `DT_GERACAO`, `HH_GERACAO`, eleição, status de candidatura e situação de totalização); fonte/extração original registrada em `data/manifests/manifest-20261008T154908Z.json`. Essas evidências locais identificam a versão observada; a semântica jurídica acima decorre das fontes oficiais citadas, não do manifesto.
