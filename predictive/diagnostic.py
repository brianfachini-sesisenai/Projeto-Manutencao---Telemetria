"""Página 'Diagnóstico e metodologia': conteúdo para o relatório, com medições reais do protótipo."""
from __future__ import annotations

import json
import time

import pandas as pd
from dash import html

from . import store
from .analytics import enrich
from .config import HISTORY_FILE, LIVE_FILE, MACHINES, TICK_SECONDS
from .figs import fmt, telemetry_fig


def _li(items):
    return html.Ul([html.Li(i) for i in items])


def measurements(sim) -> dict:
    t0 = time.perf_counter()
    df = pd.read_csv(HISTORY_FILE, parse_dates=["timestamp"])
    t_csv = (time.perf_counter() - t0) * 1000
    t0 = time.perf_counter()
    enrich(df)
    t_enrich = (time.perf_counter() - t0) * 1000
    snap = sim.snapshot()
    m = MACHINES[0]["machine_id"]
    t0 = time.perf_counter()
    telemetry_fig(MACHINES[0], snap["machines"][m], "light")
    t_fig = (time.perf_counter() - t0) * 1000
    return {
        "rows": len(df), "kb": HISTORY_FILE.stat().st_size / 1024, "t_csv": t_csv, "t_enrich": t_enrich, "t_fig": t_fig,
        "tick_kb": sim.last_payload_bytes / 1024, "snap_kb": len(json.dumps(snap).encode()) / 1024,
        "live_rows": max(0, sum(1 for _ in open(LIVE_FILE)) - 1) if LIVE_FILE.exists() else 0,
        "live_kb": LIVE_FILE.stat().st_size / 1024 if LIVE_FILE.exists() else 0,
    }


