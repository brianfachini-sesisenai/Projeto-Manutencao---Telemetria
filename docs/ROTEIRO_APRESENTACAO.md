# Roteiro da apresentação — PredictaMaq

Formato do trabalho: **15 min de demonstração + 10 min de arguição**. Este roteiro é para uma apresentação *por cima*: o que o sistema faz,
por que foi feito assim e como se explica em palavras simples. Os termos técnicos estão no glossário no fim.

## Antes de começar (10 min antes)

1. Abra o terminal na pasta do projeto e rode `python run.py`. Abra `http://localhost:8050`.
2. Confira o canto superior direito: deve aparecer **"Tempo real"** com a bolinha verde.
3. Deixe o tema **claro** (você mostra o escuro durante a apresentação).
4. Plano B: se algo falhar, use as imagens em `docs/relatorio/figuras/` (são as telas do sistema).
5. Ao terminar de ensaiar, volte tudo ao normal: botão **"Normalizar tudo"** (na tela Monitoramento) ou reinicie com `python -m predictive.datagen` e `python run.py`.

## A ideia central em uma frase

> "Criamos um painel que mostra, em tempo real, a saúde de máquinas críticas da fábrica, avisa quando algo sai do normal e
> estima **em quantos dias** uma máquina pode chegar a um estado crítico, para a equipe de manutenção agir **antes** de quebrar."

## Como descrever o sistema (ERP?)

O PredictaMaq **não é um ERP**. Um ERP integra a empresa toda (finanças, compras, estoque, RH, produção). O que fizemos é um **painel de monitoramento de condição**
com um módulo simples de **manutenção** (alertas e ordens de serviço), parecido com o módulo de manutenção de um ERP ou de um sistema de gestão de manutenção (CMMS).
Frase segura para a apresentação:

> "O PredictaMaq é um painel de monitoramento e manutenção preditiva, **inspirado no módulo de manutenção de sistemas de gestão como os ERPs**: ele tem
> alertas e ordens de serviço, mas o foco é monitorar as máquinas e prever falhas."

Evite dizer "é um ERP" ou "simula um ERP completo": se perguntarem, o professor pode notar que faltam os outros módulos.

## Roteiro (15 minutos)

### 1. Abertura — 0:00 a 1:30 (sem mexer no site ainda)
**O que dizer**
- "Máquinas como prensas e compressores são críticas: se uma para sem aviso, a produção para."
- "Existem três jeitos de fazer manutenção: **corretiva** (consertar depois que quebra), **preventiva** (trocar peças por calendário) e **preditiva**
  (olhar os dados dos sensores e agir quando os sinais mostram que vai falhar)."
- "Nosso tema é manutenção preditiva e telemetria. Telemetria é medir à distância: sensores mandam vibração, temperatura e pressão."
- "O público do painel são os engenheiros de manutenção. Os dados são **fictícios**, gerados por uma simulação."

### 2. Visão geral — 1:30 a 3:30 (tela inicial)
**O que mostrar:** o título grande, os cartões "Precisam de atenção" e a lista de máquinas.
**O que dizer**
- "Cada tela responde **uma pergunta**. Esta responde: *o que precisa da minha atenção agora?*"
- "A frase grande resume a situação. Abaixo, só as máquinas com problema, dizendo o **motivo** e a **tendência**, e não só números."
- "O estado nunca depende só da cor: tem **cor, forma e texto** (círculo = normal, triângulo = atenção, quadrado = crítico). Assim funciona
  também para quem tem daltonismo."
- Ponte com a teoria: "Isso é **hierarquia visual** (o mais importante é o maior) e **proximidade** (o que é da mesma máquina fica junto)."

