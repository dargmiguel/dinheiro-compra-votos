# Especificação — Investigação de dinheiro, atenção e votos

## Problem Statement

Como leitor e investigador, quero saber o que os dados eleitorais brasileiros sustentam sobre a relação entre **gasto declarado de campanha**, **engajamento público** e votação. Hoje não existe um pipeline reproduzível que conecte prestação de contas, candidaturas, resultados eleitorais, participação eleitoral e sinais públicos de atenção em uma mesma **unidade candidato-eleição**, mantendo explícitos os limites de associação, a cobertura das fontes e o risco de **inferência ecológica**.

Também falta uma forma auditável de responder à segunda pergunta: o que dados históricos conseguem explicar? Um modelo histórico precisa ser testado contra resultados conhecidos, sem ser apresentado como probabilidade de vitória em uma eleição atual. A ausência de versões congeladas, regras de junção, validação temporal e métricas de erro torna fácil produzir gráficos convincentes, mas não reproduzíveis.

O projeto começa sem código ou pipeline existente. Portanto, precisa estabelecer um núcleo de dados e testes de comportamento antes de adicionar dashboard, NLP ou fontes sociais de cobertura incerta.

## Solution

Construir uma investigação em três módulos associados:

1. **Dinheiro:** estudar candidaturas válidas a deputado federal, começando pelo piloto de 2022 e usando 2026 como estudo integrado principal. Estimar associação condicional entre o log do gasto declarado total e a participação de votos dentro da UF, com controles pré-eleitorais, efeitos fixos de UF e partido, diagnósticos e sensibilidades.
2. **Camada de atenção:** relacionar gastos e publicidade a métricas públicas por plataforma, mantendo cada métrica na sua unidade e usando uma **janela temporal comparável**. TSE e YouTube via API oficial formam o núcleo preferencial; Meta e Google Trends são módulos condicionais. Raspagem só pode ocorrer em páginas públicas e permitidas, com limites, snapshots, minimização e reexecução possível. Bloqueios não serão contornados.
3. **Backtest histórico:** usar município como unidade principal para comparecimento e votação geográfica, com agregações para UF e Brasil. Treinar apenas com informação disponível antes de cada eleição conhecida, avaliar em eleição ou período posterior conhecido, comparar com baseline e reportar erro por tamanho de município. A disputa presidencial de 2022 entre Lula e Bolsonaro é um caso histórico, não uma previsão atual.

A execução deve começar com um piloto pequeno em 2022 para validar downloads, versões, chaves, deduplicação, cobertura e disponibilidade social. Só depois o pipeline será aplicado à versão congelada de 2026. O resultado público será um repositório reproduzível com metodologia, dados derivados e figuras; o artigo no LinkedIn será a narrativa, e um dashboard será opcional.

## User Stories

