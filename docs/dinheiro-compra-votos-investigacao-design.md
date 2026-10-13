# Dinheiro compra votos? Uma investigação das eleições brasileiras

## Resumo

Esta investigação estuda, em módulos conectados mas não confundidos, a relação entre dinheiro declarado, atenção pública e resultados eleitorais. A análise financeira reproduzível de 2022 é a entrega corrente e vem antes de 2026, redes sociais, PJe e backtests. A camada de atenção e os ciclos posteriores não bloqueiam a análise contratada de 2022. Todas as estimativas financeiras são associativas, não causais.

## Termos

- **Gasto declarado de campanha** — valores informados na prestação de contas eleitoral oficial de um candidato em uma eleição. É um insumo observado, não prova de que o gasto causou votos. Evitar: “investimento”, “dinheiro gasto causou votos”, “orçamento de campanha”.
- **Unidade candidato-eleição** — um candidato concorrendo em uma eleição para um cargo, junto da localidade e do contexto eleitoral relevantes. Evitar: “linha do candidato”, “registro da campanha”.
- **Backtest histórico** — modelo treinado apenas com eleições disponíveis antes de uma eleição conhecida e avaliado contra o resultado já observado. Evitar: “previsão da eleição atual”, “probabilidade de vitória de Lula”, “projeção”.
- **Inferência ecológica** — risco de inferir comportamento de eleitores individuais a partir de resultados geográficos agregados e dados de participação. Evitar: “conclusão no nível do eleitor”, “o que os eleitores fizeram”.
- **Versão congelada dos dados** — cópia identificada por data, URLs, arquivos e checksums, usada para manter a análise reproduzível mesmo quando o TSE atualiza registros. Evitar: “dados finais”, “arquivo atual”.
- **Participação eleitoral** — comparecimento ou proporção de eleitores que votaram, sempre com denominador e unidade geográfica ou temporal definidos. Evitar: “engajamento”, “interesse do eleitor”.
- **Exposição de gasto** — variável observada que representa o gasto declarado antes da transformação estatística, com unidade, período e regra de inclusão documentados. Evitar: “dose de dinheiro”, “investimento recebido”, “efeito do gasto”.
- **Engajamento público** — interações ou métricas observáveis em uma plataforma, como visualizações, curtidas, comentários e compartilhamentos, sem tratá-las como apoio eleitoral individual. Evitar: “apoio”, “voto digital”, “popularidade real”.
- **Camada de atenção** — módulo que relaciona gastos e publicidade a sinais públicos de alcance ou interação em redes e buscas, separado do módulo de votação. Evitar: “conversão garantida”, “funil causal”, “intenção de voto”.
- **Janela temporal comparável** — período definido antes da análise em que gasto, publicação, atenção e votação podem ser alinhados sem usar informação posterior ao resultado. Evitar: “período escolhido depois”, “antes e depois misturados”, “tempo real”.
- **Vazamento temporal** — uso, na construção ou no ajuste de um modelo, de informação que só estaria disponível depois do momento que o *backtest* pretende simular. Evitar: “olhar o futuro”, “viés de atualização”, “previsão perfeita”.

## Por que

A pergunta do projeto é “Dinheiro compra votos?”. A investigação deve testar o que os dados sustentam sem transformar correlação em causalidade. A proposta começa com gastos declarados, votos e controles eleitorais; depois amplia a pergunta para “Dinheiro compra atenção? E atenção se converte em votos?”. A conexão entre os módulos é substantiva, não uma autorização para tratar uma associação entre gastos, plataformas e votação como uma cadeia causal identificada.

A investigação também quer saber o que os dados históricos conseguem explicar. Resultados anteriores podem ser usados para construir modelos retrospectivos e testá-los contra eleições já encerradas. Isso é diferente de produzir uma probabilidade de vitória de Lula, Bolsonaro ou qualquer outro candidato em uma disputa atual.

## Decisões travadas

Estas decisões têm consequências difíceis de reverter, mudam o desenho da investigação ou seriam surpreendentes sem contexto.

### Q1 — Estimando principal: associação condicional, não causalidade

A análise de financiamento estimará a associação condicional entre gasto declarado e votos, com controles explícitos e limites causais no texto. A razão é que gasto é endógeno à qualidade do candidato, apoio partidário, incumbência, geografia e competitividade esperada. Os dados administrativos observacionais disponíveis não identificam, sozinhos, o efeito causal do gasto. A alternativa causal foi rejeitada por exigir identificação mais forte; a descrição sem estimativa formal foi rejeitada porque desperdiçaria variação e controles úteis.

### Q2 e Q10 — Papéis de 2022 e 2026

