"""Layouts estáticos das páginas (os callbacks ficam em app.py)."""
from __future__ import annotations

from dash import dash_table, dcc, html

from .config import FAULTS, MACHINE_IDS, MACHINES, VARIABLES

MACHINE_OPTIONS = [{"label": f"{m['machine_id']} · {m['name']}", "value": m["machine_id"]} for m in MACHINES]


def field(label: str, control, fid: str | None = None):
    return html.Div([html.Label(label, htmlFor=fid), control], className="field")


def header(title: str, sub: str):
    return html.Div([
        html.Div([html.H1(title, className="page-title"), html.P(sub, className="page-sub")]),
        html.Div(id="ticker", className="ticker", role="status", **{"aria-live": "polite"}),
    ], className="topbar")


def overview():
    return html.Div([
        header("Visão geral da planta", "Estado de saúde das máquinas críticas em tempo real."),
        html.Div(id="ov-kpis", className="grid kpis"),
        html.Div([html.H2("Máquinas monitoradas"), html.Div(id="ov-grid", className="grid machines")], className="section"),
        html.Div([
            html.Div([html.H3("Mapa de severidade"),
                      html.P("Cada célula mostra a leitura atual; a cor indica a zona (verde = normal, âmbar = atenção, vermelho = crítico).", className="hint"),
                      dcc.Graph(id="ov-heat", config={"displayModeBar": False})], className="card"),
            html.Div([html.H3("Como ler este painel"),
                      html.Div([
                          html.P("Estados usam cor + forma + texto (● Normal, ▲ Atenção, ■ Crítico), de modo que a leitura não depende só da cor."),
                          html.P("O índice de saúde (0–100) combina o pior desvio e a média ponderada das três variáveis em relação aos limites operacionais."),
                          html.P("Clique em uma máquina para abrir a telemetria detalhada."),
                      ], className="prose")], className="card"),
        ], className="grid two section"),
    ])


def telemetry(machine: str):
    return html.Div([
        header("Telemetria ao vivo", "Séries temporais de vibração, temperatura e pressão com zonas de limite."),
        html.Div([
            field("Máquina", dcc.Dropdown(id="tele-machine", options=MACHINE_OPTIONS, value=machine, clearable=False), "tele-machine"),
            field("Janela de tempo", dcc.Dropdown(id="tele-window", clearable=False, value=150,
                                                  options=[{"label": "Últimos 2 min", "value": 60}, {"label": "Últimos 5 min", "value": 150},
                                                           {"label": "Últimos 15 min", "value": 450}]), "tele-window"),
        ], className="controls"),
        html.Div(id="tele-tiles", className="live-tiles"),
        html.Div(dcc.Graph(id="tele-graph", config={"displayModeBar": False}), className="card"),
        html.Div([
            html.H3("Simulador de falhas (demonstração)"),
            html.P("Injeta uma falha na máquina escolhida; os valores sobem/descem gradualmente (~20 s) e o detector abre um alerta ao confirmar 3 leituras consecutivas fora do limite.", className="hint"),
            html.Div([
                field("Máquina", dcc.Dropdown(id="fault-machine", options=MACHINE_OPTIONS, value=machine, clearable=False), "fault-machine"),
                field("Tipo de falha", dcc.Dropdown(id="fault-kind", clearable=False, value="rolamento",
                                                    options=[{"label": v["label"], "value": k} for k, v in FAULTS.items()]), "fault-kind"),
                html.Button("Injetar falha", id="fault-inject", className="btn danger", n_clicks=0),
                html.Button("Normalizar máquina", id="fault-clear", className="btn", n_clicks=0),
                html.Button("Normalizar todas", id="fault-clear-all", className="btn", n_clicks=0),
            ], className="controls"),
            html.Div(id="fault-msg", className="msg"),
        ], className="card section"),
    ])


