# Roteiro dos slides 6, 7 e 8 (e a ponte para o site)

Tempo sugerido: **slide 6 (~1 min) + slide 7 (~2 min) + slide 8 (~1,5 min)**, depois a passagem para a demonstração (slides 9 e 11).
Os textos abaixo são falas de exemplo: use as suas palavras e leia só os tópicos em **negrito**, se preferir.

---

## Slide 6 — Diferenças UI x UX (a imagem da mostarda Heinz)

**Em uma frase:** UI é *como parece*; UX é *como é usar*.

**O que dizer**
- "**UI** (*User Interface*) é a interface: o visual, as cores, os botões, o layout. É o que a pessoa **vê**."
- "**UX** (*User Experience*) é a experiência completa: o quanto é **fácil, rápido e agradável** conseguir o que se quer."
- Explique a imagem: "Os dois frascos são da mesma marca e têm o mesmo rótulo, ou seja, a mesma 'cara'. A diferença está em **usar**: na garrafa de vidro
  é difícil tirar o final do produto; no frasco de apertar, o conteúdo sai fácil e vai até o fim. **A aparência é parecida, a experiência é diferente.**"
- Ligação com o nosso projeto: "A primeira versão do nosso site tinha uma aparência boa, mas muita informação na tela e o usuário ficava perdido. Na segunda
  versão mantivemos o visual e **mudamos a experiência**: uma pergunta por tela, o mais importante em destaque."

**Frase de transição:** "E para melhorar a experiência existem princípios de design; os principais estão no slide anterior." (ou ligue ao slide 7 com "agora, como isso chega ao navegador?")

**Se perguntarem:** "UI e UX são a mesma coisa?" → "Não. UI é uma parte da UX. Dá para ter uma interface bonita com uma experiência ruim, como no exemplo da garrafa."

---

## Slide 7 — Integração web (Plotly, Chart.js, D3.js)

**Em uma frase:** integração web é colocar gráficos e dashboards **dentro de uma página que abre no navegador**, recebendo dados.

**Conceitos em palavras simples**
- **Integrar na web:** a tela é feita com **HTML5** (a estrutura), **CSS** (a aparência) e **JavaScript** (o comportamento). Os gráficos e os dados precisam "conversar" com essa página.
- **Biblioteca x framework:** biblioteca é um **conjunto de ferramentas** que você chama (ex.: Plotly desenha gráficos); framework é a **estrutura** que organiza o aplicativo inteiro (ex.: Dash, do slide 4).
- **Tempo real:** o servidor pode **empurrar** dados para a tela (WebSocket), em vez de a tela perguntar toda hora.

**O que dizer**
- "Aqui estão três bibliotecas de gráficos para a web:"
  - "**Plotly**: gráficos interativos prontos, em Python, R ou JavaScript. É a que **usamos**, por meio do Dash. É como um **kit pronto**: monta rápido."
  - "**Chart.js**: biblioteca JavaScript **leve**, que desenha gráficos padrão na página usando o elemento HTML5 chamado *canvas*. Boa para gráficos simples em sites."
  - "**D3.js**: JavaScript com **controle total** do visual. É como ter as **peças soltas**: dá para criar qualquer visualização, mas exige bem mais código."
- Aponte a captura do site à direita: "Isto é o resultado: uma **página web** com o painel funcionando. No nosso caso, o servidor envia as leituras dos sensores por **WebSocket** e o painel se atualiza sozinho."
- Se quiser acrescentar algo que **não está no slide** (sugestão): "O sistema também oferece uma **API** com os dados em formato padrão, para outros sistemas consultarem."

**Se perguntarem**
- *"Por que Plotly e não D3?"* → "Plotly entrega gráficos interativos com pouco código e se integra ao Python, que usamos para analisar os dados. D3 daria mais controle visual, mas levaria muito mais tempo."
- *"O que é WebSocket?"* → "Uma conexão que fica aberta entre o navegador e o servidor, e o servidor manda dados novos assim que existem."
- *"O site funciona no celular?"* → "Sim, o layout se adapta a telas pequenas."