A decisão original priorizou 2026, mas a ordem operacional foi corrigida: concluir primeiro a análise financeira reproduzível de 2022; 2026 e a integração com atenção são etapas posteriores. Não agrupar ciclos automaticamente nem permitir que módulos futuros bloqueiem a entrega 2022.

### Q4 — Congelamento das fontes

Cada versão usada terá data de extração, URLs, nomes dos arquivos e checksums. Retificações ou atualizações do TSE serão uma nova versão, não uma sobrescrita silenciosa. Consultar sempre o arquivo mais recente foi rejeitado porque não reproduz números já publicados; extrair uma vez sem metadados perde a trilha de auditoria.

### Q6 — Desfecho de votos

O desfecho principal será a participação de votos do candidato dentro da UF; votos brutos serão mantidos em log como sensibilidade. Votos brutos misturam desempenho relativo com tamanho do eleitorado e escala territorial. Custo por voto foi rejeitado como desfecho porque usa o próprio resultado no denominador e é instável em campanhas pequenas. A condição de eleito perde informação e muda a pergunta para classificação.

### Q7 — Exposição de gasto

A exposição principal será o log do gasto declarado total. Gasto por eleitor e categorias de gasto serão sensibilidades. O log reduz a influência mecânica da cauda sem apagar a escala da campanha. Gasto por voto usa o desfecho no denominador; gasto bruto deixa valores extremos dominarem; uma única normalização esconderia uma escolha substantiva.

### Q8 — Camada integrada de atenção

O projeto terá três camadas: dinheiro, redes sociais/atenção e votação. A análise integrada investigará associações entre gastos, publicidade, publicações, alcance, engajamento e votação, com controles e limitações documentados. A resposta não escolheu um conjunto fechado de controles da pergunta original; ela ampliou o escopo do projeto. Essa ampliação será tratada como três módulos associados, não como prova de que atenção é apoio eleitoral.

### Q11, Q13 e Q16 — Fontes, raspagem e bloqueios

O núcleo deverá usar o TSE para candidaturas, contas e resultados; YouTube pela API oficial quando disponível; Meta e Google Trends como módulos condicionais documentados. A proposta inicial admitiu raspagem como fallback. A regra final é mais restrita: só páginas públicas e permitidas, com data, limites de requisição, minimização de dados e possibilidade de reexecução. Se uma fonte bloquear acesso, exigir autenticação não disponível, não preservar histórico ou criar dúvida de permissão, a coleta para essa fonte deve parar, o motivo deve ser registrado e a métrica deve ficar fora do núcleo. Não se deve contornar bloqueios. Uma base comercial pode ser uma sensibilidade licenciada, mas não substitui a transparência do núcleo.

### Q12 — Relação entre dinheiro, atenção e votação

Serão feitas três análises associativas sequenciais, com candidato, localidade, medidas e janelas temporais alinhados. A investigação não chamará a sequência de mediação causal. Um modelo de mediação causal exige hipóteses fortes e dados de plataforma que podem faltar; um índice único destruiria interpretações; módulos totalmente isolados perderiam a conexão investigativa.

### Q14 — Comparabilidade das plataformas

Cada plataforma terá métricas próprias e uma janela temporal comparável. Só serão comparadas ou agregadas medidas cuja definição e cobertura estejam verificadas; análises entre plataformas serão secundárias. Curtidas, comentários, visualizações, seguidores e buscas não são unidades intercambiáveis. Seguidores representam audiência acumulada, não atenção no período; sentimento não é métrica universal e depende da cobertura textual e da qualidade do classificador.

### Q15 — Finalidade do módulo histórico

O módulo fará *backtests* retrospectivos de comparecimento e votação geográfica em eleições conhecidas, inclusive a eleição presidencial de 2022, usando apenas informações que estariam disponíveis antes de cada resultado. Ele reportará o erro contra o resultado observado. Não produzirá probabilidade de vitória em uma eleição atual. A alternativa causal foi rejeitada porque exigiria outro desenho; mapas sem modelo e erro não testariam capacidade explicativa.

### Q17 — Unidade geográfica histórica

O município será a unidade principal, com agregações para UF e Brasil. Votação e comparecimento serão desfechos separados. O município oferece resolução espacial publicável e ainda permite auditoria e agregação. Usar apenas UF perde variação; usar seção como unidade principal pode exigir compatibilização histórica e cobertura mais frágeis; inferir comportamento individual seria inferência ecológica indevida.

### Q18 — Validação histórica