### 3. Monitoramento — 3:30 a 5:30 (menu "Monitoramento")
**O que mostrar:** escolher uma máquina (PR-02), clicar nas três abas (vibração, temperatura, pressão), mostrar as faixas amarela e vermelha.
**O que dizer**
- "Aqui vemos uma máquina em **tempo real**. Cada aba é uma variável: vibração, temperatura e pressão."
- "A faixa **amarela** é atenção; a **vermelha**, crítico. Quando a linha entra numa faixa, o estado muda."
- "Mostramos **uma variável por vez** de propósito, para não sobrecarregar quem olha (carga cognitiva)."
- "O indicador 'Tempo real' mostra que o servidor está **empurrando** os dados para a tela (tecnologia WebSocket), sem precisar recarregar a página."
- Clique no botão de tema e mostre o **modo escuro** (dois segundos). "Também funciona no celular."

### 4. Demonstração de falha — 5:30 a 7:30 (ainda em Monitoramento)
**Passos**
1. Escolha **PR-01**. Abra "Modo demonstração: simular uma falha".
2. Tipo de falha: **Falha de rolamento**. Clique **Injetar falha**.
3. Enquanto espera (~25–30 s), explique: "Estamos simulando um rolamento desgastando: a vibração começa a subir."
4. Aparece a **notificação** no canto da tela e a linha entra na faixa vermelha. "O sistema só abre alerta depois de 3 leituras seguidas fora do limite,
   para não disparar por um ruído isolado."
5. Vá em **Visão geral**: o título agora diz **"1 máquina em estado crítico"**.

### 5. Alertas e ordens de serviço — 7:30 a 9:30 (menu "Alertas")
**O que mostrar:** o alerta da PR-01 → **Reconhecer** → **Criar OS** → aba "Ordens de serviço" → **Iniciar**.
**O que dizer**
- "Aqui está o fluxo de uma equipe de manutenção: **alerta → reconhecimento → ordem de serviço → conclusão**."
- "Cada linha mostra a **próxima ação**, para o usuário não precisar procurar botões."
- "Tudo é salvo em arquivos **CSV**, que é o nosso 'banco de dados' (podemos abrir `data/work_orders.csv` para mostrar a ordem criada)."

### 6. Análise preditiva — 9:30 a 12:00 (menu "Análise preditiva")
**O que mostrar:** PR-02, o número grande de dias, o gráfico com a linha pontilhada e o quadrado vermelho.
**O que dizer**
- "Esta tela responde: *quando preciso agir?*"
- "A PR-02 vem aumentando a vibração de forma constante. Traçamos uma **reta de tendência** e vemos onde ela cruza o limite crítico: cerca de
  **5 dias**. Esse número é a **vida útil restante** (RUL)."
- "Abaixo mostramos a **confiança**: quando os dados oscilam muito, o sistema avisa que a estimativa é fraca."
- "Com um clique geramos a **ordem de serviço** preditiva."
- Seja honesto: "É um modelo simples (uma reta); em uma fábrica real seria validado com dados de falhas reais."

### 7. Tecnologia e conclusão — 12:00 a 15:00 (menu "Sobre" ou slide)
**O que dizer**
- "Usamos **Python com Dash/Plotly**, que é a stack recomendada na proposta: tudo em Python, com gráficos interativos."
- "Comparamos com D3.js, Chart.js, Streamlit e Power BI. Escolhemos Dash porque junta análise de dados e interface num só lugar."
- "Fizemos uma **primeira versão** com muita informação na tela, avaliamos criticamente e **redesenhamos**: uma pergunta por tela, detalhes escondidos,
  contraste calculado."
- Limitações (mostra maturidade): "dados simulados; CSV não escala; o modelo de previsão é simples; não testamos com usuários reais."
- Próximos passos: "banco de séries temporais, sensores reais, modelos mais avançados."
- Fechamento: "O objetivo foi mostrar como **design, dados e tecnologia** juntos ajudam a decidir antes da falha."

## Sugestão de divisão entre os integrantes
- **Pessoa 1:** Abertura + Visão geral (contexto e design).
- **Pessoa 2:** Monitoramento + demonstração de falha.
- **Pessoa 3:** Alertas + Análise preditiva.
- **Pessoa 4/5:** Tecnologia, limitações e conclusão.

## Glossário em palavras simples

