# Dinheiro Compra Votos?

Uma investigação reproduzível sobre o que as contas eleitorais permitem dizer da relação entre despesas declaradas e resultados. A pergunta é provocativa; os dados observacionais não mostram que dinheiro cause votos.

## Pergunta e recorte

O trabalho concluído analisa candidaturas a deputado federal no primeiro turno de 2022, nas 27 UFs, a partir de dados oficiais do TSE. A população principal usa a situação `APTO` no snapshot congelado — não uma reconstrução da situação jurídica na data da eleição. O relatório parte de 9.476 candidaturas APTO; os modelos completos usam 9.202 com despesas, votos e controles observados.

## Resultados em contexto

- **Volume e origem são medidas diferentes.** No cenário principal, 9.204 candidaturas APTO com despesa `Final` observada somaram R$ 3,076 bilhões em despesas contratadas declaradas. Separadamente, 88,3% dos R$ 3,053 bilhões em receitas financeiras classificadas vieram de fontes públicas. Despesa contratada, receita recebida e pagamento declarado não são intercambiáveis; despesas não são necessariamente recursos públicos.
- **Despesa e votação tiveram associação positiva ajustada.** No modelo principal (GLM binomial/logit fracionário, N=9.202), `log(1 + despesa contratada)` (valores em R$) associou-se à participação nos votos válidos da UF após controles de UF, partido, idade, sexo, raça e escolaridade (β=0,948; IC 95% robusto HC1: 0,910–0,985). É uma associação condicional, não um efeito causal.
- **A faixa acima de R$ 1 milhão concentrou eleitos, mas não garantiu a vaga.** 420 dos 510 eleitos do recorte (82,4%) declararam despesas acima desse valor. Entre as 987 candidaturas na faixa, 567 não se elegeram (57,4%). Os denominadores respondem a perguntas diferentes.
- **O ranking de despesas partidárias não foi o de eleitos.** Candidaturas filiadas à UNIÃO somaram R$ 492,9 milhões em despesas contratadas e tiveram 57 eleitos; as filiadas ao PL somaram R$ 213,9 milhões e tiveram 98. São despesas de candidaturas filiadas, não dos diretórios; a comparação não mede eficiência.
- **Composição e taxa de eleição também são medidas distintas.** Mulheres foram 35,5% das 9.202 candidaturas do recorte e 17,6% dos 510 eleitos; suas medianas de despesa contratada (R$ 65,6 mil) foram próximas às dos homens (R$ 65,0 mil). Candidaturas pretas ou pardas eram 47,6% das 9.202 candidaturas e 27,3% dos 510 eleitos; a taxa observada foi 139/4.381 (3,17%), contra 363/4.681 (7,75%) entre candidaturas brancas. A comparação de raça/cor tem recortes e coberturas próprios.

## Relatórios e resultados

- [Relatório de análise financeira](reports/tse-2022-financial-analysis.md)
- [Coeficientes e intervalos dos modelos](reports/tse-2022-financial-model-estimates.csv) · [previsões por nível de despesa](reports/tse-2022-predicted-expense-scenarios.csv)
- [Distribuição de receitas, despesas e pagamentos](reports/tse-2022-financial-distribution-totals.csv) · [por partido](reports/tse-2022-financial-distribution-by-party.csv) · [por grupo](reports/tse-2022-financial-distribution-by-group.csv)
- [Comparação descritiva de despesas e eleição](reports/tse-2022-election-expense-comparison.csv) · [modelos secundários de eleição](reports/tse-2022-election-expense-models.csv)
- [Descrições por raça/cor](reports/tse-2022-race-group-descriptives.csv) · [denominador oficial de votos válidos por UF](reports/tse-2022-vote-denominator-by-uf.csv)
- [Protocolo de reprodução e fontes](docs/pilot-2022-reproduction.md)
- [Decisões metodológicas do estudo](docs/dinheiro-compra-votos-investigacao-design.md)

## Como os dados viram resultados

