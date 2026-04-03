"""Local HTML rendering for the Build-10 technical dashboard."""

from __future__ import annotations

from html import escape

from ui.contracts import DashboardCard, DashboardSection


def _status_class(status: str) -> str:
    return {
        "healthy": "status-healthy",
        "warning": "status-warning",
        "critical": "status-critical",
        "planned": "status-planned",
    }.get(status, "status-info")


def _render_card(card: DashboardCard) -> str:
    detail = f"<p class='card-detail'>{escape(card.detail)}</p>" if card.detail else ""
    return (
        f"<article class='card {_status_class(card.status)}'>"
        f"<header><span class='card-label'>{escape(card.label)}</span>"
        f"<span class='card-status'>{escape(card.status)}</span></header>"
        f"<p class='card-value'>{escape(card.value)}</p>"
        f"{detail}"
        f"</article>"
    )


def _render_section(section: DashboardSection) -> str:
    cards = "".join(_render_card(card) for card in section.cards)
    return (
        f"<section class='section'>"
        f"<h2>{escape(section.title)}</h2>"
        f"<div class='card-grid'>{cards}</div>"
        f"</section>"
    )


def _render_list(title: str, values: tuple[str, ...]) -> str:
    if not values:
        return ""
    items = "".join(f"<li>{escape(value)}</li>" for value in values)
    return f"<section class='section'><h2>{escape(title)}</h2><ul class='bullet-list'>{items}</ul></section>"


def _render_code_block(title: str, body: str) -> str:
    if not body:
        return ""
    return (
        "<details class='details-block'>"
        f"<summary>{escape(title)}</summary>"
        f"<pre>{escape(body)}</pre>"
        "</details>"
    )


def _render_market_lab() -> str:
    return """
    <section class="section market-lab">
      <h2>Live Market Lab</h2>
      <p class="market-lab-note">
        Public Binance streams only. Pair and timeframe can be changed locally from this HTML page.
      </p>
      <div class="market-lab-controls">
        <label>
          <span>Pair</span>
          <select id="market-lab-pair">
            <option value="BTCUSDT">BTCUSDT</option>
            <option value="ETHUSDT">ETHUSDT</option>
          </select>
        </label>
        <label>
          <span>Timeframe</span>
          <select id="market-lab-timeframe">
            <option value="15m">15m</option>
            <option value="1h">1h</option>
            <option value="4h">4h</option>
            <option value="1d">1d</option>
          </select>
        </label>
        <label>
          <span>View</span>
          <select id="market-lab-view">
            <option value="candles">Candles</option>
            <option value="line">Line</option>
          </select>
        </label>
        <button id="market-lab-reload" type="button">Reload</button>
      </div>
      <div class="market-lab-status">
        <div id="market-lab-connection">Disconnected</div>
        <div id="market-lab-summary">No market data loaded yet.</div>
      </div>
      <svg id="market-lab-chart" viewBox="0 0 960 360" role="img" aria-label="Live market chart"></svg>
    </section>
    """


