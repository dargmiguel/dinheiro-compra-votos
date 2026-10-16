# Protocolo pré-especificado — proporção eleita ajustada por raça/cor (TSE 2022)

Análise secundária posterior aos primeiros resultados e complementar à comparação eleitoral descritiva já publicada. Reutiliza a coorte binária da análise secundária de raça/cor e a base derivada existente; não substitui o resultado principal de participação de votos.

## População e grupos

Comparar candidaturas APTO a deputado federal, 1º turno de 2022, autodeclaradas `BRANCA` com `PRETA` + `PARDA`. Para manter a população idêntica entre especificações, usar apenas candidaturas com resultado classificável (códigos oficiais 2, 3, 4 ou 5), voto e denominador observados, controles completos — UF, partido, idade, sexo e escolaridade — e despesa `Final` presente tanto na versão deduplicada quanto em todas as linhas. Assim, os modelos sem despesa e com despesa (em ambas as representações) não mudam de coorte. Informar N e resultados por grupo; não recodificar outras categorias raciais.

## Descrição e estimandos

Eleito = códigos `2` (`ELEITO POR QP`) ou `3` (`ELEITO POR MÉDIA`); não eleito = `4` (`NÃO ELEITO`) ou `5` (`SUPLENTE`). Mostrar proporção observada por grupo, com numerador e denominador. Se a comparação ajustada for sustentada, restringir todas as especificações ao mesmo conjunto de candidaturas nas células UF×partido aprovadas pelo critério de suporte; ajustar primeiro um logit binomial com grupo racial e controles, depois o mesmo logit acrescentando `log1p(despesa contratada em R$)`. Deduplicado é principal; repetir acrescentando despesa de todas as linhas como sensibilidade. Não incluir votos ou custo por voto como preditor.

Apresentar probabilidades ajustadas por grupo como médias de previsões sobre os mesmos perfis da população restrita com suporte, e a diferença pretas+pardas menos brancas em pontos percentuais. Incerteza por método delta com covariância robusta HC1; ICs são pontuais para essas médias e diferença, não intervalos individuais.

## Regra de suporte e estabilidade

Antes de ajustar, contar candidaturas em células `UF × partido` da população comum. Publicar ajuste somente se células com pelo menos 10 candidaturas em cada grupo cobrirem ao menos 80% de cada grupo; fit e padronização usam somente candidaturas dessas células e a mesma coorte em todos os modelos. Exigir também ao menos 10 eleitas e 10 não eleitas em cada grupo nessa coorte; matriz de desenho de posto completo; convergência; covariância, erros-padrão, previsões e ICs finitos. Se qualquer condição falhar, não publicar probabilidades ajustadas ou diferença ajustada; manter apenas proporções observadas e explicar a limitação. Não reduzir os limiares depois de olhar os resultados.

## Interpretação

A mudança entre proporções ajustadas sem e com despesa é associativa. Não demonstra que gastos expliquem a diferença, nem prova discriminação ou causalidade. Despesa contratada declarada não significa pagamento efetivo nem recurso necessariamente público.