1. **Aquisição e versão:** quatro ZIPs do TSE — candidaturas, prestações de contas, votação nominal e totais oficiais de votos válidos — são identificados no manifesto `20261008T154908Z`, com URL, identificador do recurso, data, metadados HTTP, tamanho e SHA-256. Os arquivos brutos e o SQLite derivado não são distribuídos no Git.
2. **Processamento e validação:** o pipeline lê os CSVs dentro dos ZIPs, preserva origem e linha, monta a base SQLite e registra `validation.json`. O denominador oficial inclui votos nominais e de legenda; os totais são reconciliados nas 27 UFs antes dos filtros `APTO` e `Final`.
3. **Análise e auditoria:** `analyze` gera modelos e tabelas; `duplicates`, `expense-temporal` e `funding-source` produzem diagnósticos e análises complementares. O relatório registra população, coberturas, diagnósticos e sensibilidades.
4. **Visualização:** as tabelas analíticas são exportadas em CSV/JSON; as curvas de apoio são SVGs. Os arquivos preservam os recortes e denominadores usados no relatório.

## Decisões metodológicas essenciais

- A deduplicação principal considera iguais somente registros que coincidem nos 53 campos originais do TSE, no mesmo snapshot e membro de origem. É uma escolha documentada, não uma confirmação de identidade econômica. As ocorrências originais e suas referências são preservadas; a análise de sensibilidade mantém todas as linhas.
- Zero observado não é ausência: uma prestação sem linha fica vazia e marcada como ausente; uma linha com valor zero permanece como zero observado.
- Receitas financeiras são valores recebidos; despesas contratadas são valores declarados em contratos; pagamentos são valores declarados como pagos. Cobertura, unidade e denominador variam entre as medidas, que são reportadas separadamente.
- A análise principal usa despesas `Final` deduplicadas; outras prestações e a versão com todas as linhas são apresentadas à parte. O relatório não presume que `Final` seja a última entrega recebida com sucesso.
- Os resultados são descritivos ou associativos. Não identificam causalidade, desperdício ou eficiência, e não permitem inferir decisões de eleitores individuais.

## Reproduzir

Requer Python 3.11+. Os comandos abaixo estão registrados no CLI `python -m tse_pilot`; para obter e preparar os ZIPs, siga primeiro o [protocolo de reprodução](docs/pilot-2022-reproduction.md).

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v

# Processar o snapshot congelado e gerar as análises
python -m tse_pilot run --manifest data/manifests/manifest-20261008T154908Z.json --output data/derived/2022
python -m tse_pilot analyze --database data/derived/2022/pilot.sqlite --validation data/derived/2022/validation.json --output reports
python -m tse_pilot duplicates --database data/derived/2022/pilot.sqlite --output reports/tse-2022-duplicate-diagnostics.json
python -m tse_pilot expense-temporal --database data/derived/2022/pilot.sqlite --output reports
python -m tse_pilot funding-source --database data/derived/2022/pilot.sqlite --archive data/raw/2022/20261008T154908Z/prestacao_de_contas_eleitorais_candidatos_2022.zip --output reports
```

Para iniciar um snapshot novo, o CLI também oferece `inventory`, `acquire`, `freeze-votes` e `inspect`. Os comandos, parâmetros e ordem estão detalhados no protocolo.

## Tecnologias

Python 3.11+, biblioteca padrão (`argparse`, `csv`, `sqlite3`, `zipfile`, `unittest`), SQLite, NumPy, pandas, SciPy, statsmodels, CSV, JSON e SVG.

## Limitações e próximos passos

**Concluído:** pipeline e validações para o recorte TSE 2022, análise financeira documentada e análises complementares de eleição, raça/cor, tempo e fontes financeiras. Os arquivos brutos e a base SQLite precisam ser obtidos localmente para reproduzir a execução.

**Futuro:** extensão a 2026, integração de métricas de redes sociais e backtests históricos ainda não foram concluídos. Dependem de dados, cobertura e validação específicos; não fazem parte dos resultados apresentados aqui.
