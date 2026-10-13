# Dinheiro compra votos?

Investigação reproduzível sobre despesas declaradas de campanha e resultados eleitorais no Brasil. A entrega em curso é a análise financeira do TSE para deputado federal no primeiro turno de 2022. Os resultados são associativos, não causais.

## Estado da análise 2022

O denominador oficial de votos válidos por UF inclui votos nominais e de legenda e é reconciliado com os votos nominais por candidato antes dos filtros de candidatura e prestação. A população principal usa candidaturas `APTO` no snapshot congelado e despesas `Final`; `INAPTO` tem levantamento separado por tipo de prestação.

O tratamento principal deduplica apenas registros iguais nos 53 campos originais do TSE, dentro do mesmo snapshot e membro de origem. A base preserva todas as ocorrências e suas referências; “todas as linhas” é a sensibilidade. Essa é uma escolha metodológica e não confirma identidade econômica oficial das repetições.

O relatório explica participações previstas em níveis comparáveis de despesa, curvas por sexo no suporte comum, diagnósticos de ajuste e influência, e compara as previsões dos dois cenários. Todas as estimativas são associativas. O relatório exploratório anterior não substitui essa análise. 2026, redes sociais, PJe e backtests são etapas posteriores e não bloqueiam esta entrega.

## Reproduzir o snapshot atual

Requer Python 3.11+.

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m tse_pilot run --manifest data/manifests/manifest-20261008T154908Z.json --output data/derived/2022
python -m tse_pilot analyze --database data/derived/2022/pilot.sqlite --validation data/derived/2022/validation.json --output reports
```

O manifesto identifica quatro ZIPs e registra URL, identificador do recurso, horário de aquisição, cabeçalhos HTTP, tamanho e SHA-256. ZIPs originais e base SQLite não são distribuídos no Git; obtenha-os conforme `docs/pilot-2022-reproduction.md` antes de reproduzir.

Para baixar um snapshot novo, execute também `python -m tse_pilot inventory --data-root data`, `python -m tse_pilot acquire --data-root data` e `python -m tse_pilot freeze-votes --manifest data/manifests/manifest-<snapshot>.json`. `acquire` congela os arquivos de candidaturas, contas e votação nominal; `freeze-votes` acrescenta o quarto ZIP de totais oficiais ao mesmo manifesto. `analyze` exige validação aprovada e denominadores reconciliados nas 27 UFs.

## Leituras

- [Reprodução, fontes, consultas e comandos](docs/pilot-2022-reproduction.md)
- [Especificação da investigação](docs/dinheiro-compra-votos-investigacao-spec.md)
- [Decisões metodológicas e protocolo financeiro 2022](docs/dinheiro-compra-votos-investigacao-design.md)
- [Relatório final de análise financeira](reports/tse-2022-financial-analysis.md)
- [Denominador oficial de votos válidos por UF](reports/tse-2022-vote-denominator-by-uf.csv)
- [Estimativas dos modelos](reports/tse-2022-financial-model-estimates.csv)
- [Participações previstas por nível de despesa](reports/tse-2022-predicted-expense-scenarios.csv)
- [Curva prevista de mulheres e homens no suporte comum](reports/tse-2022-sex-interaction-curve.csv)
- [Calibração por decis dos modelos completos](reports/tse-2022-model-calibration-deciles.csv)
- [Casos de maior influência nos modelos](reports/tse-2022-model-influence-top-candidates.csv)
- [Sensibilidade ao 1% de maior despesa](reports/tse-2022-top-one-percent-expense-sensitivity.csv)
- [Despesas de candidaturas INAPTO por prestação](reports/tse-2022-inapto-expenses-by-type.csv)
- [Resumo detalhado em JSON](reports/tse-2022-financial-analysis.json)
- [Despesas APTO por tipo de prestação](reports/tse-2022-apto-expenses-by-type.csv)
- [Diagnósticos de deduplicação em JSON](reports/tse-2022-duplicate-diagnostics.json)
- [Todas as ocorrências excluídas, com referência à linha mantida](reports/tse-2022-dedup-exclusions.csv)
- [Diagnósticos de duplicação](reports/tse-2022-deduplication-analysis.md)

## Limites

- Associação não implica causalidade; não se estima efeito de gastos sobre votos.
- A situação `APTO` representa o snapshot, não uma conclusão jurídica na data da eleição.
- Despesas contratadas declaradas não são pagamentos efetivos.
- Ausência de prestação ou linha não equivale a gasto zero.
- A deduplicação de igualdade integral não atesta identidade econômica; diferenças não são chamadas de desperdício ou gasto indevido.
- Votos agregados por UF não permitem inferir decisões de eleitores individuais.
- Integração de despesas pagas é complementar; a ausência dela não bloqueia a análise contratada.
