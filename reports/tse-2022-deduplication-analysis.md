# Despesas TSE 2022: deduplicação e validação

**Estado:** ingestão, validação e protocolo financeiro 2022 aprovados. A análise contratada foi executada; resultados, sensibilidades e limitações estão em `reports/tse-2022-financial-analysis.md`.

## Fonte e escopo executado

- Manifesto: `20261008T154908Z`.
- ZIP de prestação de contas: `prestacao_de_contas_eleitorais_candidatos_2022.zip`.
- SHA-256 do ZIP original, antes e depois da execução: `d706fa9abaa8e00a222a4bdafc310bc198b8c8f2dd55a31c4177847344967bc4`.
- Escopo: 27 membros por UF, eleição 2022, primeiro turno, deputado federal. Membros `BR` e `BRASIL` foram excluídos para não misturar agregados com arquivos por UF.
- A validação integral não filtra `TP_PRESTACAO_CONTAS`; o total integral inclui todas as categorias de prestação presentes no recorte.

## Regra aplicada

A base principal mantém uma ocorrência por grupo de igualdade exata nos 53 campos originais do TSE, dentro do mesmo snapshot e membro de origem. Os campos de auditoria não participam da comparação. `SQ_DESPESA` e `NR_DOCUMENTO` são referências, não chaves de deduplicação. A primeira ocorrência pela ordem do arquivo é mantida; cada ocorrência excluída aponta para a ocorrência mantida.

O hash da linha é apenas um índice de busca. A inclusão de uma linha como repetição exige comparação do valor integral dos 53 campos. `expense_occurrences` e o ZIP original permanecem intactos; `expense_dedup_exclusions` registra as linhas fora da base principal. A preservação de todas as linhas é a sensibilidade.

Esta é uma escolha metodológica. O TSE não confirmou oficialmente que linhas idênticas representam a mesma identidade econômica. A diferença financeira não é classificada como desperdício nem gasto indevido.

## Validação da ingestão

| Fonte | Linhas lidas | Linhas selecionadas | Base principal |
|---|---:|---:|---:|
| Candidaturas | 29.292 | 10.630 | 10.630 |
| Despesas contratadas | 2.200.603 | 1.139.275 ocorrências preservadas | 1.117.401 |
| Votos nominais | 9.296.166 | 3.756.403 | 3.756.403 |

Todas as contagens fatais foram zero: campos inválidos ou ausentes, duplicidade de chave, candidato desconhecido e votos fora do intervalo válido. As reconciliações fecharam exatamente: 1.117.401 linhas e R$ 3.137.087.110,15 na base principal de despesas; 3.756.403 linhas e 105.014.357 votos válidos nominais na agregação. Há 210 candidatos sem qualquer linha de despesa e 955 sem linha de voto no universo geral; ausência permanece distinta de zero. No recorte APTO/Final, 272 candidaturas não têm linha Final.

## Universo integral — todos os tipos de prestação

| Tratamento | Linhas de despesa | Total de despesa contratada |
|---|---:|---:|
| Principal: deduplicação exata | 1.117.401 | R$ 3.137.087.110,15 |
| Sensibilidade: preservar todas as ocorrências | 1.139.275 | R$ 3.166.000.111,80 |
| Diferença da sensibilidade para o principal | 21.874 ocorrências excedentes | R$ 28.913.001,65 |

As exclusões afetam 2.026 candidatos e 6.682 referências de despesa. Há 49.744 pares candidato/`SQ_DESPESA` com mais de uma linha distinta; eles não são duplicatas integrais por esse fato. O diagnóstico por UF está em `reports/tse-2022-duplicate-diagnostics.json`; `reports/tse-2022-dedup-exclusions.csv` enumera todas as 21.874 ocorrências excluídas e aponta a ocorrência mantida.

## Recorte da análise principal Final/APTO

Este é o recorte principal do protocolo: candidaturas `APTO` no snapshot, para deputado federal no primeiro turno, usando despesas `Final`. `APTO` não reconstrói a situação na data da votação; `Final` é o rótulo da prestação e não prova ser a última entrega recebida com sucesso.