A validação será temporal ou *leave-one-election-out*, com baseline explícito, métricas de erro absoluto, erro relativo definido e calibração por tamanho do município. O mesmo conjunto não poderá servir para ajustar e avaliar o resultado que o modelo pretende reproduzir. R² dentro da amostra foi rejeitado como único teste; transformar desempenho histórico em probabilidade atual muda o produto; mapas sem métricas selecionam a narrativa.

### Q19 — Base de dados e proveniência

Dados brutos serão guardados de forma imutável, acompanhados de manifesto de versões e checksums. As tabelas tratadas serão produzidas em SQL ou Parquet, com chaves e testes de duplicidade explícitos. Notebooks não serão a única fonte de verdade; uma tabela final sem origem não basta; um banco vivo não poderá substituir silenciosamente os registros publicados.

### Q22 — Família de modelo para participação

O modelo principal será apropriado a um desfecho fracionário limitado entre zero e um, com especificação prévia. OLS ou uma transformação simples poderá ser sensibilidade transparente. A participação pode ter valores muito pequenos e zeros; OLS pode prever fora do intervalo; eleito/não eleito descarta informação; escolher uma máquina-preta apenas pelo ajuste prejudica a interpretação e não resolve confundimento.

### Q23 — Robustez e incerteza

Antes de olhar todos os resultados, serão fixados pergunta, população, exposição, desfecho, controles e métricas. A publicação separará análise principal, exploração e sensibilidades. Não será escolhida depois a especificação que melhor conta a história, nem publicada apenas a combinação significativa entre muitos cortes. Intervalos e diagnósticos serão parte do resultado, não decoração.

## Protocolo financeiro do piloto TSE 2022

Este protocolo específico rege a análise de 2022; ele não altera silenciosamente a população de outros ciclos.

- **População:** candidaturas a deputado federal `APTO` (`CD_SITUACAO_CANDIDATURA = 12`) no snapshot congelado são o principal. Isso não reconstitui validade na data da eleição. `INAPTO` fica em levantamento separado de despesas, por tipo de prestação.
- **Prestações:** `Final` é principal; demais tipos são apresentados separadamente. Não se presume qual versão foi a última recepcionada com sucesso.
- **Despesas:** o principal é log do total `VR_DESPESA_CONTRATADA` declarado em `Final`, usando a regra de igualdade exata nos 53 campos originais por snapshot/membro; todas as linhas permanecem como sensibilidade auditável. A escolha não confirma identidade econômica oficial. Despesas pagas, se integradas e validadas, são medida complementar separada; sua integração não bloqueia a análise contratada.
- **Votos:** para deputado federal no 1º turno de 2022, a participação do candidato usa votos nominais válidos divididos pelo total oficial de votos válidos da UF/cargo, incluindo legenda. O denominador é calculado antes dos filtros de situação `APTO` e prestação `Final`; basta uma fonte oficial de total válido, sem exigir detalhe partidário.
- **Controles:** UF, partido, idade na eleição, sexo, raça e escolaridade; comparar com ajuste apenas por UF/partido. Estado civil e ocupação ficam para descrição/sensibilidade. Partido e federação não entram simultaneamente sem avaliação de redundância.
- **Análise secundária:** permitir que a associação despesas–votos varie entre mulheres e homens; reportá-la como associação, sem interpretação causal.
- **Critério de aprovação:** zero erros fatais; fonte oficial e agregados reconciliados; chaves, checksums e comandos reproduzíveis verificados; exclusões auditáveis; sensibilidades e limitações documentadas. Zero observado, ausência e registro inválido devem permanecer distintos. Ausências conhecidas e repetições exatas cobertas pela regra acordada não bloqueiam sozinhas; as demais validações obrigatórias continuam valendo.



## Escolhas rotineiras

- **Q3 — Estrutura editorial:** um artigo terá duas partes explicitamente separadas, com implementação começando pelo financiamento. A conexão conceitual será preservada sem transformar os módulos em um único modelo.
- **Q5 — População geral:** entram candidaturas operacionalmente válidas a deputado federal, preservando votos zero e contas zeradas quando os registros forem válidos. Eleitos, somente candidatos com valores positivos e limiares serão sensibilidades, não a população principal. Para o piloto TSE 2022, vale a regra específica de APTO no snapshot registrada acima.
- **Q9 — Extremos e registros problemáticos:** zeros válidos serão preservados; registros inválidos serão excluídos com motivo codificado; extremos serão tratados por diagnóstico e sensibilidade, não por limpeza silenciosa, winsorização automática ou imputação sem justificativa.
- **Q20 — Sentimento e temas:** entram apenas como módulo exploratório secundário, com amostra, classificador, avaliação e limitações documentados. Não serão usados como proxy direto de voto. Comentários incompletos, sarcasmo, bots, moderação e viés de amostragem devem ser explicitados.
- **Q21 — Entrega:** o repositório reproduzível com metodologia, dados derivados e figuras é a entrega de verificação; o LinkedIn é a narrativa pública; o dashboard é opcional e só entra se não prejudicar congelamento, auditoria e documentação.
- **Q24 — Primeiro portão:** concluir a análise financeira de 2022 com fontes congeladas, chaves, deduplicação, denominador reconciliado, modelos, sensibilidades e limitações. Disponibilidade social não é critério de bloqueio; módulos de atenção, 2026 e backtests ficam para depois.

