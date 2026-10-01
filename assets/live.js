/* Cliente WebSocket: recebe os "ticks" de telemetria empurrados pelo servidor (/ws) e publica
   um pequeno marcador no dcc.Store "live-store"; os callbacks do Dash reagem a ele.
   Reconecta automaticamente com backoff exponencial. */
(function () {
  let retry = 0, n = 0;

  function ready() {
    return window.dash_clientside && window.dash_clientside.set_props && document.getElementById("ws-indicator");
  }
  function indicator(kind, text) {
    try { window.dash_clientside.set_props("ws-indicator", { className: "ws-indicator " + kind, children: text }); } catch (e) {}
  }
  function publish(data) {
    try { window.dash_clientside.set_props("live-store", { data: data }); } catch (e) {}
  }
  function connect() {
    if (!ready()) { setTimeout(connect, 300); return; }
    indicator("connecting", "Conectando…");
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(proto + "://" + location.host + "/ws");
    ws.onopen = () => { retry = 0; indicator("on", "Tempo real"); };
    ws.onmessage = (ev) => {
      try {
        const d = JSON.parse(ev.data);
        if (d.type !== "tick") return;
        n += 1;
        publish({ n: n, ts: d.ts, bytes: ev.data.length, alerts: (d.alerts || []).length });
      } catch (e) { console.error(e); }
    };
    ws.onclose = () => { indicator("off", "Reconectando…"); setTimeout(connect, Math.min(10000, 1000 * Math.pow(2, retry++))); };
    ws.onerror = () => ws.close();
  }
  window.addEventListener("load", connect);
})();