def layout(sim):
    m = measurements(sim)
    ux = [
        ("Proximidade", "Cada máquina é um cartão; valores e estado ficam agrupados no mesmo bloco.", "Visão geral"),
        ("Similaridade", "Mesma cor/ordem para cada variável em todas as telas (vibração = azul, temperatura = laranja, pressão = verde-água).", "Telemetria"),
        ("Figura-fundo / contraste", "Faixas de atenção e crítico ao fundo; a série em primeiro plano; temas claro e escuro, com texto de alto contraste sobre o fundo.", "Gráficos"),
        ("Hierarquia visual", "KPIs grandes no topo, cartões no meio, detalhes e tabelas por último (leitura em 'F').", "Visão geral"),
        ("Carga cognitiva", "Máximo de 3 variáveis por máquina; zonas pré-calculadas em vez de o usuário comparar números com limites de cabeça.", "Todas"),
        ("Acessibilidade de cor", "Estado = cor + forma (● ▲ ■) + texto; os limites têm traço diferente (tracejado/pontilhado).", "Alertas"),
        ("Feedback e visibilidade do sistema", "Indicador de conexão (tempo real / reconectando) e ticker do último alerta.", "Cabeçalho"),
    ]
    return html.Div([
        html.Div([html.H1("Diagnóstico e metodologia", className="page-title"),
                  html.P("Material de apoio ao relatório: fundamentos aplicados, arquitetura, diagnóstico crítico do próprio protótipo e comparativos.", className="page-sub")], className="topbar"),

        html.Div([
            html.Div([html.H3("Medições do protótipo (ao vivo)"),
                      html.Div([
                          html.Table([
                              html.Tr([html.Th("Métrica"), html.Th("Valor")]),
                              html.Tr([html.Td("Histórico em CSV"), html.Td(f"{m['rows']:,} linhas · {fmt(m['kb'], 0)} KB".replace(",", "."))]),
                              html.Tr([html.Td("Leitura do CSV (pandas, sem cache)"), html.Td(f"{fmt(m['t_csv'], 0)} ms")]),
                              html.Tr([html.Td("Enriquecimento (status + índice de saúde)"), html.Td(f"{fmt(m['t_enrich'], 0)} ms")]),
                              html.Tr([html.Td("Montagem da figura de telemetria (3 painéis)"), html.Td(f"{fmt(m['t_fig'], 0)} ms")]),
                              html.Tr([html.Td(f"Pacote do WebSocket (1 tick / {TICK_SECONDS:g} s)"), html.Td(f"{fmt(m['tick_kb'], 1)} KB")]),
                              html.Tr([html.Td("Snapshot completo (se fosse polling)"), html.Td(f"{fmt(m['snap_kb'], 0)} KB")]),
                              html.Tr([html.Td("Telemetria ao vivo gravada nesta sessão"), html.Td(f"{m['live_rows']:,} linhas · {fmt(m['live_kb'], 0)} KB".replace(",", "."))]),
                          ]),
                      ], className="prose")], className="card"),
            html.Div([html.H3("Arquitetura"),
                      html.Div([
                          html.P([html.Span("Simulador", className="tag"), "gera leituras (modelo com carga, desgaste e falhas) →",
                                  html.Span("CSV", className="tag"), "histórico, alertas e OS →",
                                  html.Span("Flask + WebSocket", className="tag"), "empurra cada tick →",
                                  html.Span("Dash/Plotly", className="tag"), "renderiza os gráficos."]),
                          _li(["API REST de sensores: /api/sensors, /api/history, /api/snapshot, /api/health.",
                               "Alertas: detector com debounce (3 leituras) e histerese de liberação (8 leituras).",
                               "Persistência: CSV com lock de processo; histórico em cache por mtime."]),
                      ], className="prose")], className="card"),
        ], className="grid two"),

        html.Div([html.H2("Fundamentos de UX aplicados"),
                  html.Div(html.Table([html.Tr([html.Th("Princípio"), html.Th("Como foi aplicado"), html.Th("Onde")])] +
                                      [html.Tr([html.Td(a), html.Td(b), html.Td(c)]) for a, b, c in ux]), className="prose card")], className="section"),

        html.Div([html.H2("Diagnóstico crítico do protótipo"), html.Div([
            html.Div([html.H3("Falhas de usabilidade"), html.Div(_li([
                "Sem filtro de turno/linha: o engenheiro vê todas as máquinas, mesmo as que não são de sua responsabilidade.",
                "Limites são fixos no código; o usuário não consegue ajustá-los por máquina.",
                "Conceito de 'índice de saúde' exige explicação; faltam tooltips com a fórmula nos cartões.",
                "Tabelas de alerta não têm agrupamento (um mesmo evento pode gerar vários alertas de variáveis diferentes).",
                "Não há tratamento de fuso horário nem de múltiplos usuários/perfis.",
            ]), className="prose")], className="card"),
            html.Div([html.H3("Gargalos de performance"), html.Div(_li([
                f"Cada tick reconstrói as figuras no servidor ({fmt(m['t_fig'], 0)} ms por figura de telemetria): não escala para dezenas de máquinas/usuários.",
                f"CSV como banco: leitura completa custa {fmt(m['t_csv'], 0)} ms e escrita reescreve o arquivo inteiro (alertas/OS); não há concorrência real entre processos.",
                "Estado do simulador vive na memória de um único processo (não funciona com vários workers do servidor).",
                "Servidor de desenvolvimento do Flask: aceitável para a demonstração, não para produção.",
            ]), className="prose")], className="card"),
            html.Div([html.H3("Oportunidades de melhoria"), html.Div(_li([
                "Trocar CSV por TimescaleDB/InfluxDB e um broker (MQTT/OPC UA) para ingestão real de sensores.",
                "Atualizar o gráfico no navegador com extendData (envia só o ponto novo) e downsampling (LTTB) para janelas longas.",
                "Substituir a regressão linear por modelos de degradação (exponencial, filtro de Kalman) e validar com falhas reais.",
                "Autenticação, perfis (operador/engenheiro/gestor) e trilha de auditoria nas OS.",
                "Servir com gunicorn + gevent e Redis pub/sub para escalar o WebSocket.",
            ]), className="prose")], className="card"),
        ], className="grid three")], className="section"),

        html.Div([html.H2("Comparativo de tecnologias"), html.Div(html.Table([
            html.Tr([html.Th("Opção"), html.Th("Pontos fortes"), html.Th("Limitações"), html.Th("Quando usar")]),
            html.Tr([html.Td("Dash + Plotly (usado)"), html.Td("Tudo em Python; callbacks reativos; gráficos interativos prontos; fácil de integrar com pandas."), html.Td("Cada interação passa pelo servidor; menos controle fino de visual."), html.Td("Dashboards analíticos com times de dados/engenharia.")]),
            html.Tr([html.Td("D3.js"), html.Td("Controle total do visual; desempenho excelente."), html.Td("Curva de aprendizado alta; muito código."), html.Td("Visualizações customizadas e inéditas.")]),
            html.Tr([html.Td("Chart.js"), html.Td("Leve, simples, bom para gráficos padrão."), html.Td("Menos recursos analíticos (zoom, subplots) nativos."), html.Td("Painéis simples embutidos em páginas web.")]),
            html.Tr([html.Td("Streamlit"), html.Td("Prototipagem muito rápida."), html.Td("Reexecuta o script a cada interação; layout menos flexível."), html.Td("Exploração e protótipos internos.")]),
            html.Tr([html.Td("Power BI / Tableau"), html.Td("Autosserviço, governança, conectores corporativos."), html.Td("Tempo real limitado/custo de licença; menos customização."), html.Td("BI corporativo e relatórios gerenciais.")]),
        ]), className="prose card")], className="section"),
    ])
