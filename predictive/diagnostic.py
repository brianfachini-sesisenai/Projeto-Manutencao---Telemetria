"""Conteúdo da página 'Sobre o projeto' (apoio ao relatório), com medições reais do protótipo."""
from __future__ import annotations

import json
import time

import pandas as pd
from dash import html

from .analytics import enrich
from .config import HISTORY_FILE, LIVE_FILE, MACHINES, TICK_SECONDS
from .figs import fmt, live_fig


def _ul(items):
    return html.Ul([html.Li(i) for i in items])


def _table(head, rows):
    return html.Table([html.Tr([html.Th(h) for h in head])] + [html.Tr([html.Td(c) for c in r]) for r in rows], className="kv")


def measurements(sim) -> dict:
    t0 = time.perf_counter()
    df = pd.read_csv(HISTORY_FILE, parse_dates=["timestamp"])
    t_csv = (time.perf_counter() - t0) * 1000
    t0 = time.perf_counter()
    enrich(df)
    t_enrich = (time.perf_counter() - t0) * 1000
    snap = sim.snapshot()
    d = snap["machines"][MACHINES[0]["machine_id"]]
    t0 = time.perf_counter()
    live_fig(MACHINES[0], "vibration_mm_s", d["t"], d["vib"], "light", 0)
    t_fig = (time.perf_counter() - t0) * 1000
    return {"rows": len(df), "kb": HISTORY_FILE.stat().st_size / 1024, "t_csv": t_csv, "t_enrich": t_enrich, "t_fig": t_fig,
            "tick_kb": sim.last_payload_bytes / 1024, "snap_kb": len(json.dumps(snap).encode()) / 1024,
            "live_rows": max(0, sum(1 for _ in open(LIVE_FILE)) - 1) if LIVE_FILE.exists() else 0,
            "live_kb": LIVE_FILE.stat().st_size / 1024 if LIVE_FILE.exists() else 0}