def predictive(machine: str):
    return html.Div([
        header("Análise preditiva", "Tendência, anomalias e estimativa de vida útil restante (RUL) a partir do histórico em CSV."),
        html.Div([
            field("Máquina", dcc.Dropdown(id="pred-machine", options=MACHINE_OPTIONS, value=machine, clearable=False), "pred-machine"),
            field("Período", dcc.Dropdown(id="pred-days", clearable=False, value=14,
                                          options=[{"label": "Últimos 3 dias", "value": 3}, {"label": "Últimos 7 dias", "value": 7},
                                                   {"label": "Últimos 14 dias", "value": 14}]), "pred-days"),
            field("Variável analisada", dcc.Dropdown(id="pred-var", clearable=False, value="vibration_mm_s",
                                                     options=[{"label": f"{v['label']} ({v['unit']})", "value": k} for k, v in VARIABLES.items()]), "pred-var"),
        ], className="controls"),
        html.Div(id="pred-kpis", className="grid kpis"),
        html.Div([
            html.Div([html.H3("Índice de saúde"), html.P("Quanto menor, mais próximo dos limites. Faixas: atenção < 75, crítico < 45.", className="hint"),
                      dcc.Graph(id="pred-health", config={"displayModeBar": False})], className="card"),
            html.Div([html.H3("Estimativa de vida útil restante (RUL)"),
                      html.P("Regressão linear sobre médias horárias dos últimos 5 dias, extrapolada até o limite crítico.", className="hint"),
                      html.Div(id="pred-rul")], className="card"),
        ], className="grid two section"),
        html.Div([html.H3("Tendência e anomalias"),
                  html.P("Losangos marcam desvios de curto prazo (z-score robusto por mediana/MAD). A linha tracejada projeta a tendência até o horizonte.", className="hint"),
                  dcc.Graph(id="pred-trend", config={"displayModeBar": False})], className="card section"),
        html.Div([
            html.Div([html.H3("Comparativo entre máquinas"), html.P("Distribuição da variável no período (caixa = quartis).", className="hint"),
                      dcc.Graph(id="pred-box", config={"displayModeBar": False})], className="card"),
            html.Div([html.H3("Correlação entre variáveis"), html.P("Relação entre carga, vibração, temperatura e pressão da máquina.", className="hint"),
                      dcc.Graph(id="pred-corr", config={"displayModeBar": False})], className="card"),
        ], className="grid two section"),
    ])


TABLE_STYLE = dict(
    style_table={"overflowX": "auto"},
    style_header={"backgroundColor": "var(--surface-2)", "color": "var(--muted)", "fontWeight": "700", "border": "none",
                  "borderBottom": "1px solid var(--border)", "fontSize": "12px", "textTransform": "uppercase"},
    style_cell={"backgroundColor": "var(--surface)", "color": "var(--text)", "border": "none", "borderBottom": "1px solid var(--border)",
                "padding": "8px 10px", "fontSize": "13px", "textAlign": "left", "minWidth": "70px", "maxWidth": "420px", "fontFamily": "inherit"},
    style_data={"whiteSpace": "normal", "height": "auto"},
    style_data_conditional=[
        {"if": {"filter_query": '{Severidade} contains "Crítico"', "column_id": "Severidade"}, "color": "var(--crit)", "fontWeight": "700"},
        {"if": {"filter_query": '{Severidade} contains "Atenção"', "column_id": "Severidade"}, "color": "var(--warn)", "fontWeight": "700"},
        {"if": {"filter_query": '{Prioridade} = "Alta"', "column_id": "Prioridade"}, "color": "var(--crit)", "fontWeight": "700"},
        {"if": {"state": "selected"}, "backgroundColor": "var(--blue-soft)", "border": "none"},
    ],
)

ALERT_COLS = ["ID", "Data/hora", "Máquina", "Variável", "Severidade", "Valor", "Status", "OS", "Mensagem"]
WO_COLS = ["ID", "Criada em", "Máquina", "Tipo", "Prioridade", "Status", "Responsável", "Prazo", "Descrição"]


