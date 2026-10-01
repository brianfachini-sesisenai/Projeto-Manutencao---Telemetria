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

| Rota | Conteúdo |
|---|---|
| `/` | KPIs da frota, cartões por máquina (estado, índice de saúde, valores, sparkline), mapa de severidade |
| `/telemetria` | Séries em tempo real (WebSocket) com zonas de atenção/crítico + **simulador de falhas** para demonstrar alertas |
| `/preditiva` | Índice de saúde, anomalias (z-score robusto), tendência e **RUL** por regressão linear, boxplot e correlação |
| `/alertas` | Alertas e ordens de serviço (reconhecer, resolver, gerar OS, criar OS manual, exportar CSV) |
| `/diagnostico` | Fundamentos de UX aplicados, medições reais do protótipo, diagnóstico crítico e comparativo de tecnologias |

O botão **Alternar tema** muda entre claro e escuro (preferência salva no navegador).

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
* `predictive/figs.py`, `pages.py`, `app.py`, `diagnostic.py` — interface

## Limitações (assumidas)

Dados simulados; limites ilustrativos (não são de norma/fabricante); RUL por regressão linear é didático; CSV como
banco não escala; estado do simulador em memória de um único processo. Detalhes na página `/diagnostico`.
