# Estudo: como apresentar uma apuração ao vivo

Feito em 21/10/2026, antes do 2º turno. Referências olhadas no celular: g1 (apuração de 2022), Bloomberg (2024), e os textos do Reuters Institute sobre a "agulha" do New York Times, o estudo de Cai e Kay (CHI 2024) sobre o vocabulário visual das páginas de resultado, e a auditoria de acessibilidade de Sarah Fossheim sobre os painéis de 2024.

## O que as melhores páginas fazem

1. **Uma frase em português claro acima de tudo.** O g1 abre com "Lula (PT) é eleito presidente com 50,90% dos votos". O NYT diz que páginas de resultado "são painéis de dados sem contexto" e que o trabalho é "segurar a mão do leitor". A leitura pré-comprometida da régua já existia na página, mas estava escondida nos detalhes.
2. **O tempo da noite é uma barra.** O g1 põe a fatia de seções apuradas como uma linha verde sob o título; a NRK usa uma barra de progresso fixa. É o único elemento "de progresso" que a página precisa.
3. **Expectativa, não só placar.** A agulha do NYT parte de uma expectativa pré-eleitoral e migra para uma estimativa modelada conforme os votos chegam, porque "os primeiros votos contados costumam diferir muito dos que faltam". É exatamente o que a régua faz. Mostrar a margem final esperada com a sua incerteza, e não só a chance, é a forma honesta de mostrar isso.
4. **Dizer o que vem a seguir.** O NYT avisa "que dados esperamos de cada estado e em que ordem". Aqui, o equivalente é o próximo marco da noite com a hora em que ele chegou em 2022.
5. **Limiares explícitos para mostrar informação** (Cai e Kay): nada aparece antes de ter base. Aqui: nacional a partir de 15% das seções, estado a partir de 30% das suas seções, votos dos eliminados a partir de 90%.
6. **Acessibilidade** (Fossheim): sem cabeçalho fixo que engole a tela com zoom; cor nunca sozinha, sempre com texto; interação por teclado; mudanças anunciadas para leitor de tela.

## O que mudou na página por causa disto

- A frase de leitura ("Flávio tende a vencer", "empate técnico pela régua") subiu para debaixo da chance.
- O título ganhou a barra de seções apuradas como sublinhado.
- Entrou a **margem final esperada** com faixa de incerteza, num eixo de −8 a +8, abaixo da chance.
- Entrou o **próximo marco** da noite com a hora de 2022.
- A chance e o estado da apuração são anunciados a leitores de tela (`aria-live`).
- Monoespaçada só em rótulos, estado e metadados; as linhas secundárias das listas voltaram ao tipo de texto.

## Bibliotecas de componentes

Decisão: **nenhuma**. A página tem seis componentes (placar, barra, faixa de margem, lista com filete, painel de ajuda, gráfico de linha). O painel é `<dialog>` nativo; o gráfico é SVG de 40 linhas; o resto é tipografia. Uma biblioteca (shadcn, Radix, Shoelace, Pico) traria mais peso que ganho e empurraria o visual para o genérico que se quis evitar. O que vale manter como "sistema" é o `DESIGN.md`: tokens, escala de tipo e regras. Se um dia a página virar um app com formulários e tabelas, a escolha certa seria uma biblioteca sem opinião visual, como Radix ou Web Awesome, por cima dos mesmos tokens.