def _render_market_lab_script() -> str:
    return """
  <script>
    (() => {
      const pairSelect = document.getElementById("market-lab-pair");
      const timeframeSelect = document.getElementById("market-lab-timeframe");
      const viewSelect = document.getElementById("market-lab-view");
      const reloadButton = document.getElementById("market-lab-reload");
      const connectionEl = document.getElementById("market-lab-connection");
      const summaryEl = document.getElementById("market-lab-summary");
      const chartEl = document.getElementById("market-lab-chart");
      if (!pairSelect || !timeframeSelect || !viewSelect || !reloadButton || !connectionEl || !summaryEl || !chartEl) {
        return;
      }

      const state = {
        socket: null,
        candles: [],
        pair: pairSelect.value,
        timeframe: timeframeSelect.value,
        view: viewSelect.value,
      };

      const MAX_CANDLES = 96;
      const SVG_WIDTH = 960;
      const SVG_HEIGHT = 360;
      const PAD_LEFT = 56;
      const PAD_RIGHT = 20;
      const PAD_TOP = 20;
      const PAD_BOTTOM = 34;

      function setConnection(text, tone = "info") {
        connectionEl.textContent = text;
        connectionEl.dataset.tone = tone;
      }

      function setSummary(text) {
        summaryEl.textContent = text;
      }

      function escapeHtml(value) {
        return String(value)
          .replaceAll("&", "&amp;")
          .replaceAll("<", "&lt;")
          .replaceAll(">", "&gt;");
      }

      function yForPrice(price, minPrice, maxPrice) {
        const innerHeight = SVG_HEIGHT - PAD_TOP - PAD_BOTTOM;
        if (maxPrice <= minPrice) {
          return PAD_TOP + innerHeight / 2;
        }
        const ratio = (price - minPrice) / (maxPrice - minPrice);
        return PAD_TOP + innerHeight - ratio * innerHeight;
      }

      function xForIndex(index, count) {
        const innerWidth = SVG_WIDTH - PAD_LEFT - PAD_RIGHT;
        if (count <= 1) {
          return PAD_LEFT + innerWidth / 2;
        }
        return PAD_LEFT + (innerWidth * index) / (count - 1);
      }

      function drawChart() {
        const candles = state.candles.slice(-MAX_CANDLES);
        if (!candles.length) {
          chartEl.innerHTML = "<text x='40' y='56' fill='#5a6872' font-size='16'>Waiting for public Binance market data...</text>";
          return;
        }

        const highs = candles.map(item => item.high);
        const lows = candles.map(item => item.low);
        const minPrice = Math.min(...lows);
        const maxPrice = Math.max(...highs);
        const first = candles[0];
        const last = candles[candles.length - 1];
        const priceLabels = [maxPrice, (maxPrice + minPrice) / 2, minPrice];

        let body = "";
        body += `<rect x='0' y='0' width='${SVG_WIDTH}' height='${SVG_HEIGHT}' rx='14' fill='#f8fbfd' stroke='#d5dde5'></rect>`;
        body += `<line x1='${PAD_LEFT}' y1='${SVG_HEIGHT - PAD_BOTTOM}' x2='${SVG_WIDTH - PAD_RIGHT}' y2='${SVG_HEIGHT - PAD_BOTTOM}' stroke='#b8c4cf' stroke-width='1'></line>`;
        body += `<line x1='${PAD_LEFT}' y1='${PAD_TOP}' x2='${PAD_LEFT}' y2='${SVG_HEIGHT - PAD_BOTTOM}' stroke='#b8c4cf' stroke-width='1'></line>`;

        for (const label of priceLabels) {
          const y = yForPrice(label, minPrice, maxPrice);
          body += `<line x1='${PAD_LEFT}' y1='${y}' x2='${SVG_WIDTH - PAD_RIGHT}' y2='${y}' stroke='#e2e9f0' stroke-dasharray='4 4'></line>`;
          body += `<text x='10' y='${y + 4}' fill='#5a6872' font-size='12'>${label.toFixed(2)}</text>`;
        }

        if (state.view === "line") {
          const points = candles.map((item, index) => {
            return `${xForIndex(index, candles.length)},${yForPrice(item.close, minPrice, maxPrice)}`;
          }).join(" ");
          body += `<polyline fill='none' stroke='#2f7de1' stroke-width='2.5' points='${points}'></polyline>`;
        } else {
          const innerWidth = SVG_WIDTH - PAD_LEFT - PAD_RIGHT;
          const candleWidth = Math.max(5, Math.min(14, innerWidth / Math.max(candles.length, 24) - 2));
          candles.forEach((item, index) => {
            const x = xForIndex(index, candles.length);
            const openY = yForPrice(item.open, minPrice, maxPrice);
            const closeY = yForPrice(item.close, minPrice, maxPrice);
            const highY = yForPrice(item.high, minPrice, maxPrice);
            const lowY = yForPrice(item.low, minPrice, maxPrice);
            const top = Math.min(openY, closeY);
            const height = Math.max(2, Math.abs(closeY - openY));
            const color = item.close >= item.open ? "#2f9b63" : "#c44141";
            body += `<line x1='${x}' y1='${highY}' x2='${x}' y2='${lowY}' stroke='${color}' stroke-width='1.5'></line>`;
            body += `<rect x='${x - candleWidth / 2}' y='${top}' width='${candleWidth}' height='${height}' rx='1.5' fill='${color}' opacity='0.88'></rect>`;
          });
        }

        body += `<text x='${PAD_LEFT}' y='${SVG_HEIGHT - 10}' fill='#5a6872' font-size='12'>${escapeHtml(first.label)} -> ${escapeHtml(last.label)}</text>`;
        chartEl.innerHTML = body;

        const direction = last.close >= first.open ? "up" : "down";
        setSummary(
          `${state.pair} ${state.timeframe} / ${candles.length} candles / last close ${last.close.toFixed(2)} / range ${minPrice.toFixed(2)}-${maxPrice.toFixed(2)} / trend ${direction}`
        );
      }

      function normalizeHistoryRow(row) {
        return {
          openTime: Number(row[0]),
          label: new Date(Number(row[0])).toLocaleString(),
          open: Number(row[1]),
          high: Number(row[2]),
          low: Number(row[3]),
          close: Number(row[4]),
          volume: Number(row[5]),
          closeTime: Number(row[6]),
          isClosed: true,
        };
      }

      function normalizeSocketPayload(payload) {
        const k = payload && payload.k;
        if (!k) {
          return null;
        }
        return {
          openTime: Number(k.t),
          label: new Date(Number(k.t)).toLocaleString(),
          open: Number(k.o),
          high: Number(k.h),
          low: Number(k.l),
          close: Number(k.c),
          volume: Number(k.v),
          closeTime: Number(k.T),
          isClosed: Boolean(k.x),
        };
      }

      function upsertCandle(candle) {
        const existingIndex = state.candles.findIndex(item => item.openTime === candle.openTime);
        if (existingIndex >= 0) {
          state.candles.splice(existingIndex, 1, candle);
        } else {
          state.candles.push(candle);
          state.candles.sort((left, right) => left.openTime - right.openTime);
          if (state.candles.length > MAX_CANDLES) {
            state.candles = state.candles.slice(-MAX_CANDLES);
          }
        }
      }

      async function loadHistory() {
        const url = `https://api.binance.com/api/v3/klines?symbol=${state.pair}&interval=${state.timeframe}&limit=${MAX_CANDLES}`;
        const response = await fetch(url, { mode: "cors" });
        if (!response.ok) {
          throw new Error(`history_http_${response.status}`);
        }
        const rows = await response.json();
        if (!Array.isArray(rows)) {
          throw new Error("history_payload_invalid");
        }
        state.candles = rows.map(normalizeHistoryRow);
        drawChart();
      }

      function connectSocket() {
        if (state.socket) {
          state.socket.close();
          state.socket = null;
        }
        const stream = `${state.pair.toLowerCase()}@kline_${state.timeframe}`;
        const endpoint = `wss://stream.binance.com:9443/ws/${stream}`;
        const socket = new WebSocket(endpoint);
        state.socket = socket;
        setConnection(`Connecting: ${stream}`, "warning");

        socket.addEventListener("open", () => {
          setConnection(`Connected: ${stream}`, "healthy");
        });

        socket.addEventListener("message", event => {
          try {
            const payload = JSON.parse(event.data);
            const candle = normalizeSocketPayload(payload);
            if (!candle) {
              return;
            }
            upsertCandle(candle);
            drawChart();
          } catch (error) {
            setConnection(`Stream parse error: ${String(error)}`, "critical");
          }
        });

        socket.addEventListener("error", () => {
          setConnection(`WebSocket error on ${stream}`, "critical");
        });

        socket.addEventListener("close", () => {
          if (state.socket === socket) {
            setConnection(`Disconnected: ${stream}`, "warning");
          }
        });
      }

      async function reloadMarketLab() {
        state.pair = pairSelect.value;
        state.timeframe = timeframeSelect.value;
        state.view = viewSelect.value;
        setConnection("Loading public Binance history...", "warning");
        setSummary("Refreshing local chart...");
        chartEl.innerHTML = "";
        try {
          await loadHistory();
          connectSocket();
        } catch (error) {
          setConnection(`Public Binance load failed: ${String(error)}`, "critical");
          chartEl.innerHTML = "<text x='40' y='56' fill='#c44141' font-size='16'>Unable to load public Binance history for the selected pair/timeframe.</text>";
          setSummary("No chart available.");
        }
      }

      reloadButton.addEventListener("click", () => {
        reloadMarketLab();
      });
      pairSelect.addEventListener("change", () => {
        reloadMarketLab();
      });
      timeframeSelect.addEventListener("change", () => {
        reloadMarketLab();
      });
      viewSelect.addEventListener("change", () => {
        state.view = viewSelect.value;
        drawChart();
      });

      reloadMarketLab();
    })();
  </script>
    """