---

## Slide 8 — Ferramentas de BI (Power BI, Tableau, Looker Studio, Qlik Sense, Domo)

**Em uma frase:** BI são ferramentas **prontas** para transformar dados em painéis e relatórios que ajudam a decidir.

**Conceitos em palavras simples**
- **BI (*Business Intelligence*):** reunir dados de várias fontes, organizá-los, analisá-los e mostrá-los em painéis para apoiar decisões (como diz o slide).
- Diferença para o que fizemos: BI = ferramenta **pronta**, com pouco ou nenhum código; o nosso painel = **feito sob medida** em código.

**O que dizer (de forma geral, sem se aprofundar)**
- "**Power BI**, da Microsoft, é muito usado nas empresas e integra bem com Excel e outros produtos da Microsoft."
- "**Tableau** é conhecido pela flexibilidade para criar visualizações."
- "**Looker Studio**, do Google, é uma opção gratuita e simples de compartilhar."
- "**Qlik Sense** e **Domo** são plataformas corporativas para integrar dados e criar painéis, o Domo em nuvem."
- "O que elas têm em comum: **conectam várias fontes de dados** (planilhas, bancos) e permitem criar painéis **arrastando e soltando**, sem programar muito."
- Posicione o nosso projeto: "Para este trabalho, escolhemos **código** (Python/Dash) porque queríamos **dados em tempo real** e controle total do design. Em geral, ferramentas de BI são excelentes para relatórios gerenciais, mas têm mais limitações para tempo real e para personalizar a interface."
- Seja honesto: "Nós **comparamos na teoria**; não construímos o mesmo painel em Power BI. Os arquivos CSV do projeto poderiam ser carregados nessas ferramentas."

**Se perguntarem**
- *"Qual é melhor?"* → "Depende do objetivo. Para relatórios corporativos e rapidez, uma ferramenta de BI. Para um painel em tempo real e personalizado, código."
- *"Vocês usaram alguma delas?"* → "Não nesta aplicação; fizemos a comparação teórica."

---

## Ponte para a demonstração (slides 9 e 11)

> "Agora vamos ver tudo isso funcionando: um painel de monitoramento de máquinas com dados simulados."

- O slide **9** é só o título "demonstração prática"; o slide **11** é a imagem do site. Quando chegar nele, **abra o site ao vivo** e siga o roteiro de `docs/ROTEIRO_APRESENTACAO.md` (visão geral → monitoramento → falha simulada → alertas → análise).
- Se o site não abrir, use as capturas em `docs/relatorio/figuras/`.

---

## Ajustes recomendados no slide (antes de apresentar)

| Prioridade | Slide | Ajuste |
|---|---|---|
| **Alta** | 10 | É um modelo não editado ("DASHBOARD", texto "HHYRT" e gráfico de barras "Grupo A–D"). **Remova** ou troque por capturas reais do site (`docs/relatorio/figuras/`). |
| **Alta** | 12 | Corrija "Acesso em: 1 out. **202**" para **2026** (referência da Iberdrola). Os slides 4 a 8 não têm fontes; para o "levantamento bibliográfico e documental" pedido, acrescente referências de UX, Dash/Plotly e BI. |
| Média | 4 | Diga qual framework **vocês usaram** (Dash) e por quê, em uma linha. Há também um grande espaço vazio entre os dois cartões. |
| Média | (novo) | Um slide curto de **decisões e limitações** (a proposta pede reflexão crítica na arguição): dados simulados, CSV como banco, modelo de previsão simples, não testado com usuários. |
| Baixa | 2, 3 | O texto justificado cria espaços grandes entre palavras; alinhar à esquerda melhora a leitura. |
| Baixa | 6 | Se a imagem veio de terceiros, indique a fonte. |
