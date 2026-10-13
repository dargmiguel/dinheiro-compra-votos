# Análise exploratória provisória — TSE 2022

> **Validação de ingestão aprovada; protocolo financeiro 2022 definido em [Fixar o protocolo da análise financeira do piloto TSE 2022](https://github.com/dargmiguel/dinheiro-compra-votos/issues/11). Este recorte continua exploratório, não é a análise final nem uma conclusão causal.** Ele ainda não aplica o denominador oficial incluindo legenda, os controles definidos nem a análise secundária por sexo.

## Recorte atual

- População deste recorte exploratório: `CD_SITUACAO_CANDIDATURA = 12` (`APTO`) no snapshot posterior à eleição; não reconstrói situação no dia da votação.
- Prestação deste recorte: `TP_PRESTACAO_CONTAS = Final`; não comprova que seja a última entrega recebida com sucesso.
- Medida aqui: despesas contratadas declaradas; o ZIP contém arquivos de despesas pagas, mas este recorte não os integra.
- Votos aqui: `QT_VOTOS_NOMINAIS_VALIDOS` agregado por candidato, município, zona e indicador de voto em trânsito; não é o denominador oficial de votos válidos incluindo legenda.
- Ausência permanece ausente; zero observado permanece zero.

Entram 9.476 registros `APTO` dos 10.630 candidatos filtrados; 1.154 `INAPTO` não entram neste recorte. Todas as linhas financeiras `Final` para candidatos `APTO` somam 1.117.066 ocorrências antes da deduplicação.

## Tratamento das repetições

| Tratamento | Linhas `Final`/`APTO` | Candidatos com total diferente | Despesa contratada |
|---|---:|---:|---:|
| Deduplicado: uma ocorrência por igualdade exata nos 53 campos | 1.095.391 | 1.977 | R$ 3.076.142.628,75 |
| Todas as linhas: preservar todas as ocorrências | 1.117.066 | — | R$ 3.104.677.701,68 |
| Todas as linhas menos deduplicado | 21.675 excluídas do deduplicado | 1.977 afetados | R$ 28.535.072,93 |

A regra é metodológica; a identidade econômica das repetições não foi confirmada oficialmente. A diferença não é desperdício nem gasto indevido.

## Resultados descritivos

Para 9.100 candidaturas com despesa observada e votos nominais positivos, o custo agregado exploratório é R$ 29,52 no tratamento deduplicado e R$ 29,79 em todas as linhas. É a soma das despesas dividida pela soma dos votos dos pares completos, não a média dos custos individuais. Despesa zero observada resulta em custo zero; despesa ausente fica fora do quociente.

Spearman entre despesa contratada e votos nominais válidos é positivo nas 27 UFs: 0,722059–0,857010 no tratamento deduplicado. São associações descritivas; não indicam que gasto cause votos, não selecionam o tratamento e não substituem a análise ajustada definida no protocolo.

## Reproduzir e inspecionar

```text
python -m tse_pilot explore --manifest data/manifests/manifest-20261008T154908Z.json --validation data/derived/2022/validation.json --output data/exploratory/2022
```

Relatório completo, tabelas, CSVs e gráficos regeneráveis: `data/exploratory/2022/exploratory_report.md` e `data/exploratory/2022/`. Diagnósticos do universo integral e exemplos auditáveis: `reports/tse-2022-deduplication-analysis.md` e `reports/tse-2022-duplicate-diagnostics.json`.
