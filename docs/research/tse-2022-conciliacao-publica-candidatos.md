# Conciliação pública de gastos contratados por candidato — Deputado Federal, TSE 2022

**Data da consulta:** 2026-10-08.  
**Pergunta:** existe uma consulta ou exportação pública, documentada pelo TSE, que permita comparar totais de despesas contratadas no nível de candidato para deputado federal em 2022, preservando o tipo de prestação, a data da entrega e uma identificação da versão da publicação?

## Conclusão executiva

**Sim, existe uma consulta pública de comparação no DivulgaCandContas e ela expõe uma pequena tabela comparável por candidato.** O caminho é a interface pública, sem login: selecionar **Eleição Geral Federal 2022 → Comparativo entre candidatos**, filtrar cargo e UF, escolher candidatos do mesmo cargo e, na tabela, ler as colunas de **Gastos Financeiros**, **Gastos Estimáveis**, **Tipo** e **Data de entrega**. A barra de ações da própria tabela também informa **“Exportar dados no formato CSV em UTF-8”**.

A consulta pública não deve ser confundida com uma série histórica imutável. Para a consulta observada, a página inicial mostrou **Data da última atualização: 08/10/2026 14:42** e o rodapé mostrou **Versão 2.8.37**. O registro exibido para o candidato traz, separadamente, o tipo/data da entrega (`Entrega Final`, `24/10/2022`). Assim, o relatório deve guardar a data/hora de acesso, a versão da aplicação e os campos da entrega junto do CSV exportado ou de uma captura da tabela.

O Portal de Dados Abertos oferece ainda um ZIP oficial de lançamentos de prestação de contas. Ele é adequado para auditoria de linhas e agregação reproduzível, mas não é um total pronto por candidato: exige filtrar a unidade candidato-eleição, escolher a entrega segundo a semântica documentada e agregar `VR_DESPESA_CONTRATADA`. Não deduplicar as 21.874 linhas repetidas automaticamente; a documentação oficial não define uma regra de unicidade para essas linhas.

## Fontes oficiais e identificadores

Todas as páginas abaixo foram consultadas em 2026-10-08.