def render_technical_dashboard_html(
    *,
    title: str,
    generated_at: str,
    source_mode: str,
    source_note: str,
    sections: tuple[DashboardSection, ...],
    future_panels: tuple[str, ...] = (),
    footer_notes: tuple[str, ...] = (),
    observability_text: str = "",
    raw_payload_json: str = "",
    raw_view_json: str = "",
) -> str:
    """Render a local static HTML page for the technical dashboard."""

    rendered_sections = "".join(_render_section(section) for section in sections)
    future_section = _render_list("Future Panels", future_panels)
    footer_section = _render_list("Notes", footer_notes)
    observability_block = _render_code_block("Observability Export", observability_text)
    payload_block = _render_code_block("Raw Technical Payload", raw_payload_json)
    view_block = _render_code_block("Raw Technical View", raw_view_json)
    market_lab = _render_market_lab()
    market_lab_script = _render_market_lab_script()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f4f6f8;
      --panel: #ffffff;
      --text: #1e2933;
      --muted: #5a6872;
      --border: #d5dde5;
      --healthy: #dff6e8;
      --healthy-border: #3fa76b;
      --warning: #fff1d6;
      --warning-border: #c58b19;
      --critical: #ffe0e0;
      --critical-border: #c44141;
      --info: #e4eefc;
      --info-border: #4a7fd1;
      --planned: #ededed;
      --planned-border: #7c8590;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", Tahoma, sans-serif;
      background: linear-gradient(180deg, #eef3f7 0%, var(--bg) 160px);
      color: var(--text);
    }}
    main {{
      max-width: 1280px;
      margin: 0 auto;
      padding: 24px;
    }}
    .hero, .section, .details-block {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 14px;
      box-shadow: 0 10px 26px rgba(25, 39, 52, 0.05);
    }}
    .hero {{
      padding: 24px;
      margin-bottom: 20px;
    }}
    .hero h1 {{
      margin: 0 0 8px;
      font-size: 28px;
    }}
    .hero-meta {{
      display: grid;
      gap: 6px;
      color: var(--muted);
      font-size: 14px;
    }}
    .hero-note {{
      margin-top: 14px;
      padding: 12px 14px;
      border-radius: 10px;
      background: #f8fbfd;
      border: 1px solid #dfe8ef;
    }}
    .section {{
      padding: 18px;
      margin-bottom: 18px;
    }}
    .section h2 {{
      margin: 0 0 14px;
      font-size: 18px;
    }}
    .card-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
    }}
    .card {{
      border-radius: 12px;
      border: 1px solid var(--border);
      padding: 14px;
      min-height: 128px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}
    .card header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--muted);
    }}
    .card-label {{
      font-weight: 700;
    }}
    .card-status {{
      font-weight: 700;
    }}
    .card-value {{
      margin: 0;
      font-size: 22px;
      font-weight: 700;
      line-height: 1.25;
      word-break: break-word;
    }}
    .card-detail {{
      margin: 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
      white-space: pre-wrap;
    }}
    .status-healthy {{
      background: var(--healthy);
      border-color: var(--healthy-border);
    }}
    .status-warning {{
      background: var(--warning);
      border-color: var(--warning-border);
    }}
    .status-critical {{
      background: var(--critical);
      border-color: var(--critical-border);
    }}
    .status-info {{
      background: var(--info);
      border-color: var(--info-border);
    }}
    .status-planned {{
      background: var(--planned);
      border-color: var(--planned-border);
    }}
    .bullet-list {{
      margin: 0;
      padding-left: 20px;
      color: var(--muted);
    }}
    .details-block {{
      margin-bottom: 18px;
      overflow: hidden;
    }}
    .details-block summary {{
      cursor: pointer;
      padding: 14px 18px;
      font-weight: 700;
      background: #f7fafc;
    }}
    .details-block pre {{
      margin: 0;
      padding: 16px 18px;
      overflow-x: auto;
      background: #10171f;
      color: #edf3fb;
      font-size: 13px;
      line-height: 1.5;
    }}
    .market-lab-note {{
      margin: 0 0 16px;
      color: var(--muted);
      font-size: 14px;
    }}
    .market-lab-controls {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      align-items: end;
      margin-bottom: 16px;
    }}
    .market-lab-controls label {{
      display: grid;
      gap: 6px;
      font-size: 13px;
      color: var(--muted);
    }}
    .market-lab-controls select,
    .market-lab-controls button {{
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 10px 12px;
      font: inherit;
      background: #fff;
      color: var(--text);
    }}
    .market-lab-controls button {{
      cursor: pointer;
      font-weight: 700;
      background: #e4eefc;
      border-color: #4a7fd1;
    }}
    .market-lab-status {{
      display: grid;
      gap: 6px;
      margin-bottom: 16px;
      color: var(--muted);
      font-size: 13px;
    }}
    #market-lab-connection[data-tone="healthy"] {{ color: #1f7a4d; }}
    #market-lab-connection[data-tone="warning"] {{ color: #9a6700; }}
    #market-lab-connection[data-tone="critical"] {{ color: #b42318; }}
    #market-lab-chart {{
      width: 100%;
      min-height: 360px;
      border: 1px solid var(--border);
      border-radius: 14px;
      background: linear-gradient(180deg, #ffffff 0%, #f7fafc 100%);
    }}
    @media (max-width: 720px) {{
      main {{ padding: 16px; }}
      .hero {{ padding: 18px; }}
      .card-value {{ font-size: 18px; }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h1>{escape(title)}</h1>
      <div class="hero-meta">
        <div><strong>Generated at:</strong> {escape(generated_at)}</div>
        <div><strong>Source mode:</strong> {escape(source_mode)}</div>
      </div>
      <p class="hero-note">{escape(source_note)}</p>
    </section>
    {market_lab}
    {rendered_sections}
    {future_section}
    {observability_block}
    {payload_block}
    {view_block}
    {footer_section}
  </main>
  {market_lab_script}
</body>
</html>
"""


__all__ = [
    "render_technical_dashboard_html",
]
