"""Aplicação Dash: roteamento, tema e callbacks."""
from __future__ import annotations

import time
from urllib.parse import parse_qs

import pandas as pd
from dash import Dash, Input, Output, State, callback_context, dcc, html, no_update
from dash.exceptions import PreventUpdate

from . import diagnostic, pages, store
from .analytics import enrich, estimate_rul, health_index, level_of, rolling_anomalies
from .config import (ROOT, FAULTS, HISTORY_FILE, LIMITS, MACHINE_BY_ID, MACHINE_IDS, MACHINES, PRESSURE_LABEL, STATUS_LABEL,
                     STATUS_SHAPE, VAR_KEYS, VARIABLES)
from .figs import (box_fig, corr_fig, empty_fig, fmt, health_fig, heatmap_fig, pal, sparkline_uri, style, telemetry_fig, trend_fig)
from .stream import Hub, Simulator, register_routes

NAV = [("/", "▦", "Visão geral"), ("/telemetria", "∿", "Telemetria"), ("/preditiva", "◔", "Análise preditiva"),
       ("/alertas", "⚑", "Alertas e OS"), ("/diagnostico", "✎", "Diagnóstico")]
VAR_SHORT = {"vibration_mm_s": "vib", "temperature_c": "temp", "pressure_bar": "press"}
VAR_LABEL = {k: v["label"] for k, v in VARIABLES.items()}


