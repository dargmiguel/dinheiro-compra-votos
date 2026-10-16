# Guia de navegação do repositório

Este guia explica o que existe no GitHub, como as partes se relacionam e qual arquivo ler para cada pergunta. O projeto analisa as candidaturas a deputado federal no primeiro turno de 2022. Não é um estudo causal de compra de votos.

- [README do projeto](../README.md): apresentação, resultados em contexto e comandos básicos.
- [Índice de relatórios](../reports/README.md): catálogo de 47 saídas analíticas versionadas em `reports/`, com significado, recortes e cautelas.
- [Protocolo de reprodução](pilot-2022-reproduction.md): comandos, entradas necessárias e sequência de processamento.

## Leitura recomendada

1. [README](../README.md) para entender pergunta, achados e limites.
2. [Decisões de domínio e desenho](dinheiro-compra-votos-investigacao-design.md) para definições e escolhas metodológicas.
3. [Protocolo de reprodução](pilot-2022-reproduction.md) para executar o pipeline com UV.
4. [Análise financeira principal](../reports/tse-2022-financial-analysis.md) para resultados e denominadores.
5. [Índice de relatórios](../reports/README.md) para localizar tabelas, diagnósticos e análises complementares.

## Estrutura do repositório no GitHub

### Arquivos da raiz

| Arquivo | Função |
|---|---|
| [`README.md`](../README.md) | Apresenta a investigação, os principais resultados, reprodução, tecnologias e limitações. |
| [`pyproject.toml`](../pyproject.toml) e [`uv.lock`](../uv.lock) | Definem o pacote, dependências e versões resolvidas para reprodução com UV. |
| [`Dockerfile`](../Dockerfile) e [`.dockerignore`](../.dockerignore) | Definem a imagem reproduzível e o que não entra no contexto de build. |
| [`.gitignore`](../.gitignore) | Exclui dados brutos, derivados e arquivos locais que não devem ser versionados. |
| [`AGENTS.md`](../AGENTS.md) | Regras operacionais do repositório, documentação de domínio e uso do GitHub Issues. |

### Dados versionados

| Caminho | Função |
|---|---|
| [`data/inventory-2022.json`](../data/inventory-2022.json) | Inventário das fontes oficiais e do papel de cada recurso TSE no recorte. |
| [`data/layout-2022.json`](../data/layout-2022.json) | Layouts inspecionados dos arquivos compactados: membros, delimitadores, codificações e cabeçalhos. |
| [`data/manifests/manifest-20261008T154908Z.json`](../data/manifests/manifest-20261008T154908Z.json) | Manifesto do snapshot congelado: URLs, identificadores, metadados, tamanhos e hashes. Não contém os ZIPs. |

Os ZIPs brutos e a base SQLite derivada não estão no GitHub. A reprodução baixa ou reutiliza os arquivos locais conforme o manifesto e grava dados derivados em `data/derived/`; veja o protocolo. Os CSVs e relatórios versionados em `reports/` são saídas publicadas, não dados brutos.

### Código `tse_pilot/`

| Módulo | Responsabilidade |
|---|---|
| [`__main__.py`](../tse_pilot/__main__.py) | Interface de linha de comando (`python -m tse_pilot`): inventário, aquisição, congelamento de votos, inspeção, pipeline e subcomandos de análise. |
| [`acquisition.py`](../tse_pilot/acquisition.py) | Consulta e registra recursos, baixa arquivos, calcula hashes e mantém metadados/proveniência do snapshot. |
| [`layout.py`](../tse_pilot/layout.py) | Inspeciona arquivos compactados e registra membros, codificação, delimitador e colunas. |
| [`pipeline.py`](../tse_pilot/pipeline.py) | Verifica os hashes congelados, lê fontes TSE, constrói o SQLite, preserva referências de origem, aplica a deduplicação documentada, valida dados e reconcilia votos. |
| [`duplicates.py`](../tse_pilot/duplicates.py) | Produz diagnósticos de linhas repetidas e exclusões exatas com referências auditáveis. |
| [`analysis.py`](../tse_pilot/analysis.py) | Calcula as análises principais e secundárias, modelos, predições, diagnósticos, suportes e tabelas de raça/cor, sexo, eleição e tempo. |
| [`funding.py`](../tse_pilot/funding.py) | Classifica e resume fontes de receitas e pagamentos, separando tipo de fluxo, natureza e cobertura. |
| [`exploratory.py`](../tse_pilot/exploratory.py) | Gera saídas explicitamente exploratórias; não substitui a análise principal nem seus denominadores/controles. |
| [`report.py`](../tse_pilot/report.py) | Gera relatório descritivo legado a partir da base analítica; não é a referência para os modelos atuais. |
| [`__init__.py`](../tse_pilot/__init__.py) | Metadados de versão do pacote. |