1. Como leitor de uma investigação eleitoral, quero distinguir associação condicional de causalidade, para não interpretar um coeficiente observacional como prova de que dinheiro causou votos.
2. Como investigador, quero representar cada observação como uma unidade candidato-eleição, para evitar misturar campanhas, cargos e contextos eleitorais incompatíveis.
3. Como investigador, quero começar com candidaturas válidas a deputado federal, para comparar campanhas que disputam o mesmo cargo e manter a primeira população interpretável.
4. Como investigador, quero preservar candidaturas com votos zero e contas zeradas quando os registros forem válidos, para não remover a cauda da população por conveniência.
5. Como leitor, quero ver claramente que 2022 serve para desenvolver e validar o pipeline, enquanto 2026 é o estudo integrado principal, para entender a separação entre desenvolvimento e análise.
6. Como mantenedor dos dados, quero criar uma versão congelada com data de extração, URLs, nomes de arquivos e checksums, para reproduzir números mesmo depois de retificações nas fontes.
7. Como investigador, quero distinguir zero observado, ausência de conta e registro inválido, para não transformar dado ausente em gasto zero.
8. Como investigador, quero detectar duplicatas e junções ambíguas entre candidato, partido, UF, município e eleição, para não atribuir gastos ou votos à unidade errada.
9. Como analista, quero usar participação de votos dentro da UF como desfecho principal, para comparar desempenho relativo sem deixar o tamanho do eleitorado dominar a análise.
10. Como analista, quero manter votos brutos em log como sensibilidade, para verificar se a conclusão depende da transformação do desfecho principal.
11. Como analista, quero usar o log do gasto declarado total como exposição de gasto principal, para reduzir a influência da cauda sem perder a escala da campanha.
12. Como analista, quero testar gasto por eleitor e categorias de gasto como sensibilidades, para avaliar se a associação depende da normalização ou do tipo de despesa.
13. Como leitor, quero ver efeitos fixos de UF e partido e indicadores pré-eleitorais documentados, para saber quais diferenças estruturais foram ajustadas.
14. Como analista, quero evitar variáveis posteriores à campanha ou ao resultado, para impedir vazamento temporal e ajuste pós-tratamento.
15. Como analista, quero tratar extremos com diagnósticos e sensibilidades, para mostrar quando poucos candidatos muito grandes dominam a associação sem apagar observações silenciosamente.
16. Como leitor, quero ver intervalos, diagnósticos e resultados nulos, para avaliar precisão e instabilidade em vez de apenas um coeficiente destacado.
17. Como investigador, quero relacionar gastos, publicidade, publicações, alcance e engajamento público em uma camada de atenção separada, para ampliar a pergunta sem afirmar que atenção é apoio eleitoral.
18. Como analista de plataforma, quero manter métricas de visualização, curtida, comentário, seguidor e busca separadas, para não somar grandezas que não possuem a mesma definição.
19. Como analista, quero alinhar dados sociais e eleitorais por janelas temporais comparáveis, para não usar interações posteriores ao resultado como se fossem informação pré-eleitoral.
20. Como mantenedor, quero usar fontes oficiais e APIs quando disponíveis, para maximizar legitimidade, estabilidade e reexecução.
21. Como mantenedor, quero registrar a fonte social que ficou indisponível, bloqueada ou sem histórico suficiente, para que uma lacuna conhecida não seja confundida com ausência de engajamento público.
22. Como mantenedor, quero interromper uma coleta quando houver bloqueio, autenticação não disponível ou dúvida de permissão, para não contornar controles nem publicar uma coleta que não possa ser repetida legitimamente.
23. Como analista, quero publicar sentimento e temas apenas como módulo exploratório secundário validado, para não transformar sarcasmo, bots, moderação ou erro de classificação em voto.
24. Como investigador, quero construir backtests históricos usando somente informação disponível antes de cada resultado conhecido, para medir capacidade explicativa sem criar uma previsão de eleição atual.
25. Como analista histórico, quero usar municípios como unidade principal e agregar para UF e Brasil, para preservar variação espacial sem fazer inferência sobre eleitores individuais.
26. Como analista histórico, quero separar comparecimento de votação como desfechos, para não esconder dois fenômenos em uma única métrica.
27. Como analista histórico, quero comparar o modelo com um baseline explícito, para saber se a complexidade acrescenta capacidade explicativa real.
28. Como leitor, quero ver erro absoluto, erro relativo definido e desempenho por tamanho de município, para identificar onde o modelo falha.
29. Como analista, quero usar validação temporal ou leave-one-election-out, para não avaliar um modelo no mesmo conjunto usado para ajustá-lo.
30. Como mantenedor de dados, quero guardar dados brutos imutáveis e produzir tabelas tratadas com chaves e testes de duplicidade, para separar evidência original de transformação.
31. Como colaborador, quero encontrar manifesto, versões, decisões metodológicas e limitações no repositório, para refazer a análise sem depender de conhecimento oral.
32. Como investigador, quero definir população, exposição, desfecho, controles e métricas antes de examinar todos os resultados, para separar análise principal, exploração e sensibilidades.
33. Como leitor brasileiro, quero que a narrativa evite “dinheiro compra votos” como conclusão automática, para que associações fracas, nulas ou contrárias à hipótese também sejam publicadas.
34. Como autor, quero gerar figuras e tabelas a partir de dados derivados versionados, para que o artigo público não dependa de cópias manuais.
35. Como usuário do repositório, quero uma narrativa no LinkedIn apoiada pelo repositório reproduzível, para obter acessibilidade sem sacrificar auditoria.
36. Como mantenedor, quero adiar o dashboard até o pipeline e a documentação estarem estáveis, para não priorizar interface em detrimento da validade da investigação.
37. Como responsável pelo escopo, quero um piloto de viabilidade em 2022 com critérios de parada, para detectar cedo incompatibilidades de arquivos, chaves, cobertura e APIs.
38. Como agente de implementação, quero um único seam de teste no artefato do pipeline — versão congelada de entrada até tabelas canônicas e saídas analíticas —, para validar comportamento externo com o menor acoplamento possível.

## Implementation Decisions

