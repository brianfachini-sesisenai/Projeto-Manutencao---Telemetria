"""Layouts das páginas. Cada página responde a uma pergunta; o restante fica em detalhes recolhíveis."""
from __future__ import annotations

from dash import dcc, html

from .config import FAULTS, MACHINES, MACHINE_IDS, VARIABLES
from .ui import details, machine_seg, page_head, seg

MACHINE_OPTIONS = [{"label": f"{m['machine_id']} · {m['name']}", "value": m["machine_id"]} for m in MACHINES]


def overview():
    return html.Div([
        page_head("Visão geral", "Como está a planta agora e o que precisa da sua atenção."),
        html.Div(id="ov-hero"),
        html.Div([html.Div("Precisam de atenção", className="section-title"), html.Div(id="ov-attn")], className="section"),
        html.Div([html.Div("Todas as máquinas", className="section-title"), html.Div(id="ov-table")], className="section"),
    ])


def _vtab(var: str, name: str):
    return html.Div([html.Span(name, className="vtab-name"), html.Span(id=f"tv-{var}", className="vtab-val"),
                     html.Span(id=f"ts-{var}", className="vtab-state")], className="vtab")


def monitor(machine: str):
    return html.Div([
        page_head("Monitoramento", "Leituras dos sensores em tempo real, comparadas aos limites de operação."),
        html.Div([machine_seg("mon-machine", machine),
                  seg("mon-window", [(60, "2 min"), (150, "5 min"), (450, "15 min")], 150)], className="machine-bar"),
        html.Div(id="mon-head", className="machine-head"),
        dcc.RadioItems(id="mon-var", className="vtabs", value="vibration_mm_s",
                       options=[{"label": _vtab(k, v["label"]), "value": k} for k, v in VARIABLES.items()]),
        html.Div([html.Div(id="mon-title", className="chart-title"), dcc.Graph(id="mon-graph", config={"displayModeBar": False})], className="card chart-card"),
        details("Modo demonstração: simular uma falha",
                html.P("Injeta uma falha na máquina escolhida. Os valores se deslocam em ~20 s e o alerta abre após 3 leituras consecutivas fora do limite.", className="muted small"),
                html.Div([
                    html.Div([html.Label("Máquina", htmlFor="fault-machine"), dcc.Dropdown(id="fault-machine", options=MACHINE_OPTIONS, value=machine, clearable=False)], className="field"),
                    html.Div([html.Label("Tipo de falha", htmlFor="fault-kind"), dcc.Dropdown(id="fault-kind", clearable=False, value="rolamento",
                                                                                            options=[{"label": v["label"], "value": k} for k, v in FAULTS.items()])], className="field"),
                    html.Button("Injetar falha", id="fault-inject", className="btn danger", n_clicks=0),
                    html.Button("Normalizar tudo", id="fault-clear-all", className="btn", n_clicks=0),
                ], className="row-controls"),
                html.Div(id="fault-msg", className="msg", style={"marginTop": "12px"})),
    ])


def analysis(machine: str):
    return html.Div([
        page_head("Análise preditiva", "Quando agir: tendência de degradação e estimativa de vida útil restante."),
        html.Div([machine_seg("pred-machine", machine)], className="machine-bar"),
        html.Div(id="pred-insight", className="card insight"),
        html.Div(id="pred-msg", className="msg", style={"marginTop": "10px"}),
        html.Div([
            seg("pred-view", [("vibration_mm_s", "Vibração"), ("temperature_c", "Temperatura"), ("pressure_bar", "Pressão"),
                              ("health", "Índice de saúde"), ("compare", "Comparar máquinas")], "vibration_mm_s"),
            seg("pred-days", [(7, "7 dias"), (14, "14 dias")], 14),
        ], className="toolbar", style={"marginTop": "28px"}),
        html.Div([html.Div(id="pred-title", className="chart-title"), dcc.Graph(id="pred-graph", config={"displayModeBar": False})], className="card chart-card"),
        details("Como a estimativa é calculada", html.Div(id="pred-detail")),
    ])


def alerts():
    return html.Div([
        page_head("Alertas e manutenção", "Trate o que está pendente: reconheça o alerta, abra uma ordem de serviço e acompanhe até concluir.",
                  html.Div([html.Button("Exportar CSV", id="al-dl-btn", className="btn ghost sm", n_clicks=0)])),
        html.Div(id="al-msg", className="msg"),
        html.Div([
            seg("al-view", [("alerts", "Alertas"), ("wo", "Ordens de serviço")], "alerts"),
            seg("al-filter", [("pending", "Pendentes"), ("done", "Concluídos"), ("all", "Todos")], "pending"),
        ], className="toolbar"),
        html.Div(id="al-list", className="card list"),
        details("Nova ordem de serviço manual", html.Div([
            html.Div([html.Label("Máquina", htmlFor="new-machine"), dcc.Dropdown(id="new-machine", options=MACHINE_OPTIONS, value=MACHINE_IDS[0], clearable=False)], className="field"),
            html.Div([html.Label("Tipo", htmlFor="new-type"), dcc.Dropdown(id="new-type", clearable=False, value="Preditiva",
                                                                         options=[{"label": s, "value": s} for s in ("Preditiva", "Preventiva", "Corretiva")])], className="field"),
            html.Div([html.Label("Prioridade", htmlFor="new-prio"), dcc.Dropdown(id="new-prio", clearable=False, value="Média",
                                                                               options=[{"label": s, "value": s} for s in ("Baixa", "Média", "Alta")])], className="field"),
            html.Div([html.Label("Descrição", htmlFor="new-desc"), dcc.Input(id="new-desc", type="text", className="input", placeholder="Ex.: inspecionar rolamento do spindle")], className="field", style={"flex": "2"}),
            html.Button("Criar ordem", id="new-create", className="btn primary", n_clicks=0),
        ], className="row-controls")),
        dcc.Download(id="dl-file"),
        dcc.Store(id="al-version", data=0),
        dcc.Interval(id="al-interval", interval=8000),
    ])


def about():
    return html.Div([
        page_head("Sobre o projeto", "Material de apoio ao relatório: metodologia, princípios de design, diagnóstico crítico e tecnologias."),
        html.Div(seg("sobre-tab", [("ux", "Princípios de design"), ("diag", "Diagnóstico crítico"), ("tech", "Tecnologias"),
                                   ("arch", "Arquitetura"), ("meas", "Medições")], "ux"), className="toolbar"),
        html.Div(id="sobre-body"),
    ])
