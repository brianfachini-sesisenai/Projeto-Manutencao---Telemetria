# Roteiro do relatório técnico (mapeado à rubrica do professor)

Sugestão de estrutura; cada seção aponta onde o protótipo evidencia o ponto. **As referências abaixo são sugestões de
partida: confirmem edição/ano e leiam as fontes antes de citá-las.**

## 1. Fundamentação teórica (tema geral — todas as equipes)
* **Fundamentos de UX para dados** (Design e Usabilidade, 20%): leis da Gestalt, hierarquia visual, contraste, paletas
  acessíveis, carga cognitiva, heurísticas de Nielsen. Evidência: tabela em `/diagnostico`, estados com cor+forma+texto,
  tema claro/escuro. Sugestões: Stephen Few, *Information Dashboard Design*; Edward Tufte, *The Visual Display of
  Quantitative Information*; Nielsen, *10 Usability Heuristics*; WCAG 2.x (contraste e uso de cor).
* **Frameworks de código** (Programação e Frameworks, 30%): Dash/Plotly (usado) vs. D3.js, Chart.js, Streamlit, Matplotlib/
  Seaborn. Evidência: comparativo em `/diagnostico`; callbacks em `predictive/app.py`, figuras em `predictive/figs.py`.
* **Integração web** (20%): HTML5/CSS/JS, REST e WebSocket (RFC 6455) vs. polling. Evidência: `/ws`, `/api/*`,
  `assets/live.js`, layout responsivo, medição do pacote por tick (1 KB) vs. snapshot completo (28 KB).
* **Ferramentas de BI**: Power BI e Tableau — quando preferir BI de mercado e quando código próprio. Sugestão de
  contraponto prático: carregar `data/telemetry_history.csv` no Power BI e comparar esforço/resultado.

## 2. Tema da equipe: manutenção preditiva e telemetria
* Conceitos: manutenção corretiva/preventiva/preditiva, condition monitoring, RUL, índice de saúde, limites de severidade.
  Sugestões: ISO 20816 (vibração em máquinas), ISO 17359 (monitoramento de condição), ISO 13374 (processamento de dados).
* Dados: 3 variáveis × 6 máquinas; modelo do simulador (carga diária, desgaste progressivo, incidentes, falhas injetáveis).
* Público-alvo: engenheiros de manutenção e confiabilidade — requisitos: ver estado de relance, alertas acionáveis, tendência.

## 3. Diagnóstico crítico (exigido no PDF)
Usar a página `/diagnostico`: falhas de usabilidade, gargalos de performance (com as medições), oportunidades de melhoria.
Sugestão: registrar *antes/depois* de uma melhoria (ex.: downsampling ou `extendData`) com tempos medidos.

## 4. Demonstração (15 min) — roteiro sugerido
1. Visão geral: cartões, mapa de severidade (1 min).
2. Telemetria: explicar zonas e o indicador de tempo real (2 min).
3. **Injetar falha de rolamento** na PR-01 → mostrar o alerta chegando pelo ticker (2 min).
4. Alertas: reconhecer, gerar OS, ver `data/work_orders.csv` mudar (2 min).
5. Preditiva: PR-02 com RUL de poucos dias; explicar R² e limites do modelo (3 min).
6. Diagnóstico/argumentação: UX, stack, limitações, melhorias (5 min).

## 5. Perguntas prováveis na arguição
* Por que CSV e não banco de dados? (escopo; limites listados no diagnóstico)
* Como validariam o RUL? (dados reais de falha, métricas como erro absoluto médio; hoje é didático)
* Por que WebSocket e não polling? (menor payload e latência; ver medição)
* Como o design ajuda quem tem daltonismo? (forma+texto além da cor)