| Termo | Explicação |
|---|---|
| **Telemetria** | Medir à distância. Sensores nas máquinas enviam números continuamente. |
| **Manutenção preditiva** | Usar os dados para prever quando algo vai falhar e agir antes. |
| **Vibração** | Quanto a máquina "treme". Subir demais pode indicar rolamento ou peça desgastada. |
| **Temperatura** | Calor da máquina. Subir pode indicar atrito, falta de lubrificação ou resfriamento ruim. |
| **Pressão** | Força do óleo ou do ar. Cair pode indicar vazamento; subir demais, risco. |
| **Limite de atenção / crítico** | Valores a partir dos quais o estado vira amarelo / vermelho. **Os nossos são fictícios** (didáticos). |
| **Índice de saúde (0–100)** | Nota que resume o quanto a máquina está perto dos limites. Quanto menor, pior. |
| **RUL (vida útil restante)** | Estimativa de quantos dias faltam para chegar ao limite crítico se a tendência continuar. |
| **Anomalia** | Ponto que foge muito do comportamento recente. |
| **Dash / Plotly** | Dash cria a página web em Python; Plotly desenha os gráficos interativos. |
| **Flask** | Servidor web por baixo do Dash. |
| **WebSocket** | Conexão aberta entre navegador e servidor: o servidor **empurra** dados novos, sem a página precisar perguntar toda hora. |
| **API REST** | Endereços que devolvem dados em formato padrão (ex.: `/api/sensors`) para outros sistemas usarem. |
| **CSV** | Arquivo de tabela em texto. Aqui faz o papel de banco de dados. |
| **Gestalt** | Leis de como o olho agrupa elementos (proximidade, similaridade, continuidade, figura-fundo). |
| **Hierarquia visual** | O mais importante aparece maior/mais destacado. |
| **Carga cognitiva** | Esforço mental para entender a tela. Menos informação por vez reduz o esforço. |
| **Revelação progressiva** | Mostrar o essencial e deixar detalhes para quem quiser (blocos recolhidos). |

## Perguntas prováveis e respostas curtas

- **Os dados são reais?** Não. São gerados por uma simulação (carga diária, desgaste e falhas). Os limites também são fictícios.
- **Por que CSV e não um banco de dados?** Para o escopo do trabalho e para a demonstração ficar simples. Reconhecemos que não escala; o ideal seria um banco de séries temporais.
- **Como funciona o tempo real?** O servidor gera uma leitura a cada 2 segundos e a envia por WebSocket. A tela é atualizada quando recebe o aviso.
- **Como a vida útil restante é calculada?** Ajustamos uma reta aos últimos 5 dias de dados e vemos quando ela cruzaria o limite crítico. É simples e didático.
- **Isso funcionaria em uma fábrica real?** A ideia sim; a implementação precisaria de sensores reais, banco adequado, autenticação e validação dos modelos.
- **Por que Dash e não D3 ou Power BI?** Dash une Python, análise e gráficos interativos em um só lugar e é a stack indicada na proposta. D3 dá mais controle visual, mas exige muito mais código; Power BI é ótimo para BI corporativo, mas tem menos flexibilidade em tempo real.
- **Como aplicaram os princípios de design?** Uma pergunta por tela, o mais importante em destaque, estado por cor+forma+texto, detalhes recolhidos e contraste calculado.
- **Testaram com usuários?** Não; a avaliação foi feita pela equipe. É uma limitação que listamos.
- **O que mudariam?** Banco de dados real, atualização dos gráficos só com o ponto novo, modelos de previsão melhores e limites configuráveis.

## Dica: tooltips
Passe o mouse sobre os ícones **ⓘ** (Saúde, Vibração, Temperatura, Pressão, "Até o limite crítico", Confiança) para mostrar a explicação na hora; é um bom momento para falar de **carga cognitiva** e **ajuda contextual**.

## Dicas rápidas
- Fale **do problema do usuário** antes da tecnologia.
- Não tente explicar fórmulas; use a imagem da reta cruzando o limite.
- Se algo não aparecer na hora, continue falando e recarregue a página (F5); o indicador "Tempo real" confirma a conexão.
- Admitir limitações com naturalidade conta pontos na rubrica de postura crítica.
