# Direção visual

**Conceito: boletim de urna encontra placar de TV.** A página é um boletim, não um painel: uma coluna, números grandes como os do placar da apuração na televisão, rótulos e metadados em monoespaçada como no boletim de urna impresso. Sem cartões, sem sombras, sem barras de destaque. A hierarquia vem do tamanho do tipo, do espaço e de filetes de 1px.

**O que só este assunto tem.** O verde do botão CONFIRMA da urna é o acento da interface (botão principal, linha "esta noite" no gráfico, estado "em andamento"). O escuro é o grafite-esverdeado da tela da urna. Os números dos candidatos (13, 22) aparecem como na urna. Vermelho e azul são dos candidatos e de mais nada.

## Tipografia

- **Archivo** (variável, eixos `wdth` 62–125 e `wght` 400–900) para tudo proporcional. Números grandes em `wdth` 100, peso 800, tracking −0,03em. Título em `wdth` 112, peso 700. Corpo 16px/1,5, peso 400.
- **IBM Plex Mono** para o que é "do boletim": rótulos de seção, metadados, eyebrow, estado, chaves de dados. Caixa alta, 12px, tracking 0,12em.
- Escala: 12 · 14 · 16 · 18 · 26 · 36 · 44 · 64. Dígitos sempre tabulares.

## Cor (tokens em `docs/index.html`)

| token | claro | escuro | papel |
|---|---|---|---|
| `--bg` | #f2f3f1 | #0f1412 | papel frio / tela da urna |
| `--fg` | #15191a | #e9ece9 | tinta |
| `--muted` | #5f6764 | #9aa39f | rótulos, metadados |
| `--line` | #cdd3cf | #2b3430 | filetes |
| `--track` | #dfe3e0 | #222a26 | trilhos de barra |
| `--accent` | #0f7a4d | #2fae72 | verde CONFIRMA |
| `--warn` | #9a5200 | #e3a24a | avisos |
| `--lula` | #c62828 | #e25757 | Lula |
| `--flavio` | #1f5fbf | #5a8fe3 | Flávio |

Paleta de gráfico (lula, flávio, acento) validada com o validador da skill de dataviz nos dois fundos: banda de luminosidade, croma, separação para daltonismo (ΔE ≥ 20) e contraste ≥ 3:1. Texto de valores usa a cor do candidato só quando o número é dele; o resto fica em tinta e muted.

## Regras

- Uma coluna de 600px, gutter de 16px, `padding-block` no wrapper.
- Blocos separados por `h2` em mono e espaço, não por caixas. Linhas de lista separadas por filete superior.
- Barras: cantos retos, 2px de folga entre segmentos, tique central nos 50%.
- Gráfico: linhas de 2px, grade recessiva, texto em tokens de tinta, nunca na cor da série.
- Botão principal: acento com texto branco; demais, só contorno. Raio 2px.
- Movimento: só transição de cor nos números. `prefers-reduced-motion` respeitado.
- Escuro desenhado, não invertido: paleta própria, validada.