Fluxo conceitual: **inventário → aquisição e snapshot/hash → inspeção de layout → pipeline/SQLite/validação → análise e diagnósticos → CSV/JSON/SVG**. Os subcomandos e pré-requisitos exatos estão em [`pilot-2022-reproduction.md`](pilot-2022-reproduction.md). Não confunda o arquivo Python `report.py` com o relatório principal versionado em `reports/tse-2022-financial-analysis.md`.

### Testes `tests/`

| Arquivo | Escopo principal |
|---|---|
| [`test_acquisition.py`](../tests/test_acquisition.py) | Manifestos, metadados e congelamento idempotente dos totais de votos. |
| [`test_layout.py`](../tests/test_layout.py) | Leitura de layout, delimitadores, codificações e membros de ZIP. |
| [`test_pipeline.py`](../tests/test_pipeline.py) | Hashes, limites de fonte, preservação de dados, duplicatas exatas, ausências/zeros, validação, denominadores e artefatos bloqueados. |
| [`test_duplicates.py`](../tests/test_duplicates.py) | Diagnósticos e exclusões de repetições exatas sem confundir linhas distintas que compartilham identificador/documento. |
| [`test_analysis.py`](../tests/test_analysis.py) | Modelos, recortes, sensibilidades, comparações eleitorais/raça e critérios de suporte. |
| [`test_funding.py`](../tests/test_funding.py) | Classificação de fontes, cobertura, valores ausentes, naturezas e dicionários de financiamento. |
| [`test_exploratory.py`](../tests/test_exploratory.py) | Cenários exploratórios, junções por candidatura, ordenações/empates e proteção de diretórios de produção. |

Os testes usam fixtures controladas; não substituem a validação com as fontes congeladas nem validam cada caminho da CLI. Para executar a suíte, use `uv run --locked python -m unittest discover -s tests -v` conforme o README. Não trate a existência de um teste como evidência de que um resultado real específico foi reexecutado.

### Documentação `docs/`

