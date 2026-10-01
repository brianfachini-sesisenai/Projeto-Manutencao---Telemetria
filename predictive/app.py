"""Aplicação Dash: roteamento, tema e callbacks."""
from __future__ import annotations

from datetime import datetime
from urllib.parse import parse_qs

import pandas as pd
from dash import ALL, Dash, Input, Output, State, callback_context, dcc, html, no_update
from dash.exceptions import PreventUpdate

from . import diagnostic, insights, pages, store
from .analytics import enrich, estimate_rul, level_of, rolling_anomalies
from .config import FAULTS, MACHINE_BY_ID, MACHINE_IDS, MACHINES, ROOT, STATUS_LABEL, VAR_KEYS, VARIABLES
from .figs import compare_fig, fmt, health_fig, live_fig, trend_fig
from .stream import Hub, Simulator, register_routes
from .ui import chip

NAV = [("/", "Visão geral"), ("/monitoramento", "Monitoramento"), ("/analise", "Análise preditiva"), ("/alertas", "Alertas"), ("/sobre", "Sobre")]
SHORT = insights.SHORT
VAR_UNIT = {k: v["unit"] for k, v in VARIABLES.items()}


def _val(v: str, x: float) -> str:
    return f"{fmt(x, VARIABLES[v]['decimals'])} {VARIABLES[v]['unit']}"


