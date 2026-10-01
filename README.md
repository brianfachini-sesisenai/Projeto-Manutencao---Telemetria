# PredictaMaq — Manutenção Preditiva e Telemetria de Maquinário Crítico

Protótipo acadêmico (Equipe 2) do trabalho *Engenharia e Design de Interfaces Analíticas na Indústria 4.0*.
Aplicação web que simula o painel de um engenheiro de manutenção/confiabilidade monitorando **prensas hidráulicas,
compressores de parafuso e tornos CNC** a partir de telemetria de **vibração, temperatura e pressão**.

> Todos os dados são **fictícios** (gerados por simulação). A paleta azul é inspirada na identidade da WEG; o projeto não
> tem vínculo com a empresa.

## Como executar

```bash
pip install -r requirements.txt
python run.py            # http://localhost:8050
```

Na primeira execução os CSVs são gerados em `data/` (14 dias de histórico, 6 máquinas, 10 em 10 min).
Para regenerar do zero: `python -m predictive.datagen`. Testes: `pytest`.

Variáveis de ambiente: `PORT` (8050), `HOST` (127.0.0.1), `TICK_SECONDS` (2).

## Telas

Cada tela responde a **uma pergunta** e esconde o detalhe técnico em blocos recolhíveis.

| Rota | Pergunta que responde | Conteúdo |
|---|---|---|
| `/` | O que precisa da minha atenção agora? | Resumo do estado da planta, cartões "precisam de atenção" (com o motivo e a tendência) e lista compacta de todas as máquinas |
| `/monitoramento` | Como está esta máquina agora? | Três variáveis como abas-resumo; um gráfico em tempo real (WebSocket) com zonas de limite; simulador de falhas recolhido |
| `/analise` | Quando preciso agir? | Diagnóstico em linguagem natural, vida útil restante (RUL), tendência/anomalias, índice de saúde e comparação entre máquinas; ordem de serviço em um clique |
| `/alertas` | O que preciso tratar? | Alertas e ordens de serviço com a ação seguinte em cada linha (reconhecer, criar OS, iniciar, concluir); exportação CSV |
| `/sobre` | Como foi feito? | Princípios de design aplicados, diagnóstico crítico, tecnologias, arquitetura e medições reais |

O botão de contraste no canto superior direito alterna entre tema claro e escuro (preferência salva no navegador).

## Princípios de design aplicados

Hierarquia visual (um número dominante por tela), proximidade e região comum (cartões), similaridade (estado sempre como "chip"),
figura-fundo (zonas de limite translúcidas atrás da série), revelação progressiva (detalhes recolhidos) e cor acessível: estado = cor + forma +
texto, contraste de texto ≥ 4,5:1 e uma única cor de destaque nos gráficos. Detalhes em `/sobre`.

## Arquitetura

```
simulador (thread) ──► CSV (histórico, live, alertas, OS)
        │
        └─► Flask-Sock  /ws  ──► navegador (assets/live.js) ──► dcc.Store ──► callbacks Dash/Plotly
API REST: /api/sensors  /api/history?machine=PR-01  /api/snapshot  /api/health
```

* `predictive/config.py` — máquinas, variáveis e limites operacionais
* `predictive/simulator_model.py`, `datagen.py` — modelo de carga/desgaste/falhas e geração do histórico
* `predictive/analytics.py` — severidade, índice de saúde, anomalias, RUL, detector de alertas
* `predictive/stream.py` — simulador em tempo real, hub WebSocket e API REST
* `predictive/store.py` — persistência em CSV
* `predictive/figs.py`, `ui.py`, `pages.py`, `insights.py`, `app.py`, `diagnostic.py` + `assets/` (CSS e cliente WebSocket) — interface

## Limitações (assumidas)

Dados simulados; limites ilustrativos (não são de norma/fabricante); RUL por regressão linear é didático; CSV como
banco não escala; estado do simulador em memória de um único processo. Detalhes na página `/sobre`.
