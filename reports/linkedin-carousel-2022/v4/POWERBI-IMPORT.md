# Carrossel TSE 2022 — versão 4

**Estado:** 8 lâminas, 1080 × 1350 px (4:5), em `reports/linkedin-carousel-2022/v4/`. Esta é a única versão mantida do carrossel.

## Ordem do carrossel

1. `slide-01-capa.svg/png` — Bilhões em campanhas. Quem chegou à Câmara?
2. `slide-02-partidos.svg/png` — Quais partidos declararam mais despesas?
3. `slide-03-mapa-uf.svg/png` — Quanto declararam gastar os eleitos em cada estado?
4. `slide-04-faixas-eleicao.svg/png` — Quanto declararam gastar os candidatos que se elegeram?
5. `slide-05-scatter-rj.svg/png` — Despesas e participação nos votos válidos por UF.
6. `slide-06-sexo.svg/png` — Despesas medianas próximas; proporções diferentes.
7. `slide-07-raca-cor.svg/png` — Receitas e eleição por raça/cor.
8. `slide-08-conclusoes.svg/png` — O que os dados mostram.

## Medidas, recortes e denominadores

- Nenhuma ingestão ou modelo foi executado. Foram reutilizados os artefatos existentes; a mudança é de apresentação.
- Capa: totais existentes para 9.204 candidaturas; partidos e scatter: recorte eleitoral N=9.202; mapa, faixas e grupos usam os recortes APTO/Final e coberturas indicados abaixo. Esses denominadores não são intercambiáveis.
- Receitas financeiras são valores recebidos; despesas contratadas são gastos declarados; pagamentos realizados são uma medida distinta e não entram nos totais deste carrossel.
- Partidos: barras com os sete maiores totais de despesas contratadas dos candidatos filiados, não dos diretórios. Todos os partidos, candidatos, votos e eleitos estão no CSV de apoio; total maior ou menor não mede eficiência.
- Mapa: mediana de despesas declaradas Final entre eleitos APTO; 510/512 têm despesa observada. As duas ausências permanecem ausentes, nunca zero. Demais UFs: `apoio/medianas-demais-estados.svg`, `png/apoio/medianas-demais-estados.png` e `../data/despesas-eleitos-por-uf.csv`.
- Faixas: distribuição entre 510 eleitos; 82,4% estavam acima de R$ 1 milhão. Entre 987 candidaturas acima de R$ 1 milhão, 42,55% se elegeram e 57,45% não. Os denominadores são distintos.
- Scatter principal: Brasil, uma candidatura por ponto (N=9.202). X = despesa contratada declarada, de R$ 0 a R$ 3,5 milhões; Y = votos nominais válidos da candidatura ÷ votos válidos oficiais da UF, incluindo votos de legenda. Eixos lineares; extremos observados (R$ 3,42 milhões e 14,60%) dentro da visão geral, sem pontos omitidos.
- Sexo: proporção eleita = eleitos/candidaturas do grupo (homens 420/5.936; mulheres 90/3.266). Medianas de despesas contratadas: R$ 65,0 mil e R$ 65,6 mil. Mediana divide o grupo ao meio; não significa valores iguais para cada candidatura.
- Raça/cor: “negras” = autodeclaradas pretas ou pardas. Medianas de receitas financeiras (R$ 100 mil brancas; R$ 53 mil pretas+pardas) usam apenas candidaturas com receita observada: 4.557/4.681 e 4.170/4.381. Proporções eleitas (7,75%; 3,17%) usam todas as candidaturas de cada grupo: 363/4.681 e 139/4.381. Categorias originais, contagens e cobertura permanecem no CSV; o agregado pretas+pardas não deve ser somado de novo às categorias.
- Dado de apoio, fora do carrossel: mediana das razões individuais (despesa contratada deduplicada ÷ votos nominais positivos): R$ 17,79 entre eleitos e R$ 46,75 entre não eleitos. A mediana menor entre eleitos ocorre em boa parte porque eles têm muito mais votos. Não é preço do voto, custo público ou razão agregada; 104 candidaturas sem voto positivo não entram no cálculo.
- As comparações são descritivas; não identificam as causas dos resultados.

## Dados e gráficos de apoio

- `../data/despesas-eleitos-por-uf.csv` — medianas e cobertura das 27 UFs.
- `../data/distribuicao-eleitos-faixa.csv`, `../data/proporcao-eleita-por-faixa.csv` e `../data/contraponto-acima-1m.csv` — contagens, taxas e denominadores por faixa.
- `../data/partidos-recorte-eleitoral.csv` — candidatos, despesas contratadas, votos válidos e eleitos por partido.
- `sexo-resultados.csv` — contagens, denominadores, percentuais e medianas por sexo.
- `../data/raca-receitas-financeiras.csv` — categorias originais, pretas+pardas e coberturas.
- `../data/scatter-candidatos-quatro-ufs.csv` — observações por candidatura em SP, MG, RJ e BA.
- `apoio/scatter-sp-mg.svg`, `apoio/scatter-rj-ba.svg` e `png/apoio/*.png` — scatterplots complementares, fora da sequência principal.
- `../../tse-2022-election-expense-comparison.csv`, `apoio/custo-por-voto.svg` e `png/apoio/custo-por-voto.png` — fonte tabular e visualização mantidas como apoio, fora do carrossel.
- `../data/origem-receitas-financeiras.csv` — totais existentes de receitas financeiras.
- `carrossel-final.pdf` — oito lâminas em ordem narrativa.

## Fontes e reprodução

- [TSE — prestações de contas de candidatos 2022](https://cdn.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2022.zip)
- [TSE — votação nominal 2022](https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_2022.zip)
- [IBGE — malhas 2022](https://servicodados.ibge.gov.br/api/docs/malhas?versao=3)
- [Repositório e reprodução](https://github.com/dargmiguel/dinheiro-compra-votos)

Renderizar todas as lâminas: `python reports/render-linkedin-carousel-2022-final.py`; selecionar por número ou nome: `--slides 1,party,map,bands,scatter-rj,sex,race,conclusions`. O script atualiza os SVGs e as notas em `v4/`; o PDF e as prévias existentes também estão versionados nessa pasta.