| Tratamento | Linhas Final/APTO | Total de despesa contratada |
|---|---:|---:|
| Principal: deduplicação exata | 1.095.391 | R$ 3.076.142.628,75 |
| Sensibilidade: preservar todas as ocorrências | 1.117.066 | R$ 3.104.677.701,68 |
| Diferença da sensibilidade para o principal | 21.675 ocorrências excedentes | R$ 28.535.072,93 |

O recorte inclui 9.476 candidaturas `APTO` de 10.630; 1.154 `INAPTO` ficam fora e têm levantamento separado em `reports/tse-2022-financial-analysis.md`. No Final/APTO, 21.675 ocorrências foram excluídas e 1.977 candidatos foram afetados; todas as linhas permanecem na sensibilidade.

## Exemplos legíveis, conferidos no SQLite

A tabela `expense_occurrences` conserva as referências a membro e linha do CSV. Os números abaixo são `_source_row` (cabeçalho como linha 1).

- **Igualdade exata:** candidato `20001614181`, AL, `SQ_DESPESA=51008743`, documento `493`. No membro `despesas_contratadas_candidatos_2022_AL.csv`, linhas 63 e 66 têm descrição `PANFLETOS EM PAPEL COCHE 15X21 CM` e R$ 1.743,75; a 63 foi mantida e a 66 excluída. Linhas 64, 65 e 68 formam outro grupo exato com descrição `PANFLETOS PAPEL COCHE 15X21 CM`, também R$ 1.743,75; a 64 foi mantida e as demais excluídas. A linha 67 e outras do mesmo `SQ_DESPESA` são distintas.
- **Mesmo documento, itens diferentes:** candidato `160001597847`, PR, `SQ_DESPESA=51841829`, documento `180`. As linhas 91–95 de `despesas_contratadas_candidatos_2022_PR.csv` registram caixa personalizada (R$ 1.890,00), adesivo vinil (R$ 115,00) e três banners/faixas (R$ 34,00, R$ 20,00 e R$ 84,00). Todas permanecem; nenhuma exclusão exata ocorreu nesse grupo documental.

Consultas no DB Browser for SQLite:

```sql
SELECT _source_row, SQ_CANDIDATO, SQ_DESPESA, NR_DOCUMENTO,
       DS_DESPESA, VR_DESPESA_CONTRATADA, _row_signature
FROM expense_occurrences
WHERE SQ_CANDIDATO = '20001614181' AND SQ_DESPESA = '51008743'
ORDER BY _source_row;
```

```sql
SELECT o._source_row AS linha_excluida,
       x.kept_source_row AS linha_mantida,
       o.SQ_CANDIDATO, o.SQ_DESPESA, o.NR_DOCUMENTO,
       o.DS_DESPESA, o.VR_DESPESA_CONTRATADA
FROM expense_dedup_exclusions AS x
JOIN expense_occurrences AS o
  ON o._source_member = x.source_member AND o._source_row = x.source_row
WHERE o.SQ_CANDIDATO = '20001614181' AND o.SQ_DESPESA = '51008743'
ORDER BY o._source_row;
```

## Artefatos e reprodução

`data/derived/2022/pilot.sqlite` contém 9 tabelas principais de auditoria/análise. `expense_occurrences` tem 1.139.275 linhas e 57 colunas: 53 colunas originais e quatro campos de auditoria (`_source_archive`, `_source_member`, `_source_row`, `_row_signature`). `expenses` contém 1.117.401 ocorrências do tratamento principal; `expense_dedup_exclusions` contém 21.874 exclusões e as referências mantidas. O SQLite mediu 2.193.813.504 bytes.

O comando completo executado foi:

```text
python -m tse_pilot run --manifest data/manifests/manifest-20261008T154908Z.json --output data/derived/2022
python -m tse_pilot duplicates --database data/derived/2022/pilot.sqlite --output reports/tse-2022-duplicate-diagnostics.json
python -m tse_pilot analyze --database data/derived/2022/pilot.sqlite --validation data/derived/2022/validation.json --output reports
python -m unittest discover -s tests -v
```

`validation.json` registra `status = approved`, todas as contagens fatais em zero e reconciliações exatas. O relatório final `reports/tse-2022-financial-analysis.md` contém os resultados executados, comparação entre mulheres e homens, levantamento INAPTO, pagamento complementar não integrado e limitações. 2026, redes sociais, PJe e backtests são etapas posteriores; não foram iniciados aqui.