| Arquivo | Finalidade e status |
|---|---|
| [`dinheiro-compra-votos-investigacao-design.md`](dinheiro-compra-votos-investigacao-design.md) | Decisões de domínio, unidades de análise, conceitos, desfechos e ordem planejada do trabalho. Referência metodológica do piloto. |
| [`dinheiro-compra-votos-investigacao-spec.md`](dinheiro-compra-votos-investigacao-spec.md) | Especificação de requisitos/validação para módulos do projeto. É uma especificação; não comprova que módulos futuros (atenção, redes sociais, 2026 ou backtests) estejam concluídos. |
| [`pilot-2022-reproduction.md`](pilot-2022-reproduction.md) | Procedimento executável do snapshot TSE 2022, dependências UV, comandos e saídas. |
| [`research/dinheiro-compra-votos-fontes-e-viabilidade.md`](research/dinheiro-compra-votos-fontes-e-viabilidade.md) | Pesquisa sobre fontes possíveis e restrições de dados, incluindo fontes que ainda dependem de viabilidade. Não indica coleta concluída. |
| [`research/tse-2022-conciliacao-publica-candidatos.md`](research/tse-2022-conciliacao-publica-candidatos.md) | Pesquisa/diagnóstico de comparação com interface pública de candidaturas; amostra observada e limitações de acesso. |
| [`research/tse-2022-despesas-repeticoes.md`](research/tse-2022-despesas-repeticoes.md) | Pesquisa sobre estrutura e semântica das despesas repetidas, identificadores e tipos de entrega. |
| [`research/tse-2022-votos-validos-por-uf.md`](research/tse-2022-votos-validos-por-uf.md) | Base documental do denominador oficial de votos válidos por UF e sua reconciliação. |
| [`tse-2022-race-secondary-protocol.md`](tse-2022-race-secondary-protocol.md) | Protocolo pré-especificado para comparação secundária de interação por raça/cor e regra de suporte. |
| [`tse-2022-race-election-secondary-protocol.md`](tse-2022-race-election-secondary-protocol.md) | Protocolo da análise secundária de proporções de eleição por raça/cor, com cobertura e gates de publicação. |
| [`repository-guide.md`](repository-guide.md) | Este mapa de arquivos e conceitos. |
| [`agents/domain.md`](agents/domain.md), [`agents/issue-tracker.md`](agents/issue-tracker.md), [`agents/triage-labels.md`](agents/triage-labels.md) | Regras internas para documentação de domínio, Issues e rótulos de triagem; orientam contribuição, não resultados eleitorais. |

### Relatórios `reports/`

Há 47 saídas analíticas versionadas, além deste índice: relatório narrativo principal; resultados estruturados; CSVs de coeficientes, predições e denominadores; distribuição financeira e fontes; eleição; temporalidade; raça/cor; diagnósticos de deduplicação; documento exploratório histórico. A [página de índice de relatórios](../reports/README.md) enumera cada uma, explica unidades/denominadores e identifica arquivos exploratórios ou históricos. Consulte-a em vez de interpretar um CSV isoladamente.

## Como interpretar os números

- **Populações diferentes:** 9.476 candidaturas APTO no snapshot; 9.204 APTO com despesa contratada `Final` observada no recorte de distribuição; 9.202 com dados completos para o modelo principal. Os 1.154 INAPTO ficam em inventário separado.
- **Votos:** participação individual é calculada com votos nominais positivos divididos pelos votos válidos oficiais da UF, que incluem votos nominais e de legenda. Os 27 denominadores estão em `reports/tse-2022-vote-denominator-by-uf.csv`.
- **Deduplicação:** a escolha principal elimina somente repetições exatas nos 53 campos de origem dentro do mesmo snapshot/membro. Todas as ocorrências são preservadas para sensibilidade; igualdade exata é uma regra de mensuração, não juízo sobre a legitimidade econômica de uma despesa.
- **Ausência e zero:** falta de linha/campo permanece ausente; uma linha declarada com valor zero é zero observado. Não imputar ausência como zero.
- **Fluxos financeiros:** receita declarada, despesa contratada e pagamento declarado são medidas separadas, com coberturas e denominadores próprios. Não afirmar que a despesa foi paga, que veio de fonte pública ou que representa o custo total de uma candidatura.
- **Resultados:** associações e comparações descritivas não demonstram causalidade, eficiência, desperdício ou comportamento de eleitores individuais. A análise por raça/cor limita a comparação principal a BRANCA versus PRETA+PARDA; outras categorias continuam documentadas e não desaparecem da população.

## O que está concluído e o que não está

Concluído no GitHub: recorte financeiro TSE 2022, snapshot versionado, pipeline com validações, testes, relatório principal e saídas complementares catalogadas. A reexecução integral exige os arquivos brutos locais, que não estão versionados.

Futuro/condicional: comparação 2026, coleta de métricas de redes sociais e backtests históricos não são resultados concluídos. A especificação e a pesquisa de viabilidade registram planos e restrições; não devem ser citadas como implementação existente.