- O sistema será organizado em módulos de ingestão, versionamento de fonte, normalização, validação, modelagem e publicação de artefatos. O desenho deve manter um contrato de dados canônico entre ingestão e análise, em vez de permitir que cada notebook defina sua própria interpretação.
- Cada fonte produzirá uma versão identificável. A versão congelada deve carregar data, origem, arquivos e checksums. Atualizações da fonte gerarão uma nova versão, nunca substituirão silenciosamente uma versão usada em publicação.
- A unidade canônica de financiamento será a unidade candidato-eleição, com identificadores estáveis e dimensões explícitas para cargo, eleição, UF, partido, município e situação da candidatura.
- A população principal será composta por candidaturas válidas a deputado federal. Registros inválidos terão motivo codificado; zeros válidos serão preservados; ausências não serão convertidas automaticamente em zero.
- A base tratada deverá permitir auditoria de duplicidade, chaves ausentes, correspondências ambíguas, contas inválidas e divergências entre versões. O pipeline deve falhar de forma explícita quando uma chave necessária não puder ser resolvida.
- O desfecho principal será participação de votos dentro da UF. Votos brutos transformados serão sensibilidade. Comparecimento e votação histórica permanecerão desfechos separados.
- A exposição principal será log do gasto declarado total. Gasto por eleitor, categorias de despesa e outras normalizações só serão sensibilidades rotuladas.
- O modelo de participação usará uma família apropriada a desfecho fracionário limitado entre zero e um. Uma especificação OLS ou transformação simples poderá existir como sensibilidade interpretável, não como substituição silenciosa do modelo principal.
- A especificação principal usará efeitos fixos de UF e partido, indicadores pré-eleitorais documentados e incerteza apropriada à estrutura dos dados. Variáveis posteriores à campanha, ao resultado ou derivadas do próprio desfecho serão proibidas no conjunto principal.
- A análise de financiamento será associativa. A documentação deve repetir que endogeneidade, qualidade do candidato, incumbência, apoio partidário, geografia e competitividade impedem uma leitura causal direta.
- A camada de atenção será conectada por análises sequenciais, não por um índice único nem por um modelo de mediação causal. Cada plataforma conservará sua própria definição e cobertura.
- TSE será a fonte preferencial para candidaturas, contas e resultados. YouTube poderá entrar por API oficial. Meta e Google Trends entrarão como módulos condicionais, apenas quando a disponibilidade, definição da métrica e janela forem verificáveis.
- Qualquer raspagem ficará limitada a páginas públicas e permitidas, com limites de requisição, data, minimização e reexecução. Bloqueios, autenticação não disponível, ausência de histórico ou dúvida de permissão encerram aquela coleta e geram uma lacuna documentada.
- Sentimento e temas serão secundários. Só serão publicados com amostra, classificador, avaliação e limitações documentados; nunca serão tratados como proxy direto de voto.
- O módulo histórico terá município como unidade principal e UF/Brasil como agregações. Ele usará somente informação disponível antes do resultado-alvo. A disputa presidencial de 2022 entre Lula e Bolsonaro será um caso de avaliação retrospectiva, não uma previsão atual.
- Backtests usarão separação temporal ou leave-one-election-out, baseline explícito e métricas de erro absoluto, erro relativo definido e calibração ou estratificação por tamanho de município.
- A ordem de execução será: piloto de 2022; congelamento e tratamento da base; análise de financiamento; verificação da camada de atenção; incorporação da versão de 2026; backtests históricos; publicação.
- O pipeline manterá dados brutos imutáveis e tabelas derivadas em formato consultável, com manifesto de transformação. Notebooks poderão explorar dados, mas não serão a única fonte de verdade nem substituirão o pipeline reproduzível.
- A análise principal, hipóteses, população, controles, métricas e sensibilidades deverão ser definidos antes da leitura completa dos resultados. Exploração posterior será rotulada como exploratória.
- A publicação priorizará repositório, metodologia e figuras. O LinkedIn será uma camada narrativa. Dashboard só será desenvolvido depois do portão de viabilidade e sem substituir documentação.
- Não há código existente ou ADRs aplicáveis no repositório atual. Os seams e módulos propostos são novos e devem permanecer pequenos, determinísticos e orientados a artefatos.

## Testing Decisions