def alerts():
    return html.Div([
        header("Alertas e ordens de serviço", "Fluxo simplificado de manutenção: alerta → reconhecimento → ordem de serviço → conclusão."),
        html.Div([
            field("Status do alerta", dcc.Dropdown(id="al-status", multi=True, value=["Aberto", "Reconhecido"],
                                                   options=[{"label": s, "value": s} for s in ("Aberto", "Reconhecido", "Resolvido")]), "al-status"),
            field("Severidade", dcc.Dropdown(id="al-sev", multi=True, placeholder="Todas",
                                             options=[{"label": s, "value": s} for s in ("Crítico", "Atenção")]), "al-sev"),
            field("Máquina", dcc.Dropdown(id="al-machine", multi=True, placeholder="Todas", options=MACHINE_OPTIONS), "al-machine"),
        ], className="controls"),
        html.Div([
            html.H3("Alertas"),
            dash_table.DataTable(id="al-table", columns=[{"name": c, "id": c} for c in ALERT_COLS], data=[], row_selectable="multi",
                                 selected_rows=[], page_size=10, sort_action="native", **TABLE_STYLE),
            html.Div([
                html.Button("Reconhecer", id="al-ack", n_clicks=0, className="btn"),
                html.Button("Marcar como resolvido", id="al-resolve", n_clicks=0, className="btn"),
                html.Button("Gerar OS a partir da seleção", id="al-make-wo", n_clicks=0, className="btn primary"),
                html.Button("Exportar CSV", id="al-dl-btn", n_clicks=0, className="btn"),
            ], className="controls", style={"marginTop": "12px"}),
            html.Div(id="al-msg", className="msg", role="status"),
        ], className="card"),
        html.Div([
            html.H3("Ordens de serviço"),
            dash_table.DataTable(id="wo-table", columns=[{"name": c, "id": c} for c in WO_COLS], data=[], row_selectable="multi",
                                 selected_rows=[], page_size=8, sort_action="native", **TABLE_STYLE),
            html.Div([
                field("Novo status", dcc.Dropdown(id="wo-status", clearable=False, value="Em andamento",
                                                  options=[{"label": s, "value": s} for s in ("Aberta", "Em andamento", "Concluída", "Cancelada")]), "wo-status"),
                html.Button("Atualizar selecionadas", id="wo-set", n_clicks=0, className="btn"),
                html.Button("Exportar CSV", id="wo-dl-btn", n_clicks=0, className="btn"),
            ], className="controls", style={"marginTop": "12px"}),
            html.Div(id="wo-msg", className="msg", role="status"),
        ], className="card section"),
        html.Div([
            html.H3("Nova ordem de serviço manual"),
            html.Div([
                field("Máquina", dcc.Dropdown(id="new-machine", options=MACHINE_OPTIONS, value=MACHINE_IDS[0], clearable=False), "new-machine"),
                field("Tipo", dcc.Dropdown(id="new-type", clearable=False, value="Preditiva",
                                           options=[{"label": s, "value": s} for s in ("Preditiva", "Preventiva", "Corretiva")]), "new-type"),
                field("Prioridade", dcc.Dropdown(id="new-prio", clearable=False, value="Média",
                                                 options=[{"label": s, "value": s} for s in ("Baixa", "Média", "Alta")]), "new-prio"),
                field("Descrição", dcc.Input(id="new-desc", type="text", className="input", placeholder="Ex.: inspecionar rolamento do spindle", debounce=False), "new-desc"),
                html.Button("Criar OS", id="new-create", n_clicks=0, className="btn primary"),
            ], className="controls"),
        ], className="card section"),
        dcc.Download(id="dl-alerts"), dcc.Download(id="dl-wo"),
        dcc.Store(id="al-version", data=0),
        dcc.Interval(id="al-interval", interval=5000),
    ])
