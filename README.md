# Apuração 2026 · 2º turno

Página estática que lê os arquivos oficiais do Divulga/TSE direto do navegador e mostra, a cada 2 minutos:

- o placar Lula × Flávio em votos válidos, abstenção e brancos + nulos, contra o 2º turno de 2022 e o 1º turno de 2026;
- a **chance de vitória**: antes da urna, pelas pesquisas corrigidas pelo erro do 1º turno; durante a apuração, combinada com a régua;
- a **régua**: a margem final que a parcial sugere, descontada a ordem de chegada das seções medida no 2º turno de 2022;
- os **institutos**: a última onda de cada um e, ao vivo, a distância para a implícita da régua;
- SP, MG, RJ, BA e PE contra 2022 e contra o 1º turno;
- a abstenção por estado contra o próprio estado no 1º turno e em 2022;
- a curva da noite sobre as curvas esperadas para Lula +2, empate e Flávio +2.

Nada sai do navegador: o histórico de leituras fica em `localStorage`. `?demo=1` mostra a página cheia com dados fictícios (`&pst=20` muda a fatia, `&final=-1` o resultado hipotético). `?replay=2022` é o **ensaio**: percorre a apuração real do 2º turno de 2022 ponto a ponto (`&ms=200` acelera), com a chance vindo só da régua. Se o arquivo do TSE ficar 10 minutos sem mudar durante a apuração, o selo do topo avisa "TSE parado".

## Estrutura

- `docs/index.html` — a página, HTML e JS puros, sem build.
- `docs/referencia.js` — dados de referência que a página carrega; gerado, não editar à mão.
- `ferramentas/referencia.py` — gera `dados/*.json` e `docs/referencia.js` a partir das fontes primárias do TSE.
- `ferramentas/apuracao.py` — a mesma régua no terminal, com log em CSV e, em `--loop`, os arquivos brutos do TSE de cada leitura (nacional, 27 UFs e exterior) em `dados/noite/*.json.gz`, fora do git. É a matéria-prima para reconstruir a curva de 2026 por estado depois.
- `dados/` — referências em JSON (curva de 2022, urna de 2022 e do 1º turno por UF, abstenção) e `pesquisas_2t.json`, mantido à mão, com as pesquisas de 2º turno e o erro de cada instituto no 1º turno.

## Rodar

```bash
python3 -m http.server 8787 --directory docs     # http://localhost:8787
python3 ferramentas/apuracao.py --probe           # os arquivos do TSE existem?
python3 ferramentas/apuracao.py --loop 120        # domingo, das 17h em diante: lê e grava dados/log_2t_2026.csv
python3 ferramentas/referencia.py                 # refaz as referências (baixa ~5 MB do TSE)
```

Para refazer `dados/urna_2t_2022_uf.json` é preciso o `votacao_candidato_munzona_2022.zip` (580 MB) dos dados abertos do TSE: `python3 ferramentas/referencia.py --munzona caminho/do.zip`.

## Domingo 25/10, passo a passo

| hora | o quê |
|---|---|
| 16h50 | `python3 ferramentas/apuracao.py --probe` confirma que os três arquivos do TSE respondem. Abrir a página no celular e deixar "a cada 2 min" ligado. |
| 17h00 | `python3 ferramentas/apuracao.py --loop 120` num terminal que fique aberto a noite inteira. Cada leitura imprime a régua, grava uma linha em `dados/log_2t_2026.csv` e um `.json.gz` em `dados/noite/`. |
| 17h–18h | Até 15% das seções a página diz "cedo demais"; a chance quase não sai do prior. Em 2022, 20% foi às 17h49. |
| ~18h30 | Em 2022, 50% foi às 18h26 e a virada de Lula veio aos 66,8%, às 18h42. É a faixa em que a régua passa a valer mais que as pesquisas. |
| ~20h | Em 2022, 99% foi às 20h00. A chance deve estar perto de 0 ou 100. |
| depois | `and = f` no arquivo nacional fecha a totalização; a página marca "finalizada" e os institutos passam a mostrar o erro contra a urna. |

Se o TSE parar de responder: a página tenta de novo sozinha a cada 2 minutos e o logger segue tentando; o Divulga oficial (resultados.tse.jus.br) é a reserva. Se a página mostrar "TSE parado", é o arquivo que não avançou, não a página.

## Método

Margem final implícita = margem parcial − k × efeito, onde efeito é a diferença entre a margem parcial e a final de Lula na mesma fatia de seções no 2º turno de 2022 (fonte: histórico oficial de totalização do TSE). k = 1 supõe que a diferença entre regiões é a de 2022, como ocorreu no 1º turno de 2026, em que o país inteiro se moveu por igual; k = 0,5 supõe que ela se achatou pela metade. A leitura em texto segue regras fixadas antes da apuração: a partir de 15% das seções, implícita acima de +1 tende a Lula, abaixo de −1 tende a Flávio, entre as duas é empate técnico.

**Chance de vitória.** Prior: última onda de cada instituto com campo encerrado a partir da data de corte, margem Lula − Flávio entre os dois, corrigida por `fator_correcao` (0,5) × erro do mesmo instituto no 1º turno de 2026; centro = média das corrigidas; incerteza `sigma0` = 3,3 pontos (erro das finais de 2º turno Datafolha/Ibope-Ipec 2006–2022, cerca de 2,5, combinado com a dúvida sobre aplicar metade ou todo o erro do 1º turno). Atualização: a implícita da régua entra como observação com incerteza 0,3 × |efeito restante| + 0,15; a chance é a combinação das duas, cada uma pesada pelo inverso da variância. Aos 100% a chance é 0 ou 100. Parâmetros em `dados/pesquisas_2t.json`.

## Fontes

- Divulga/TSE, eleição 6258: `https://resultados.tse.jus.br/oficial/ele2026/6258/dados/<uf>/<uf>-c0001-e006258-u.json` e `br/br-e006258-ab.json`.
- Histórico de totalização do 2º turno de 2022, `detalhe_votacao_munzona_2022.zip` e `votacao_candidato_munzona_2022.zip`: [dados abertos do TSE](https://dadosabertos.tse.jus.br/dataset/resultados-2022).
- Resultado final do 1º turno de 2026: Divulga/TSE, eleição 6257.

Página independente, sem vínculo com o TSE, partidos ou campanhas.