def tab(name: str, sim):
    if name == "ux":
        rows = [
            ("Hierarquia visual", "Três níveis tipográficos: título da página (28 px), seção em caixa-alta discreta, corpo. O número mais importante de cada tela é o maior (ex.: estado da planta, RUL).", "Todas"),
            ("Proximidade e região comum", "Informações da mesma máquina ficam no mesmo cartão; espaçamento maior entre seções do que dentro delas.", "Visão geral"),
            ("Similaridade", "Estado sempre no mesmo componente (chip) e mesma lógica de cor; variáveis sempre na mesma ordem.", "Todas"),
            ("Continuidade e alinhamento", "Tabela de máquinas em colunas alinhadas; leitura em varredura vertical.", "Visão geral"),
            ("Figura-fundo", "Cartões brancos sobre fundo neutro; nos gráficos, a série em primeiro plano e as zonas de limite como fundo translúcido.", "Gráficos"),
            ("Carga cognitiva e revelação progressiva", "Uma pergunta por tela; uma variável por gráfico; detalhes técnicos e simulador ficam em blocos recolhidos.", "Todas"),
            ("Cor acessível", "Estado = cor + forma (círculo, triângulo, quadrado) + texto; contraste calculado: texto ≥ 4,5:1 e elementos gráficos ≥ 3:1 (exceto o âmbar no tema claro, compensado por forma e rótulo). Cor de destaque única (azul) nos gráficos.", "Todas"),
            ("Ajuda contextual (tooltips)", "Ícone “i” ao lado de termos técnicos (saúde, RUL, confiança, zonas) explica o significado ao passar o mouse ou focar com o teclado; botões de ação têm dica do que fazem.", "Todas"),
            ("Feedback do sistema", "Indicador de conexão em tempo real, notificação de novo alerta e mensagens após cada ação.", "Cabeçalho"),
        ]
        return html.Div(_table(["Princípio", "Como foi aplicado", "Onde"], rows), className="card card-pad prose")
    if name == "diag":
        return html.Div([
            html.Div([html.H3("Falhas de usabilidade"), _ul([
                "Sem filtro por turno/linha: o engenheiro vê todas as máquinas, inclusive as que não são de sua responsabilidade.",
                "Limites fixos no código; o usuário não consegue ajustá-los por máquina.",
                "O índice de saúde é uma métrica própria e precisa ser explicada (há um bloco de detalhes na análise, mas falta tooltip nos cartões).",
                "Sem perfis de usuário, autenticação ou trilha de auditoria nas ordens de serviço.",
            ])], className="card card-pad prose"),
            html.Div([html.H3("Gargalos de performance"), _ul([
                "Cada tick reconstrói as figuras no servidor: não escala para muitas máquinas/usuários.",
                "CSV como banco: leitura completa a cada consulta e regravação integral de alertas/OS; sem concorrência entre processos.",
                "Estado do simulador na memória de um único processo (não funciona com vários workers).",
                "Servidor de desenvolvimento do Flask: aceitável para a demonstração, não para produção.",
            ])], className="card card-pad prose"),
            html.Div([html.H3("Oportunidades de melhoria"), _ul([
                "Substituir CSV por banco de séries temporais (TimescaleDB/InfluxDB) e ingestão real via MQTT/OPC UA.",
                "Atualizar o gráfico no navegador só com o ponto novo (extendData) e usar downsampling em janelas longas.",
                "Trocar a regressão linear por modelos de degradação (exponencial, filtro de Kalman) e validar com falhas reais.",
                "Servir com gunicorn + gevent e Redis pub/sub para escalar o WebSocket.",
            ])], className="card card-pad prose"),
        ], className="three")
    if name == "tech":
        rows = [
            ("Dash + Plotly (usado)", "Tudo em Python; callbacks reativos; gráficos interativos; integra com pandas.", "Cada interação passa pelo servidor; menos controle fino do visual.", "Dashboards analíticos com times de dados/engenharia."),
            ("D3.js", "Controle total do visual; desempenho excelente.", "Curva de aprendizado alta; muito código.", "Visualizações customizadas."),
            ("Chart.js", "Leve e simples para gráficos padrão.", "Menos recursos analíticos nativos (zoom, subplots).", "Painéis simples embutidos em páginas web."),
            ("Streamlit", "Prototipagem muito rápida.", "Reexecuta o script a cada interação; layout menos flexível.", "Exploração e protótipos internos."),
            ("Power BI / Tableau", "Autosserviço, governança, conectores corporativos.", "Tempo real limitado; custo de licença; menos customização.", "BI corporativo e relatórios gerenciais."),
        ]
        return html.Div(_table(["Opção", "Pontos fortes", "Limitações", "Quando usar"], rows), className="card card-pad prose")
    if name == "arch":
        return html.Div([
            html.P([html.Span("Simulador", className="tag"), "  gera leituras (carga, desgaste, falhas)  →  ", html.Span("CSV", className="tag"),
                    "  histórico, alertas e ordens  →  ", html.Span("Flask + WebSocket", className="tag"), "  empurra cada leitura  →  ", html.Span("Dash/Plotly", className="tag"),
                    "  desenha a interface."]),
            _ul(["API REST de sensores: /api/sensors, /api/history?machine=PR-01, /api/snapshot, /api/health.",
                 "Alertas: detector com debounce (3 leituras consecutivas) e histerese de liberação (8 leituras).",
                 "RUL: regressão linear das médias horárias dos últimos 5 dias, extrapolada até o limite crítico; mostra R² como confiança.",
                 "Persistência: CSV com lock de processo; histórico em cache por data de modificação."])], className="card card-pad prose")
    m = measurements(sim)
    rows = [("Histórico em CSV", f"{m['rows']:,} linhas · {fmt(m['kb'], 0)} KB".replace(",", ".")),
            ("Leitura do CSV (pandas)", f"{fmt(m['t_csv'], 0)} ms"), ("Status + índice de saúde (vetorizado)", f"{fmt(m['t_enrich'], 0)} ms"),
            ("Montagem de uma figura de telemetria", f"{fmt(m['t_fig'], 0)} ms"),
            (f"Pacote do WebSocket (1 tick a cada {TICK_SECONDS:g} s)", f"{fmt(m['tick_kb'], 1)} KB"),
            ("Snapshot completo (equivalente a polling)", f"{fmt(m['snap_kb'], 0)} KB"),
            ("Telemetria ao vivo gravada nesta sessão", f"{m['live_rows']:,} linhas · {fmt(m['live_kb'], 0)} KB".replace(",", "."))]
    return html.Div(_table(["Métrica", "Valor (medido agora)"], rows), className="card card-pad prose")