def _plural(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def create_app() -> tuple[Dash, Simulator]:
    hub = Hub()
    sim = Simulator(hub)
    app = Dash(__name__, assets_folder=str(ROOT / "assets"), title="PredictaMaq · Manutenção preditiva", suppress_callback_exceptions=True, update_title=None,
               meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}])
    register_routes(app.server, sim, hub)

    app.layout = html.Div([
        dcc.Location(id="url"), dcc.Store(id="live-store"), dcc.Store(id="theme", storage_type="local"), html.Div(id="theme-sink", hidden=True),
        html.Header(html.Div([
            html.Div([html.Div("P", className="brand-mark"), html.Span("PredictaMaq", className="bn")], className="brand"),
            html.Nav([dcc.Link([label, html.Span(id="nav-badge", className="nav-badge")] if href == "/alertas" else label, href=href, id=f"nav-{i}")
                      for i, (href, label) in enumerate(NAV)], className="nav", **{"aria-label": "Principal"}),
            html.Div([html.Span("Conectando…", id="ws-indicator", className="ws-indicator connecting"),
                      html.Button(id="theme-toggle", className="icon-btn", n_clicks=0, title="Alternar tema claro/escuro", **{"aria-label": "Alternar tema"}),
                      html.Div("EM", className="avatar", title="Engenharia de Manutenção")], className="appbar-right"),
        ], className="appbar-in"), className="appbar"),
        html.Main(id="page", className="page"),
        html.Div(id="toast-area", **{"aria-live": "polite"}),
    ])

    # ------------------------------------------------------------ tema
    app.clientside_callback(
        """function(n, current){ if (n) { return current === 'dark' ? 'light' : 'dark'; }
            return current || (window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'); }""",
        Output("theme", "data"), Input("theme-toggle", "n_clicks"), State("theme", "data"))
    app.clientside_callback("""function(t){ document.documentElement.setAttribute('data-theme', t || 'light'); return t; }""",
                            Output("theme-sink", "children"), Input("theme", "data"))

    # ------------------------------------------------------------ rotas
    @app.callback(Output("page", "children"), [Output(f"nav-{i}", "className") for i in range(len(NAV))], Input("url", "pathname"), Input("url", "search"))
    def route(path, search):
        path = (path or "/").rstrip("/") or "/"
        q = parse_qs((search or "").lstrip("?"))
        machine = q.get("machine", [None])[0]
        machine = machine if machine in MACHINE_BY_ID else None
        if path == "/monitoramento":
            page = pages.monitor(machine or MACHINE_IDS[0])
        elif path == "/analise":
            page = pages.analysis(machine or "PR-02")
        elif path == "/alertas":
            page = pages.alerts()
        elif path == "/sobre":
            page = pages.about()
        else:
            path, page = "/", pages.overview()
        return [page] + ["active" if href == path else "" for href, _ in NAV]

    # ------------------------------------------------------------ notificações + selo de alertas
    @app.callback(Output("toast-area", "children"), Output("nav-badge", "children"), Input("live-store", "data"))
    def notify(_live):
        al = store.list_alerts()
        pending = int((al["status"] == "Aberto").sum()) if len(al) else 0
        toast = None
        if sim.recent_alerts:
            a = sim.recent_alerts[0]
            if (pd.Timestamp.now() - pd.Timestamp(a["timestamp"])).total_seconds() < 8:
                lvl = 2 if a["severity"] == "Crítico" else 1
                toast = dcc.Link(html.Div([chip(lvl), html.Div([html.B(f"Novo alerta em {a['machine_id']}"), html.Span(a["message"])])], className=f"toast s{lvl}"),
                                 href="/alertas")
        return toast, (str(pending) if pending else "")

    # ------------------------------------------------------------ visão geral
    @app.callback(Output("ov-hero", "children"), Output("ov-attn", "children"), Output("ov-table", "children"), Input("live-store", "data"))
    def overview(_live):
        snap = sim.snapshot()
        counts, data = {0: 0, 1: 0, 2: 0}, []
        for m in MACHINES:
            d = snap["machines"][m["machine_id"]]
            counts[d["status"]] += 1
            data.append((m, d, {v: d[SHORT[v]][-1] for v in VAR_KEYS}))
        worst = 2 if counts[2] else 1 if counts[1] else 0
        if worst == 2:
            title = f"{_plural(counts[2], 'máquina em estado crítico', 'máquinas em estado crítico')}"
        elif worst == 1:
            title = f"{_plural(counts[1], 'máquina precisa', 'máquinas precisam')} de atenção"
        else:
            title = "Todas as máquinas operam normalmente"
        hero = html.Div([
            html.Div([html.H2(title, className="hero-title"),
                      html.P(f"Atualizado às {datetime.now():%H:%M:%S} · {len(MACHINES)} máquinas monitoradas", className="hero-sub"),
                      html.Div([chip(0, f"{counts[0]} normais"), chip(1, f"{counts[1]} em atenção"), chip(2, f"{counts[2]} críticas")], className="hero-counts")], className="hero-text"),
            dcc.Link("Ver alertas", href="/alertas", className="btn primary") if worst else html.Div(),
        ], className=f"card hero s{worst}")
        needs = sorted([x for x in data if x[1]["status"] > 0], key=lambda x: (-x[1]["status"], x[1]["hi"]))
        if needs:
            cards = []
            for m, d, last in needs:
                st = d["status"]
                tt = insights.trend_text(m["machine_id"])
                cards.append(html.Div([
                    html.Div([html.Div([html.Div(m["name"], className="attn-name"), html.Div(f"{m['machine_id']} · {m['area']}", className="attn-area")]), chip(st)], className="attn-top"),
                    html.P(insights.reason(m["machine_id"], last), className="attn-reason"),
                    html.P(["Tendência: ", tt], className="attn-trend") if tt else html.Div(),
                    html.Div([dcc.Link("Analisar tendência", href=f"/analise?machine={m['machine_id']}", className="btn primary sm"),
                              dcc.Link("Ver em tempo real", href=f"/monitoramento?machine={m['machine_id']}", className="btn ghost sm")], className="attn-foot"),
                ], className=f"card attn s{st}"))
            attn = html.Div(cards, className="attn-grid")
        else:
            attn = html.Div([chip(0, "Tudo certo"), "Nenhuma máquina fora da faixa normal neste momento."], className="card allgood")
        head = html.Div([html.Div("Estado"), html.Div("Máquina"), html.Div("Saúde", className="c-h"),
                         html.Div("Vibração", className="c-v"), html.Div("Temperatura", className="c-v"), html.Div("Pressão", className="c-v"), html.Div()], className="mrow head")
        rows = []
        for m, d, last in sorted(data, key=lambda x: (-x[1]["status"], x[0]["machine_id"])):
            mt = m["type"]
            vals = [html.Div(_val(v, last[v]), className=f"mval c-v num lvl{level_of(mt, v, last[v])}") for v in VAR_KEYS]
            rows.append(dcc.Link([chip(d["status"]), html.Div([html.Div(m["name"], className="mname"), html.Div(f"{m['machine_id']} · {m['area']}", className="marea")]),
                                  html.Div([html.Div(html.Div(className="hbar-fill", style={"width": f"{max(3, d['hi'])}%"}), className="hbar-track"), html.Span(fmt(d["hi"], 0), className="hbar-val num")], className="hbar c-h"),
                                  *vals, html.Div("›", className="chev")], href=f"/monitoramento?machine={m['machine_id']}", className="mrow"))
        return hero, attn, html.Div([head, *rows], className="card mtable")

    # ------------------------------------------------------------ monitoramento
    outs = [Output("mon-head", "children"), Output("mon-title", "children"), Output("mon-graph", "figure")]
    for v in VAR_KEYS:
        outs += [Output(f"tv-{v}", "children"), Output(f"ts-{v}", "children")]

    @app.callback(*outs, Input("live-store", "data"), Input("mon-machine", "value"), Input("mon-var", "value"), Input("mon-window", "value"), Input("theme", "data"))
    def monitor(_live, machine, var, window, theme):
        machine = machine or MACHINE_IDS[0]
        m, var = MACHINE_BY_ID[machine], var or "vibration_mm_s"
        d = sim.snapshot()["machines"][machine]
        n = int(window or 150)
        last = {v: d[SHORT[v]][-1] for v in VAR_KEYS}
        head = [html.Div(m["name"], className="machine-title"), chip(d["status"]),
                html.Span(f"{m['area']} · saúde {fmt(d['hi'], 0)}/100 · carga {fmt(d['load'][-1], 0)}%", className="muted")]
        lvl = level_of(m["type"], var, last[var])
        title = [html.H3(f"{insights.label(machine, var)} ({VAR_UNIT[var]})"), html.Span("Últimos " + {60: "2", 150: "5", 450: "15"}.get(n, "5") + " minutos", className="faint small")]
        fig = live_fig(m, var, d["t"][-n:], d[SHORT[var]][-n:], theme, lvl)
        res = [head, title, fig]
        for v in VAR_KEYS:
            res += [[fmt(last[v], VARIABLES[v]["decimals"]), html.Small(VAR_UNIT[v])], chip(level_of(m["type"], v, last[v]))]
        return tuple(res)

    @app.callback(Output("fault-msg", "children"), Input("fault-inject", "n_clicks"), Input("fault-clear-all", "n_clicks"),
                  State("fault-machine", "value"), State("fault-kind", "value"), prevent_initial_call=True)
    def faults(_a, _b, machine, kind):
        if callback_context.triggered_id == "fault-inject":
            sim.inject_fault(machine, kind)
            return f"Falha injetada em {machine}: {FAULTS[kind]['label']}. Acompanhe o gráfico; o alerta aparece em instantes."
        sim.clear_faults()
        return "Todas as máquinas voltando ao normal."

    # ------------------------------------------------------------ análise preditiva
    @app.callback(Output("pred-insight", "children"), Output("pred-insight", "className"), Input("pred-machine", "value"), Input("live-store", "data"))
    def insight(machine, _live):
        machine = machine or "PR-02"
        m = MACHINE_BY_ID[machine]
        d = sim.snapshot()["machines"][machine]
        st = d["status"]
        last = {v: d[SHORT[v]][-1] for v in VAR_KEYS}
        main = insights.fleet_trends()[machine]["main"]
        days = main["rul_days"] if main else None
        if st == 2:
            title, body, chip_el = insights.reason(machine, last), "A máquina já está em estado crítico. Recomenda-se ação imediata.", chip(2, "Crítico agora")
        elif main:
            word = "alta" if main["slope_per_day"] > 0 else "queda"
            title = f"{insights.label(machine, main['var'])} em {word} constante"
            body = (f"{insights.trend_text(machine)} Confiança da estimativa: {insights.confidence(main['r2'])}. "
                    f"{insights.recommendation(days)}")
            chip_el = chip(2 if days < 7 else 1, "Ação planejada" if days >= 7 else "Ação urgente")
        else:
            title, body, chip_el = "Sem sinais de degradação", "Nenhuma variável aponta para o limite crítico nos próximos 60 dias, com base nos últimos 5 dias.", chip(0, "Estável")
        sev = 2 if (st == 2 or (days is not None and days < 7)) else 1 if days is not None else 0
        big = html.Div([html.Div("Até o limite crítico", className="big-label"),
                        html.Div([fmt(days, 0), html.Small("dias")] if days is not None else "—", className="big-num")], className=f"big s{sev}")
        left = html.Div([chip_el, html.H2(title, className="insight-title"), html.P(body, className="insight-body"),
                         html.Div([html.Button("Gerar ordem de serviço", id="pred-make-wo", className="btn primary", n_clicks=0)] if (main or st) else [html.Div(id="pred-make-wo")], className="insight-actions")])
        return [left, big], "card insight"

    @app.callback(Output("pred-msg", "children"), Input("pred-make-wo", "n_clicks"), State("pred-machine", "value"), prevent_initial_call=True)
    def make_wo(n, machine):
        if not n:
            raise PreventUpdate
        d = sim.snapshot()["machines"][machine]
        main = insights.fleet_trends()[machine]["main"]
        days = main["rul_days"] if main else None
        last = {v: d[SHORT[v]][-1] for v in VAR_KEYS}
        prio = "Alta" if d["status"] == 2 or (days is not None and days < 7) else "Média"
        desc = insights.trend_text(machine) or insights.reason(machine, last)
        wo = store.create_work_order(machine, prio, "Preditiva", desc, due_days=2 if prio == "Alta" else 7)
        return f"Ordem {wo['wo_id']} criada para {machine} (prioridade {prio.lower()}). Acompanhe em Alertas › Ordens de serviço."

    @app.callback(Output("pred-title", "children"), Output("pred-graph", "figure"), Output("pred-detail", "children"),
                  Input("pred-machine", "value"), Input("pred-view", "value"), Input("pred-days", "value"), Input("theme", "data"))
    def analysis_chart(machine, view, days, theme):
        machine, view, days = machine or "PR-02", view or "vibration_mm_s", days or 14
        full = enrich(store.load_history())
        end = full["timestamp"].max()
        window = full[full["timestamp"] >= end - pd.Timedelta(days=days)]
        mdf = window[window["machine_id"] == machine]
        ruls = {v: estimate_rul(full, machine, v, days=5) for v in VAR_KEYS}
        if view in VAR_KEYS:
            an = rolling_anomalies(mdf.set_index("timestamp")[view])
            fig = trend_fig(mdf, machine, view, ruls[view], theme, an)
            title = [html.H3(f"{insights.label(machine, view)}: histórico e projeção"), html.Span("Linha pontilhada = projeção · círculos = anomalias", className="faint small")]
        elif view == "health":
            fig = health_fig(mdf, theme)
            title = [html.H3("Índice de saúde"), html.Span("0–100 · quanto menor, mais perto dos limites", className="faint small")]
        else:
            fig = compare_fig({m["machine_id"]: sim.snapshot()["machines"][m["machine_id"]]["hi"] for m in MACHINES}, machine, theme)
            title = [html.H3("Índice de saúde por máquina (agora)"), html.Span("Destaque = máquina selecionada", className="faint small")]
        rows = []
        for v in VAR_KEYS:
            r = ruls[v]
            est = "Estável (> 60 dias)" if r["rul_days"] is None or r["rul_days"] > 60 else f"≈ {fmt(r['rul_days'], 1)} dias"
            rows.append(html.Tr([html.Td(insights.label(machine, v)), html.Td(f"{fmt(r['slope_per_day'], 3)} {VAR_UNIT[v]}/dia"), html.Td(est),
                                 html.Td(f"{insights.confidence(r['r2'])} (R² {fmt(r['r2'], 2)})")]))
        detail = html.Div([
            html.P("A estimativa ajusta uma reta às médias horárias dos últimos 5 dias e a prolonga até o limite crítico. É um modelo didático: "
                   "assume tendência linear e perde precisão quando a série oscila ou tem picos (confiança baixa).", className="muted"),
            html.Table([html.Tr([html.Th("Variável"), html.Th("Tendência"), html.Th("Até o crítico"), html.Th("Confiança")])] + rows, className="kv"),
            html.P("Anomalias: pontos que se afastam da mediana móvel em mais de 3,5 desvios robustos (mediana/MAD).", className="muted small", style={"marginTop": "12px"}),
        ])
        return title, fig, detail

    # ------------------------------------------------------------ alertas e ordens
    def _alert_row(r) -> html.Div:
        lvl = 2 if r.severity == "Crítico" else 1
        m = MACHINE_BY_ID.get(r.machine_id, {"name": r.machine_id})
        meta = f"{insights.ago(r.timestamp)} · {r.status}" + (f" · {r.work_order_id}" if r.work_order_id else "")
        mk = lambda action, label, cls: html.Button(label, id={"type": "al-act", "action": action, "id": r.alert_id}, className=f"btn sm {cls}", n_clicks=0)
        acts = []
        if r.status == "Aberto":
            acts = [mk("ack", "Reconhecer", "primary")] + ([] if r.work_order_id else [mk("wo", "Criar OS", "")])
        elif r.status == "Reconhecido":
            acts = ([] if r.work_order_id else [mk("wo", "Criar OS", "primary")]) + [mk("resolve", "Resolver", "" if r.work_order_id else "")]
        return html.Div([chip(lvl), html.Div([html.Div(f"{r.machine_id} · {m['name']}", className="ltitle"), html.Div(r.message, className="lsub"), html.Div(meta, className="lmeta")], className="lmain"),
                         html.Div(acts, className="lact")], className=f"lrow{' done' if r.status == 'Resolvido' else ''}")

    def _wo_row(r) -> html.Div:
        prio = {"Alta": (2, "Alta"), "Média": (1, "Média"), "Baixa": (None, "Baixa")}.get(r.priority, (None, r.priority))
        done = r.status in ("Concluída", "Cancelada")
        mk = lambda action, label: html.Button(label, id={"type": "wo-act", "action": action, "id": r.wo_id}, className="btn sm primary", n_clicks=0)
        acts = [chip(0, r.status) if r.status == "Concluída" else chip(None, r.status, neutral=True)]
        if r.status == "Aberta":
            acts.append(mk("start", "Iniciar"))
        elif r.status == "Em andamento":
            acts.append(mk("finish", "Concluir"))
        due = pd.Timestamp(r.due_date).strftime("%d/%m")
        return html.Div([chip(*prio) if prio[0] is not None else chip(None, prio[1], neutral=True),
                         html.Div([html.Div(f"{r.wo_id} · {r.machine_id}", className="ltitle"), html.Div(r.description, className="lsub"),
                                   html.Div(f"{r.type} · {r.assigned_to} · prazo {due}", className="lmeta")], className="lmain"),
                         html.Div(acts, className="lact")], className=f"lrow{' done' if done else ''}")

    @app.callback(Output("al-list", "children"), Input("al-view", "value"), Input("al-filter", "value"), Input("al-interval", "n_intervals"), Input("al-version", "data"))
    def al_list(view, flt, _n, _v):
        if view == "wo":
            df = store.list_work_orders()
            if flt == "pending":
                df = df[~df["status"].isin(["Concluída", "Cancelada"])]
            elif flt == "done":
                df = df[df["status"].isin(["Concluída", "Cancelada"])]
            rows = [_wo_row(r) for r in df.head(60).itertuples()]
            empty = ("Nenhuma ordem de serviço aqui", "Crie uma a partir de um alerta ou pela análise preditiva.")
        else:
            df = store.list_alerts()
            if flt == "pending":
                df = df[df["status"] != "Resolvido"]
            elif flt == "done":
                df = df[df["status"] == "Resolvido"]
            rows = [_alert_row(r) for r in df.head(60).itertuples()]
            empty = ("Nenhum alerta pendente", "Quando uma leitura passar do limite, o alerta aparece aqui.")
        return rows or html.Div([html.B(empty[0]), empty[1]], className="empty")

    @app.callback(Output("al-msg", "children"), Output("al-version", "data"),
                  Input({"type": "al-act", "action": ALL, "id": ALL}, "n_clicks"), Input({"type": "wo-act", "action": ALL, "id": ALL}, "n_clicks"),
                  Input("new-create", "n_clicks"), State("new-machine", "value"), State("new-type", "value"), State("new-prio", "value"), State("new-desc", "value"),
                  State("al-version", "data"), prevent_initial_call=True)
    def actions(_a, _w, _n, nm, nt, np_, nd, version):
        trig = callback_context.triggered_id
        if not callback_context.triggered or not callback_context.triggered[0]["value"]:
            raise PreventUpdate
        bump = (version or 0) + 1
        if trig == "new-create":
            if not (nd or "").strip():
                return "Informe a descrição da ordem.", no_update
            wo = store.create_work_order(nm, np_, nt, nd.strip())
            return f"Ordem {wo['wo_id']} criada para {nm}.", bump
        if not isinstance(trig, dict):
            raise PreventUpdate
        act, rid = trig["action"], trig["id"]
        if act == "ack":
            store.set_alert_status([rid], "Reconhecido")
            return f"Alerta {rid} reconhecido.", bump
        if act == "resolve":
            store.set_alert_status([rid], "Resolvido")
            return f"Alerta {rid} resolvido.", bump
        if act == "wo":
            row = store.list_alerts().query("alert_id == @rid").iloc[0]
            prio = "Alta" if row["severity"] == "Crítico" else "Média"
            wo = store.create_work_order(row["machine_id"], prio, "Preditiva", row["message"], alert_id=rid, due_days=1 if prio == "Alta" else 3)
            store.set_alert_status([rid], "Reconhecido")
            return f"Ordem {wo['wo_id']} criada a partir do alerta {rid}.", bump
        if act in ("start", "finish"):
            status = "Em andamento" if act == "start" else "Concluída"
            store.set_work_order_status([rid], status)
            return f"{rid}: {status.lower()}.", bump
        raise PreventUpdate

    @app.callback(Output("dl-file", "data"), Input("al-dl-btn", "n_clicks"), State("al-view", "value"), prevent_initial_call=True)
    def download(_n, view):
        if view == "wo":
            return dcc.send_data_frame(store.list_work_orders().to_csv, "ordens_de_servico.csv", index=False)
        return dcc.send_data_frame(store.list_alerts().to_csv, "alertas.csv", index=False)

    # ------------------------------------------------------------ sobre
    @app.callback(Output("sobre-body", "children"), Input("sobre-tab", "value"))
    def sobre(tab):
        return diagnostic.tab(tab or "ux", sim)

    return app, sim