1. **DivulgaCandContas (interface pública):** [https://divulgacandcontas.tse.jus.br/divulga/#/home](https://divulgacandcontas.tse.jus.br/divulga/#/home). A interface exibiu a Eleição Geral Federal 2022, o cartão **Comparativo entre candidatos**, a seleção de cargo/UF e a tabela de comparação. O rodapé exibiu `Versão 2.8.37`.
2. **Notícia oficial que documenta a ferramenta:** [DivulgaCandContas: consulte arrecadações e gastos de campanhas nas Eleições 2022](https://www.tse.jus.br/comunicacao/noticias/2022/Agosto/divulgacandcontas-consulte-arrecadacoes-e-gastos-de-campanhas-nas-eleicoes-2022). O texto do TSE diz que o sistema disponibiliza consulta pública de arrecadação e gastos de campanha, que permite consultas desde 2004, é atualizado de hora em hora e inclui **Comparativo entre Candidatos** por total de recursos arrecadados e gastos de campanha. Também orienta selecionar o ano, a região e o candidato.
3. **Conjunto CKAN oficial:** [Prestação de Contas Eleitorais — 2022](https://dadosabertos.tse.jus.br/dataset/dadosabertos-tse-jus-br-dataset-prestacao-de-contas-eleitorais-2022).
4. **Recurso CKAN oficial:** [Prestação de contas de candidatos](https://dadosabertos.tse.jus.br/dataset/dadosabertos-tse-jus-br-dataset-prestacao-de-contas-eleitorais-2022/resource/e45493d5-75df-4ccf-a4b4-7b1f5213577d). Identificador do recurso: `e45493d5-75df-4ccf-a4b4-7b1f5213577d`; formato declarado: CSV; escopo: Todas as UFs; `datastore_active: false`; metadados atualizados em 05/09/2022; URL oficial do arquivo:
   `https://cdn.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2022.zip`.
5. **Leia-me oficial incluído no ZIP:** `leiame_despesas-contratadas-candidatos.pdf`. A cópia do projeto é o membro do ZIP acima; o PDF define `TP_PRESTACAO_CONTAS`, `DT_PRESTACAO_CONTAS`, `SQ_CANDIDATO`, `SQ_DESPESA`, `DT_DESPESA` e `VR_DESPESA_CONTRATADA`. O leia-me define a dívida de campanha no DivulgaCandContas a partir da última entrega final recebida com sucesso, com exclusões específicas; isso não equivale à soma bruta de todas as linhas.
6. **Regra eleitoral oficial:** [Resolução TSE nº 23.607/2019 — arquivo disponibilizado para as Eleições 2022](https://www.tse.jus.br/eleicoes/eleicoes-2022/arquivos/7-resolucao-no-23-607-prestacao-de-contas-eleitorais/@@display-file/file/7.resolucao-23.607-prestacao-de-contas-eleitorais.pdf). A notícia do TSE também vincula a resolução ao dever de informar doações e gastos eleitorais contratados.

A busca/leitura estática das páginas no ambiente de pesquisa recebeu HTTP 403 para páginas em `www.tse.jus.br` e para a página Divulga; isso é uma limitação desse modo de acesso, não evidência de inexistência dos dados. A interface pública abriu em navegador automatizado normal e foi operada apenas pelos controles visíveis. Não foram usados endpoints internos, inspeção de chamadas de rede, raspagem, bypass ou acesso autenticado.

## Amostra reproduzível pela interface pública

A sequência abaixo é reproduzível com a interface pública e não depende de endpoint não documentado:

1. Abrir o [DivulgaCandContas](https://divulgacandcontas.tse.jus.br/divulga/#/home).
2. No seletor de eleição, escolher **Eleição Geral Federal 2022**.
3. Em **Consultas Individuais / Contas Eleitorais**, abrir **Comparativo entre candidatos**.
4. Clicar para adicionar candidato; escolher `Cargo = Deputado Federal`, `UF = SP`; clicar **Pesquisar**.
5. Na lista de candidatos encontrados, adicionar **ABER JOÁS TOFANELLI — 1250 / Partido Democrático Trabalhista**. Fechar o seletor.
6. A tabela apresenta os cabeçalhos, na ordem visível: receitas (`FEFC`, `Fundo Partidário`, `Privados`, `Estimáveis`), despesas (`Gastos Financeiros`, `Gastos Estimáveis`) e prestação de contas (`Tipo`, `Data de entrega`).
7. Usar a ação de exportação da própria tabela. Ao passar o cursor sobre a ação, a interface informa: **“Exportar dados no formato CSV em UTF-8. No MS Excel utilize a opção de Importação de Dados Externos na aba Dados.”** Guardar o CSV baixado junto com a data/hora, a URL da página, a versão do rodapé e a data de atualização mostrada na home.

### Resultado observado

Para o candidato da amostra, a tabela pública mostrou:

| Identificação | Gastos Financeiros | Gastos Estimáveis | Tipo | Data de entrega | Contexto de versão |
|---|---:|---:|---|---|---|
| ABER JOÁS TOFANELLI — 1250 / PDT — São Paulo/SP | R$ 152.885,00 | R$ 0,00 | Entrega Final | 24/10/2022 | aplicação DivulgaCandContas `2.8.37`; última atualização mostrada na home: 08/10/2026 14:42 |

A mesma tabela mostrou, para conferência da estrutura, receitas de R$ 150.000,00 (FEFC), R$ 0,00 (Fundo Partidário), R$ 2.885,00 (Privados) e R$ 0,00 (Estimáveis). Esses valores não são somados às despesas; servem apenas para confirmar a posição dos campos no comparativo.

O cabeçalho e a presença de `Entrega Final`/`24/10/2022` são a evidência pública de que o comparativo não entrega apenas um número sem contexto. O valor não deve ser descrito como “valor bruto de todas as linhas do ZIP”: é o total apresentado pelo DivulgaCandContas para a entrega que a interface identifica.
### Tentativa adicional solicitada — oito candidatos

Em 08/10/2026, tentei repetir **somente** o fluxo público acima para os candidatos abaixo. A tentativa começou com `Deputado Federal` e a UF correspondente no seletor visível, sem chamadas manuais, inspeção de rede, scraping ou uso de endpoint:

| Número / UF | Candidato solicitado | Resultado |
|---|---|---|
| 4000 / CE | Denis Anderson da Rocha Bezerra | Sem valor recuperado nesta tentativa |
| 9090 / MG | Weliton Fernandes Prado | Sem valor recuperado nesta tentativa |
| 1422 / CE | Benjamim Bezerra de Menezes Neto | Sem valor recuperado nesta tentativa |
| 3642 / SP | Solange Aparecida Ferreira dos Santos | Sem valor recuperado nesta tentativa |
| 1954 / RS | Neiva Amador | Sem valor recuperado nesta tentativa |
| 1919 / MA (controle) | Fabio Henrique Dias de Macedo | Sem valor recuperado nesta tentativa |
| 1398 / SP (controle) | Luiz Paulo Teixeira Ferreira | Sem valor recuperado nesta tentativa |
| 4477 / RJ (controle) | Danielle Dytz da Cunha | Sem valor recuperado nesta tentativa |

Após a pesquisa pública para a UF/CE, a própria interface mostrou **“Erro ao carregar a página”** e **“Por favor tente mais tarde ou acesse nossa página de suporte”**, com erro HTTP **429** (limitação de requisições). O rodapé ainda mostrou a versão da aplicação `2.8.37`, mas a mensagem de atualização da home não ficou disponível após o erro. Uma nova navegação pela interface mostrou a página pública de erro `#/504`. Como a consulta não chegou a exibir os cartões desses candidatos, não há evidência visível para preencher `Gastos Financeiros`, `Gastos Estimáveis`, tipo ou data de entrega para eles. **Isso é uma falha de acesso nesta tentativa, não evidência de que os totais não existam.**

Não tentei contornar o bloqueio reduzindo controles, repetindo chamadas fora da interface, consultando rotas internas, trocando origem ou usando o ZIP como substituto da consulta pedida. A amostra de ABER JOÁS TOFANELLI acima continua sendo a única linha de comparação observada diretamente nesta sessão.


## Checks de comparabilidade

Antes de comparar candidatos, registrar e conferir:

- **Mesma eleição:** todos os cartões devem estar em `Eleição Geral Federal 2022`; não misturar anos.
- **Mesmo cargo e circunscrição:** selecionar `Deputado Federal` e registrar a UF de cada candidato. A própria interface só permite o comparativo entre candidatos do mesmo cargo.
- **Identidade:** conservar nome, número, partido e UF exibidos. O `SQ_CANDIDATO` do arquivo aberto é identificador interno candidato-eleição e não deve ser substituído silenciosamente por nome.
- **Mesmo tipo de prestação:** comparar `Entrega Final` com `Entrega Final` (ou estratificar por tipo); não misturar `Parcial`/`Relatório Financeiro` com final.
- **Data de entrega:** conservar `Data de entrega` por candidato. A data não deve ser interpretada como data da despesa; `DT_DESPESA` é outro campo no leia-me do ZIP.
- **Componentes da despesa:** preservar separadamente `Gastos Financeiros` e `Gastos Estimáveis`. Se o estudo definir “gasto total” como a soma dos dois, registrar essa regra explicitamente; não somar receitas.
- **Versão e mutabilidade:** registrar `Versão 2.8.37`, a data/hora de consulta e a mensagem de última atualização. A notícia do TSE documenta atualização horária e o leia-me avisa que os arquivos de dados podem ser atualizados/aperfeiçoados.
- **Conciliação com o ZIP:** ao validar um candidato no arquivo aberto, guardar o SHA-256 local do ZIP (manifesto do projeto: `d706fa9abaa8e00a222a4bdafc310bc198b8c8f2dd55a31c4177847344967bc4`), nome do membro, `TP_PRESTACAO_CONTAS`, `DT_PRESTACAO_CONTAS`, `SQ_CANDIDATO`, `CD_CARGO`/`DS_CARGO` e a regra de seleção da entrega. A soma de `VR_DESPESA_CONTRATADA` só é comparável depois desses filtros e da política documental de entrega.

## O que é e o que não é uma exportação pública

- **Existe:** uma consulta individual/comparativa no DivulgaCandContas, documentada pelo TSE, com totais de despesas em duas categorias, tipo de prestação e data de entrega; a interface anuncia exportação da tabela em CSV UTF-8.
- **Não foi localizado:** um recurso CKAN separado que publique, já agregado, uma linha por candidato com exatamente as colunas do comparativo e um histórico de versões. O recurso CKAN encontrado é o ZIP de lançamentos e tem `datastore_active: false`.
- **Também não foi localizado:** checksum oficial ou política pública de versionamento que preserve cada resposta histórica do DivulgaCandContas. O rodapé `2.8.37` identifica a aplicação observada; não é hash nem garantia de imutabilidade dos dados.
- **Consequência:** o comparativo é suficiente para uma amostra manual/CSV congelada no momento da consulta. Para escala e auditoria, usar o ZIP oficial como fonte de linhas, preservar o arquivo bruto e documentar a agregação; não inventar uma regra de deduplicação para as repetições exatas.

## Evidência a solicitar ao TSE se a conciliação em escala for necessária

Solicitar formalmente, para a eleição 2022 e o recorte de deputado federal:

1. o CSV exportado pelo comparativo ou uma especificação pública do seu layout, incluindo a definição exata de `Gastos Financeiros` e `Gastos Estimáveis`;
2. a chave candidato-eleição usada para ligar o comparativo ao ZIP (`SQ_CANDIDATO` ou outra), e a regra para candidaturas substituídas/inaptas;
3. a identificação da entrega efetivamente escolhida (tipo, data, status de recebimento/sucesso e tratamento de retificações);
4. o significado da data mostrada como **Data de entrega** e a relação dela com `DT_PRESTACAO_CONTAS`;
5. versão, data/hora de geração, checksum e política de retenção/retificação do conjunto que alimenta o comparativo;
6. regra oficial para linhas repetidas e para registros com o mesmo `SQ_DESPESA`/`NR_DOCUMENTO`, antes de qualquer soma por candidato.

## Fontes primárias consultadas

- [DivulgaCandContas — interface pública](https://divulgacandcontas.tse.jus.br/divulga/#/home)
- [Notícia TSE de 29/08/2022 sobre o DivulgaCandContas](https://www.tse.jus.br/comunicacao/noticias/2022/Agosto/divulgacandcontas-consulte-arrecadacoes-e-gastos-de-campanhas-nas-eleicoes-2022)
- [Conjunto TSE: Prestação de Contas Eleitorais — 2022](https://dadosabertos.tse.jus.br/dataset/dadosabertos-tse-jus-br-dataset-prestacao-de-contas-eleitorais-2022)
- [Recurso TSE: Prestação de contas de candidatos](https://dadosabertos.tse.jus.br/dataset/dadosabertos-tse-jus-br-dataset-prestacao-de-contas-eleitorais-2022/resource/e45493d5-75df-4ccf-a4b4-7b1f5213577d)
- [ZIP oficial: prestação de contas de candidatos 2022](https://cdn.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2022.zip)
- [Resolução TSE nº 23.607/2019 — arquivo para Eleições 2022](https://www.tse.jus.br/eleicoes/eleicoes-2022/arquivos/7-resolucao-no-23-607-prestacao-de-contas-eleitorais/@@display-file/file/7.resolucao-23.607-prestacao-de-contas-eleitorais.pdf)
- [Manifesto congelado do projeto](../../data/manifests/manifest-20261008T154908Z.json)