## Fatos verificados

- O diretório estava sem arquivos quando o projeto foi inicialmente inspecionado; desde então, pipeline, SQLite derivado, testes e relatórios foram criados.
- O ZIP congelado de prestação de contas contém despesas pagas por UF com `SQ_PRESTADOR_CONTAS` e `VR_PAGTO_DESPESA`; sua integração ampla ainda não foi validada e é complementar. A análise contratada não depende dela.
- A fonte oficial de totais válidos por UF, incluindo legenda, foi adicionada ao manifesto de 2022. O processamento valida os componentes de legenda e reconcilia nominal por UF contra a fonte de votos por candidato; o resultado está registrado no relatório e CSV por UF.

## Riscos

1. **Confundimento e endogeneidade:** candidatos com mais apoio prévio ou estrutura partidária podem gastar mais e obter mais votos. O resultado principal será associação, não causalidade.
2. **Inferência ecológica:** resultados municipais ou de UF não revelam comportamento individual. A redação não poderá dizer que determinado grupo de eleitores comprou ou recebeu atenção.
3. **Mutabilidade de 2026:** retificações, arquivos substituídos e datas de extração diferentes podem mudar números. Checksums e versões são obrigatórios.
4. **Junção de entidades:** nomes, números, partidos, candidaturas e localidades podem gerar duplicatas ou correspondências erradas. A unidade candidato-eleição e chaves testadas precisam ser definidas antes do modelo.
5. **Contas incompletas ou inválidas:** ausência de registro não equivale a gasto zero. A regra de validade deverá distinguir zero observado, ausência e registro inválido.
6. **Cauda e escala:** poucas campanhas muito grandes podem dominar a associação. Log, diagnósticos e sensibilidades precisam acompanhar a estimativa principal.
7. **Disponibilidade de redes:** Meta pode não oferecer histórico completo de alcance; YouTube e outras fontes podem mudar APIs; Google Trends é interesse relativo, não intenção de voto.
8. **Raspagem e acesso:** bloqueios de IP, autenticação, termos, robots, dados pessoais e mudanças de layout podem impedir coleta ou torná-la não reproduzível. Bloqueio não será contornado.
9. **Métricas não equivalentes:** curtida, comentário, visualização, seguidor, alcance e busca medem coisas diferentes e podem ter cobertura temporal desigual.
10. **NLP em português brasileiro:** sarcasmo, bots, moderação, amostragem e classificação errada tornam sentimento inadequado como desfecho principal sem validação.
11. **Vazamento temporal:** atualizações pós-eleição, resultados finais, engajamento posterior ou dados derivados do próprio resultado não podem entrar na construção do *backtest*.
12. **Múltiplas comparações:** muitos cortes por UF, partido, plataforma, categoria e janela aumentam falsos positivos. A análise principal e sensibilidades devem ser definidas antes.
13. **Desigualdade de participação:** municípios grandes podem esconder falhas em pequenos; erro deve ser estratificado por tamanho e reportado com métricas numéricas.
14. **Pressão editorial:** a pergunta do título pode induzir uma conclusão forte. O texto deverá mostrar também associações fracas, resultados nulos, limitações e casos que contrariem a hipótese.
15. **Escopo:** engenharia de dados, estatística, APIs, NLP e visualização podem transformar o projeto em cinco projetos. O piloto e o critério de parada são a defesa contra expansão sem entrega.

## Adiado

Nenhuma pergunta foi formalmente adiada. O que ainda não existe é implementação: o piloto deverá verificar cobertura, permissões, esquemas, chaves, janela temporal e disponibilidade real das fontes antes de prometer métricas sociais específicas. Se uma fonte falhar no portão, a decisão é retirar a métrica do núcleo ou publicá-la apenas como módulo condicional documentado; não é preencher a lacuna silenciosamente.

## Threads abertos

Não há decisões abertas do protocolo financeiro 2022. A prioridade corrente é executar e documentar esse protocolo; 2026, atenção/redes sociais, PJe e backtests são etapas posteriores, não bloqueios.