- O seam principal será o pipeline de artefato: uma versão congelada de entrada deve produzir tabelas canônicas, diagnósticos e saídas analíticas reproduzíveis. Esse é o ponto mais alto disponível porque o repositório ainda não tem módulos existentes; ele testa comportamento observável sem prender testes a funções internas.
- Testes devem usar fixtures pequenas e determinísticas que representem candidaturas, contas, votos, municípios, versões retificadas, zeros válidos, ausências e duplicidades. Não devem chamar APIs reais em testes determinísticos.
- O teste de ingestão deve demonstrar que metadados de versão, origem e checksum acompanham os dados e que uma fonte mutada gera uma nova versão em vez de substituir a anterior.
- O teste de normalização deve demonstrar que a unidade candidato-eleição preserva cargo, eleição, UF, partido e candidato corretos; que duplicidades são detectadas; e que ausência, zero válido e registro inválido não são confundidos.
- O teste do portão de viabilidade deve produzir um relatório observável de cobertura, chaves, duplicidades e fontes sociais disponíveis. O pipeline deve parar quando um critério obrigatório falhar.
- O teste de financiamento deve verificar, em dados conhecidos, a participação de votos dentro da UF, o log da exposição de gasto, a população de candidaturas válidas e a presença das sensibilidades. Deve validar resultados e limites, não a implementação de uma biblioteca estatística específica.
- O teste de vazamento deve incluir uma observação disponível somente depois do resultado e confirmar que ela não entra nos predictores do backtest ou da análise principal.
- O teste de backtest deve usar uma divisão temporal conhecida, comparar com baseline e conferir que as métricas de erro são calculadas no conjunto de avaliação, incluindo estratificação por tamanho do município.
- O teste da camada de atenção deve verificar que métricas de plataformas diferentes permanecem separadas, que janelas temporais incompatíveis são rejeitadas ou marcadas, e que uma fonte bloqueada vira lacuna documentada em vez de ser contornada.
- O teste de publicação deve verificar que tabelas e figuras são geradas a partir da versão derivada escolhida e carregam referência à versão congelada. Não deve testar apenas se um arquivo existe ou se uma lista não está vazia.
- O teste de sentimento, se implementado, deve usar amostra anotada e medir comportamento do classificador em português brasileiro; não deve validar a tese de que sentimento representa voto.
- Testes devem cobrir transições e erros relevantes: fonte mutável, chave ambígua, arquivo ausente, duplicata, zero válido, conta inválida, métrica social indisponível, bloqueio de coleta e vazamento temporal.
- Não há prior art de testes neste repositório: a exploração encontrou apenas documentação, sem código, fixtures ou harness existentes. A primeira implementação deve criar o seam de artefato e manter o restante das abstrações internas subordinado a ele.

## Out of Scope

- Estimar efeito causal de gastos, publicidade, engajamento público ou atenção sobre votos.
- Produzir probabilidade de vitória ou previsão de uma eleição atual.
- Inferir comportamento, intenção ou apoio de eleitores individuais a partir de dados municipais, estaduais ou de plataforma.
- Misturar cargos, eleições ou unidades geográficas incompatíveis na análise principal.
- Usar gasto por voto como exposição ou desfecho principal.
- Exigir cobertura histórica completa de Instagram, Facebook ou qualquer plataforma antes de publicar o núcleo disponível.
- Contornar bloqueios de IP, autenticação, controles de acesso ou termos de uso.
- Transformar curtidas, comentários, seguidores, visualizações, buscas ou sentimento em votos equivalentes.
- Usar análise de sentimento como desfecho principal ou proxy direto de voto.
- Treinar o backtest com o resultado que ele deve reproduzir ou com informação posterior ao momento simulado.
- Criar um índice único de dinheiro, atenção e votação.
- Construir o dashboard antes do portão de viabilidade e da documentação do pipeline.
- Prometer uma análise de 2026 sem versão congelada e metadados de extração.
- Tratar a ausência de uma conta ou métrica como gasto ou engajamento zero.
- Esconder resultados nulos, associações fracas, falhas de cobertura ou sensibilidades divergentes.
- Adicionar novas plataformas, cargos, eleições ou modelos sem atualizar a especificação principal e o critério de viabilidade.

## Further Notes

- O design document da investigação é a fonte de decisões de domínio e deve continuar sendo atualizado quando uma decisão difícil mudar.
- O primeiro entregável de código deve ser o piloto de viabilidade em 2022, não o dashboard nem a coleta social completa.
- O risco de escopo é alto: engenharia de dados, estatística, APIs, NLP e visualização são frentes diferentes. O portão de viabilidade deve produzir uma decisão explícita sobre o que entra no núcleo e o que fica condicional.
- O título público pode permanecer provocativo, mas cada resultado deve usar “associação”, “exposição de gasto”, “engajamento público” e “participação eleitoral” com as definições do glossário.
- O projeto deve registrar limitações de cobertura e acesso como resultado metodológico, não como detalhe descartável.
