# Protocolo pré-especificado — análise secundária por raça/cor (TSE 2022)

Registrado antes de calcular qualquer estatística ou estimativa por raça/cor nesta retomada. É uma análise secundária adicionada após os resultados iniciais de votos e eleição. Reutiliza `data/derived/2022/pilot.sqlite`, a validação existente e o relatório atual; não altera a análise principal nem a base canônica.

## População e grupos

Unidade: candidatura APTO a deputado federal, 1º turno de 2022, com voto nominal e denominador válido observados. Contar raça/cor na população completa APTO antes das restrições. Comparação analítica: autodeclaração `BRANCA` contra `PRETA` + `PARDA`. `AMARELA`, `INDÍGENA`, `NÃO INFORMADO`, `NÃO DIVULGÁVEL`, valor ausente e quaisquer outras categorias ficam fora apenas da comparação binária; permanecem na base e são contadas separadamente. Preservar cada categoria fora da comparação como rótulo distinto no resumo. Não inferir raça por nome, foto ou outra variável.

A coorte completa de comparação exige despesas `Final` nas duas representações (deduplicada e todas as linhas), voto e controles completos — UF, partido, idade na eleição, sexo e escolaridade — para que os dois cenários usem as mesmas candidaturas. Informar grupos na população APTO, grupos na coorte completa e exclusões por ausência de despesa/controle.

## Descrições e denominadores

Por grupo, mostrar N, despesa contratada deduplicada mediana e intervalo interquartil, votos nominais mediana e intervalo interquartil, participação de votos nominais no total oficial válido da UF mediana e intervalo interquartil, e quantidade/proporção eleita. Apresentar despesa também com todas as linhas como sensibilidade. Eleito = códigos oficiais `2` (`ELEITO POR QP`) e `3` (`ELEITO POR MÉDIA`); não eleito = `4` (`NÃO ELEITO`) e `5` (`SUPLENTE`). Denominador da proporção eleita = número de candidaturas do grupo com resultado classificável; contar à parte ausentes/outros códigos, sem os forçar a uma classe. Publicar os denominadores explícitos. Não usar custo por voto como preditor.

## Interação despesa×raça

Desfecho: participação fracionária de votos nominais válidos na UF. Exposição: `log1p(despesa contratada em R$)`. GLM Binomial com link logit, termo indicador `pretas+pardas` (referência: brancas), termo principal de despesa e interação `log1p(despesa) × pretas+pardas`. Ajustar pelos controles acordados — UF, partido, idade na data da eleição, sexo e escolaridade — e usar erros-padrão robustos HC1. Estimar `deduplicado` como principal e repetir com `todas as linhas`, na mesma coorte. Verificar posto da matriz e convergência; publicar coeficientes, IC 95%, erro-padrão e valor-p. O termo de interação compara inclinações na escala logit; não é uma diferença causal nem uma variação direta em pontos percentuais.

## Suporte e curvas

Aplicar as regras abaixo separadamente à exposição deduplicada e a todas as linhas; não relaxar limites após observar coeficientes:

1. A unidade de suporte contextual é a célula `UF × partido`. Uma célula é elegível quando há pelo menos **10 candidaturas de cada grupo** na coorte completa. Reportar N e cobertura de candidaturas em células elegíveis, por grupo, e diagnósticos marginais por UF e partido.
2. Em cada célula elegível e grupo, calcular P10 e P90 da despesa. O suporte nacional inicial é a interseção dos P10–P90 calculados sobre todas as candidaturas das células elegíveis, separadamente por grupo; ele define apenas os pontos candidatos. Cada ponto ainda precisa passar pela checagem local do item seguinte.
3. Em cada ponto candidato, uma célula só apoia o gasto se o valor estiver dentro da interseção dos intervalos locais P10–P90 de ambos os grupos. Só exibir ponto se as células apoiadas representarem **ao menos 80% de cada grupo** da coorte completa. Informar cobertura por grupo e N de perfis usados em cada ponto; não ligar linhas através de lacunas sem suporte.
4. Em cada ponto apoiado, fixar despesa e prever ambos os grupos sobre a mesma distribuição de perfis observados nas células apoiadas. ICs pontuais de 95% para a média padronizada pelo método delta, usando covariância HC1; não são intervalos individuais.
5. Exportar diagnósticos por UF e partido — contagem de cada grupo, faixas locais P10–P90, interseção e participação da coorte representada — para evidenciar onde a sobreposição nacional não assegura cobertura local.

Se os critérios não produzirem curva sustentada, publicar a insuficiência de suporte e os diagnósticos; não desenhar uma curva extrapolada.

## Interpretação e saída

Identificar a análise como secundária e posterior aos resultados iniciais. Diferenças descritivas ou ajustadas não demonstram causalidade nem discriminação; despesa contratada declarada não significa despesa paga ou necessariamente recurso público. Publicar resumo, tabelas CSV, curvas e cobertura no relatório existente e no PR, com referência à versão congelada. Não montar dashboard/carrossel nem iniciar comparação financeira com 2026.