def create_app() -> tuple[Dash, Simulator]:
    hub = Hub()
    sim = Simulator(hub)
    app = Dash(__name__, assets_folder=str(ROOT / "assets"), title="PredictaMaq · Manutenção Preditiva", suppress_callback_exceptions=True, update_title=None,
               meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}])
    register_routes(app.server, sim, hub)

    app.layout = html.Div([
        dcc.Location(id="url"),
        dcc.Store(id="live-store"),
        dcc.Store(id="theme", storage_type="local"),
        html.Div(id="theme-sink", hidden=True),
        html.Div([
            html.Aside([
                html.Div([html.Div("PM", className="brand-mark"),
                          html.Div([html.Div("PredictaMaq", className="brand-title"), html.Div("Manutenção preditiva", className="brand-sub")])], className="brand"),
                html.Nav([dcc.Link([html.Span(ico, className="ico"), label], href=href, id=f"nav-{i}") for i, (href, ico, label) in enumerate(NAV)],
                         className="nav", **{"aria-label": "Principal"}),
                html.Div([
                    html.Span("Conectando…", id="ws-indicator", className="ws-indicator connecting"),
                    html.Button("◐ Alternar tema", id="theme-toggle", className="theme-btn", n_clicks=0, title="Alternar entre tema claro e escuro"),
                    html.Div("Protótipo acadêmico · dados fictícios · paleta inspirada na identidade da WEG.", className="disclaimer"),
                ], className="side-foot"),
            ], className="sidebar"),
            html.Main(id="page", className="main"),
        ], className="shell"),
    ])

    # ------------------------------------------------------------------ tema
    app.clientside_callback(
        """function(n, current){
            if (n) { return current === 'dark' ? 'light' : 'dark'; }
            return current || (window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
        }""",
        Output("theme", "data"), Input("theme-toggle", "n_clicks"), State("theme", "data"))
    app.clientside_callback(
        """function(t){ document.documentElement.setAttribute('data-theme', t || 'light'); return t; }""",
        Output("theme-sink", "children"), Input("theme", "data"))

    # ------------------------------------------------------------------ roteamento
    @app.callback(Output("page", "children"), [Output(f"nav-{i}", "className") for i in range(len(NAV))],
                  Input("url", "pathname"), Input("url", "search"))
    def route(path, search):
        path = (path or "/").rstrip("/") or "/"
        q = parse_qs((search or "").lstrip("?"))
        machine = q.get("machine", [MACHINE_IDS[0]])[0]
        machine = machine if machine in MACHINE_BY_ID else MACHINE_IDS[0]
        if path == "/telemetria":
            page = pages.telemetry(machine)
        elif path == "/preditiva":
            page = pages.predictive("PR-02" if "machine" not in q else machine)
        elif path == "/alertas":
            page = pages.alerts()
        elif path == "/diagnostico":
            page = diagnostic.layout(sim)
        else:
            path, page = "/", pages.overview()
        return [page] + ["active" if href == path else "" for href, _, _ in NAV]

    # ------------------------------------------------------------------ ticker
    @app.callback(Output("ticker", "children"), Input("live-store", "data"), Input("url", "pathname"))
    def ticker(_live, _path):
        alerts = list(sim.recent_alerts)
        if not alerts:
            return [html.Span("●", style={"color": "var(--ok)"}), "Nenhum alerta novo nesta sessão."]
        a = alerts[0]
        lvl = 2 if a["severity"] == "Crítico" else 1
        return [html.Span(f"{STATUS_SHAPE[lvl]} {a['severity']}", className=f"badge s{lvl}"),
                html.Span(f"{a['machine_id']} · {a['message']}")]

    # ------------------------------------------------------------------ visão geral
    @app.callback(Output("ov-kpis", "children"), Output("ov-grid", "children"), Output("ov-heat", "figure"),
                  Input("live-store", "data"), Input("theme", "data"))
    def overview(_live, theme):
        snap = sim.snapshot()
        p = pal(theme)
        counts = {0: 0, 1: 0, 2: 0}
        his = []
        cards = []
        for m in MACHINES:
            d = snap["machines"][m["machine_id"]]
            counts[d["status"]] += 1
            his.append(d["hi"])
            last = {v: d[VAR_SHORT[v]][-1] for v in VAR_KEYS}
            lvls = {v: level_of(m["type"], v, last[v]) for v in VAR_KEYS}
            mvars = [html.Div([html.Span(VAR_LABEL[v], className="mvar-label"),
                               html.Span([fmt(last[v], VARIABLES[v]["decimals"]), html.Small(VARIABLES[v]["unit"])], className="mvar-val")],
                              className=f"mvar lvl-{lvls[v]}") for v in VAR_KEYS]
            st = d["status"]
            cards.append(dcc.Link([
                html.Div([html.Span(m["machine_id"], className="mcard-id"),
                          html.Span(f"{STATUS_SHAPE[st]} {STATUS_LABEL[st]}", className=f"badge s{st}")], className="mcard-head"),
                html.Div(m["name"], className="mcard-name"), html.Div(m["area"], className="mcard-area"),
                html.Div([html.Div(html.Div(className=f"hi-fill s{st}", style={"width": f"{max(2, d['hi'])}%"}), className="hi-bar"),
                          html.Span(f"Saúde {fmt(d['hi'], 0)}")], className="hi"),
                html.Div(mvars, className="mvars"),
                html.Img(src=sparkline_uri(d["vib"], p["vib"]), className="spark", alt=f"Tendência recente de vibração de {m['machine_id']}"),
            ], href=f"/telemetria?machine={m['machine_id']}", className=f"mcard status-{st}"))
        al = store.list_alerts()
        open_n = int((al["status"] == "Aberto").sum()) if len(al) else 0
        avg = sum(his) / len(his)
        kpis = [
            _kpi("Índice de saúde da frota", fmt(avg, 0), "média das máquinas (0–100)", "neutral"),
            _kpi("Em operação normal", str(counts[0]), f"de {len(MACHINES)} máquinas", "lvl-0"),
            _kpi("Em atenção", str(counts[1]), "acima do limite de atenção", "lvl-1" if counts[1] else "neutral"),
            _kpi("Críticas", str(counts[2]), "exigem ação imediata", "lvl-2" if counts[2] else "neutral"),
            _kpi("Alertas em aberto", str(open_n), "aguardando reconhecimento", "lvl-1" if open_n else "neutral"),
        ]
        return kpis, cards, heatmap_fig(snap, theme)

    # ------------------------------------------------------------------ telemetria
    @app.callback(Output("tele-tiles", "children"), Output("tele-graph", "figure"),
                  Input("live-store", "data"), Input("tele-machine", "value"), Input("tele-window", "value"), Input("theme", "data"))
    def telemetry(_live, machine, window, theme):
        snap = sim.snapshot()
        machine = machine or MACHINE_IDS[0]
        m = MACHINE_BY_ID[machine]
        d = snap["machines"][machine]
        n = int(window or 150)
        data = {k: (v[-n:] if isinstance(v, list) else v) for k, v in d.items()}
        tiles = []
        label = {"vibration_mm_s": "Vibração", "temperature_c": "Temperatura", "pressure_bar": PRESSURE_LABEL[m["type"]]}
        for v in VAR_KEYS:
            val = data[VAR_SHORT[v]][-1]
            lvl = level_of(m["type"], v, val)
            tiles.append(html.Div([html.Div(label[v], className="tile-label"),
                                   html.Div([fmt(val, VARIABLES[v]["decimals"]), html.Small(" " + VARIABLES[v]["unit"])], className="tile-val"),
                                   html.Div(f"{STATUS_SHAPE[lvl]} {STATUS_LABEL[lvl]}", className=f"tile-state")], className=f"tile lvl-{lvl}"))
        tiles.append(html.Div([html.Div("Carga", className="tile-label"),
                               html.Div([fmt(data["load"][-1], 0), html.Small(" %")], className="tile-val"),
                               html.Div(f"Saúde {fmt(d['hi'], 0)}", className="tile-state")], className="tile"))
        return tiles, telemetry_fig(m, data, theme)

    @app.callback(Output("fault-msg", "children"), Input("fault-inject", "n_clicks"), Input("fault-clear", "n_clicks"),
                  Input("fault-clear-all", "n_clicks"), State("fault-machine", "value"), State("fault-kind", "value"), prevent_initial_call=True)
    def faults(_a, _b, _c, machine, kind):
        trig = callback_context.triggered_id
        if trig == "fault-inject":
            sim.inject_fault(machine, kind)
            return f"Falha '{FAULTS[kind]['label']}' injetada em {machine}. Acompanhe os gráficos e a aba Alertas."
        if trig == "fault-clear":
            sim.clear_faults(machine)
            return f"{machine} voltando ao normal."
        sim.clear_faults()
        return "Todas as máquinas voltando ao normal."

    # ------------------------------------------------------------------ análise preditiva
    @app.callback(Output("pred-kpis", "children"), Output("pred-health", "figure"), Output("pred-rul", "children"),
                  Output("pred-trend", "figure"), Output("pred-box", "figure"), Output("pred-corr", "figure"),
                  Input("pred-machine", "value"), Input("pred-days", "value"), Input("pred-var", "value"), Input("theme", "data"))
    def predictive(machine, days, var, theme):
        machine, days, var = machine or "PR-02", days or 14, var or "vibration_mm_s"
        full = enrich(store.load_history())
        end = full["timestamp"].max()
        view = full[full["timestamp"] >= end - pd.Timedelta(days=days)]
        mdf = view[view["machine_id"] == machine]
        mtype = MACHINE_BY_ID[machine]["type"]
        last = mdf.tail(6)
        hi_now = float(last["health_index"].mean())
        st_now = int(last["status"].max())
        rows, ruls = [], {}
        for v in VAR_KEYS:
            r = estimate_rul(full, machine, v, days=5)
            ruls[v] = r
            lvl = level_of(mtype, v, float(last[v].mean()))
            if r["rul_days"] is None or r["rul_days"] > 60:
                txt, cls = ("Estável (> 60 d)", "s0")
            else:
                txt = f"{fmt(r['rul_days'], 1)} dias"
                cls = "s2" if r["rul_days"] < 7 else ("s1" if r["rul_days"] < 21 else "s0")
            conf = "alta" if r["r2"] >= 0.8 else ("média" if r["r2"] >= 0.5 else "baixa")
            rows.append(html.Tr([html.Td(VAR_LABEL[v]), html.Td(html.Span(f"{STATUS_SHAPE[lvl]} {STATUS_LABEL[lvl]}", className=f"pill s{lvl}")),
                                 html.Td(f"{fmt(r['slope_per_day'], 3)} {VARIABLES[v]['unit']}/dia"), html.Td(html.Span(txt, className=f"pill {cls}")),
                                 html.Td(f"{conf} (R² {fmt(r['r2'], 2)})")]))
        rul_tbl = [html.Table([html.Tr([html.Th("Variável"), html.Th("Agora"), html.Th("Tendência"), html.Th("RUL até o crítico"), html.Th("Confiança")])] + rows, className="rul-table"),
                   html.P("Modelo didático: assume tendência linear; confiança baixa indica que a série não segue uma reta (ex.: ruído ou picos).", className="hint", style={"marginTop": "10px"})]
        finite = [r["rul_days"] for r in ruls.values() if r["rul_days"] is not None and r["rul_days"] <= 60]
        min_rul = min(finite) if finite else None
        kpis = [
            _kpi("Índice de saúde", fmt(hi_now, 0), "média das últimas 6 leituras", f"lvl-{0 if hi_now >= 75 else 1 if hi_now >= 45 else 2}"),
            _kpi("Estado atual", f"{STATUS_SHAPE[st_now]} {STATUS_LABEL[st_now]}", MACHINE_BY_ID[machine]["name"], f"lvl-{st_now}"),
            _kpi("Menor RUL estimado", "—" if min_rul is None else f"{fmt(min_rul, 1)} d", "entre as 3 variáveis" if min_rul is not None else "sem tendência de falha no horizonte",
                 "neutral" if min_rul is None else ("lvl-2" if min_rul < 7 else "lvl-1" if min_rul < 21 else "lvl-0")),
            _kpi("Anomalias no período", str(int(rolling_anomalies(mdf.set_index("timestamp")[var])["anomaly"].sum())), f"{VAR_LABEL[var].lower()}, z robusto > 3,5", "neutral"),
        ]
        an = rolling_anomalies(mdf.set_index("timestamp")[var])
        return (kpis, health_fig(mdf, theme), rul_tbl, trend_fig(mdf, machine, var, ruls[var], theme, an),
                box_fig(view, var, theme), corr_fig(view, machine, theme))

    # ------------------------------------------------------------------ alertas e OS
    @app.callback(Output("al-table", "data"), Output("wo-table", "data"),
                  Input("al-interval", "n_intervals"), Input("al-version", "data"), Input("al-status", "value"),
                  Input("al-sev", "value"), Input("al-machine", "value"))
    def refresh_tables(_n, _v, statuses, sevs, machines):
        al = store.list_alerts()
        if statuses:
            al = al[al["status"].isin(statuses)]
        if sevs:
            al = al[al["severity"].isin(sevs)]
        if machines:
            al = al[al["machine_id"].isin(machines)]
        lvl = {"Crítico": 2, "Atenção": 1}
        al_rows = [{"id": r.alert_id, "ID": r.alert_id, "Data/hora": r.timestamp, "Máquina": r.machine_id, "Variável": VAR_LABEL.get(r.variable, r.variable),
                    "Severidade": f"{STATUS_SHAPE[lvl[r.severity]]} {r.severity}", "Valor": r.value, "Status": r.status, "OS": r.work_order_id,
                    "Mensagem": r.message} for r in al.head(300).itertuples()]
        wo = store.list_work_orders()
        wo_rows = [{"id": r.wo_id, "ID": r.wo_id, "Criada em": r.created_at, "Máquina": r.machine_id, "Tipo": r.type, "Prioridade": r.priority,
                    "Status": r.status, "Responsável": r.assigned_to, "Prazo": r.due_date[:10], "Descrição": r.description} for r in wo.itertuples()]
        return al_rows, wo_rows

    @app.callback(Output("al-msg", "children"), Output("al-version", "data"),
                  Input("al-ack", "n_clicks"), Input("al-resolve", "n_clicks"), Input("al-make-wo", "n_clicks"),
                  Input("wo-set", "n_clicks"), Input("new-create", "n_clicks"),
                  State("al-table", "selected_rows"), State("al-table", "data"), State("wo-table", "selected_rows"), State("wo-table", "data"),
                  State("wo-status", "value"), State("new-machine", "value"), State("new-type", "value"), State("new-prio", "value"),
                  State("new-desc", "value"), State("al-version", "data"), prevent_initial_call=True)
    def actions(_a, _b, _c, _d, _e, al_sel, al_data, wo_sel, wo_data, wo_status, nm, nt, np_, nd, version):
        trig = callback_context.triggered_id
        ids = [al_data[i]["ID"] for i in (al_sel or []) if i < len(al_data)]
        wids = [wo_data[i]["ID"] for i in (wo_sel or []) if i < len(wo_data)]
        bump = (version or 0) + 1
        if trig in ("al-ack", "al-resolve", "al-make-wo"):
            if not ids:
                return "Selecione ao menos um alerta na tabela.", no_update
            if trig == "al-ack":
                n = store.set_alert_status(ids, "Reconhecido")
                return f"{n} alerta(s) reconhecido(s).", bump
            if trig == "al-resolve":
                n = store.set_alert_status(ids, "Resolvido")
                return f"{n} alerta(s) marcado(s) como resolvido(s).", bump
            created = []
            for row in (al_data[i] for i in al_sel if i < len(al_data)):
                prio = "Alta" if "Crítico" in row["Severidade"] else "Média"
                wo = store.create_work_order(row["Máquina"], prio, "Preditiva", f"{row['Variável']}: {row['Mensagem']}", alert_id=row["ID"],
                                             due_days=1 if prio == "Alta" else 3)
                created.append(wo["wo_id"])
            store.set_alert_status(ids, "Reconhecido")
            return f"Ordens criadas: {', '.join(created)}.", bump
        if trig == "wo-set":
            if not wids:
                return "Selecione ao menos uma ordem de serviço na tabela de OS.", no_update
            n = store.set_work_order_status(wids, wo_status)
            return f"{n} OS atualizada(s) para '{wo_status}'.", bump
        if trig == "new-create":
            if not (nd or "").strip():
                return "Informe a descrição da OS.", no_update
            wo = store.create_work_order(nm, np_, nt, nd.strip())
            return f"OS {wo['wo_id']} criada para {nm}.", bump
        raise PreventUpdate

    @app.callback(Output("dl-alerts", "data"), Input("al-dl-btn", "n_clicks"), prevent_initial_call=True)
    def dl_alerts(_n):
        return dcc.send_data_frame(store.list_alerts().to_csv, "alertas.csv", index=False)

    @app.callback(Output("dl-wo", "data"), Input("wo-dl-btn", "n_clicks"), prevent_initial_call=True)
    def dl_wo(_n):
        return dcc.send_data_frame(store.list_work_orders().to_csv, "ordens_de_servico.csv", index=False)

    return app, sim


def _kpi(label: str, value: str, note: str, cls: str):
    return html.Div([html.Div(label, className="kpi-label"), html.Div(value, className="kpi-value"), html.Div(note, className="kpi-note")],
                    className=f"card kpi {cls}")
