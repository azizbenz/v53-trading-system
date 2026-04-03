"""Local HTML rendering for the Build-10 technical dashboard."""

from __future__ import annotations

from html import escape

from ui.contracts import DashboardCard, DashboardSection


def _slugify(value: str) -> str:
    slug: list[str] = []
    last_was_dash = False
    for character in value.lower():
        if character.isalnum():
            slug.append(character)
            last_was_dash = False
            continue
        if not last_was_dash:
            slug.append("-")
            last_was_dash = True
    return "".join(slug).strip("-")


def _status_class(status: str) -> str:
    return {
        "healthy": "status-healthy",
        "warning": "status-warning",
        "critical": "status-critical",
        "planned": "status-planned",
    }.get(status, "status-info")


def _render_card(card: DashboardCard) -> str:
    detail = f"<p class='card-detail' data-card-detail>{escape(card.detail)}</p>" if card.detail else ""
    return (
        f"<article class='card {_status_class(card.status)}' data-card-key='{escape(card.key)}'>"
        f"<header><span class='card-label' data-card-label>{escape(card.label)}</span>"
        f"<span class='card-status' data-card-status>{escape(card.status)}</span></header>"
        f"<p class='card-value' data-card-value>{escape(card.value)}</p>"
        f"{detail}"
        f"</article>"
    )


def _render_section(section: DashboardSection) -> str:
    cards = "".join(_render_card(card) for card in section.cards)
    section_key = _slugify(section.title)
    return (
        f"<section class='section' id='section-{section_key}' data-section-key='{section_key}'>"
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
    block_key = _slugify(title)
    return (
        f"<details class='details-block' id='detail-{block_key}'>"
        f"<summary>{escape(title)}</summary>"
        f"<pre>{escape(body)}</pre>"
        "</details>"
    )


def _render_panel_navigation(future_panels: tuple[str, ...]) -> str:
    if not future_panels:
        return ""
    specs = {
        "technical_supervision": (
            "Technical Supervision",
            "Live sections: System, Portfolio, Pairs, Engines, Risk, Execution, Data & Infra, Alerts.",
            "#section-system",
        ),
        "build9x_diagnostics": (
            "Build-9X Diagnostics",
            "Governed diagnostics, hypotheses, replay candidates, capacity and backpressure.",
            "#section-build-9x",
        ),
        "shadow_supervision": (
            "Build-11 Shadow",
            "Shadow 30-day gate, divergences, component verdicts and blocking reasons.",
            "#section-build-11-shadow",
        ),
        "micro_live_supervision": (
            "Build-12 Micro-live",
            "Probe gating, budget, guardrails and operator safing surface.",
            "#section-build-12-micro-live",
        ),
        "live_light_supervision": (
            "Build-13 Live-Light",
            "Execution gating, readiness, Build-14 influence and operator safing surface.",
            "#section-build-13-live-light",
        ),
        "build14_supervision": (
            "Build-14 Enablers",
            "Reader-level Build-14 evidence and governed influence mode.",
            "#section-build-14-enablers",
        ),
        "artifact_import": (
            "Replay & Import",
            "Artifact manifest, lineage and import validation state.",
            "#section-replay-import",
        ),
        "observability_export": (
            "Observability Export",
            "Metrics and export detail rendered from the active dashboard payload.",
            "#detail-observability-export",
        ),
    }
    cards: list[str] = []
    for panel in future_panels:
        label, detail, target = specs.get(
            panel,
            (panel, "Panel declared in payload but not mapped to a dashboard anchor yet.", "#"),
        )
        cards.append(
            "<article class='panel-nav-card'>"
            f"<header><span class='panel-nav-label'>{escape(panel)}</span></header>"
            f"<p class='panel-nav-value'>{escape(label)}</p>"
            f"<p class='panel-nav-detail'>{escape(detail)}</p>"
            f"<a class='panel-nav-link' href='{escape(target)}'>Open panel</a>"
            "</article>"
        )
    return (
        "<section class='section panel-nav' id='section-future-panels'>"
        "<h2>Future Panels</h2>"
        "<div class='panel-nav-grid'>"
        + "".join(cards)
        + "</div></section>"
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
            <option value="1m">1m</option>
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
        <div id="market-lab-liquidity">No liquidity data loaded yet.</div>
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
      const liquidityEl = document.getElementById("market-lab-liquidity");
      const chartEl = document.getElementById("market-lab-chart");
      if (!pairSelect || !timeframeSelect || !viewSelect || !reloadButton || !connectionEl || !summaryEl || !liquidityEl || !chartEl) {
        return;
      }

      const state = {
        socket: null,
        candles: [],
        pair: pairSelect.value,
        timeframe: timeframeSelect.value,
        view: viewSelect.value,
        lastBookTicker: null,
        lastDepth: null,
      };

      const MAX_CANDLES = 96;
      const SVG_WIDTH = 960;
      const SVG_HEIGHT = 360;
      const PAD_LEFT = 56;
      const PAD_RIGHT = 20;
      const PAD_TOP = 20;
      const PAD_BOTTOM = 34;
      const LIVE_PAIRS = ["BTCUSDT", "ETHUSDT"];
      const FRESHNESS_WARNING_MS = 9500;
      const STATUS_CLASS_MAP = {
        healthy: "status-healthy",
        warning: "status-warning",
        critical: "status-critical",
        planned: "status-planned",
        info: "status-info",
      };
      const bridge = {
        socket: null,
        reconnectCount: 0,
        staleSpikeCount: 0,
        lastStalePairs: [],
        pairs: Object.fromEntries(
          LIVE_PAIRS.map(pair => [
            pair,
            {
              lastUpdateMs: 0,
              bestBid: null,
              bestAsk: null,
              bidQty: null,
              askQty: null,
              lastUpdateId: null,
              spreadSamples: [],
              sources: new Set(),
            },
          ])
        ),
      };

      function statusClass(status) {
        return STATUS_CLASS_MAP[status] || STATUS_CLASS_MAP.info;
      }

      function setConnection(text, tone = "info") {
        connectionEl.textContent = text;
        connectionEl.dataset.tone = tone;
      }

      function setSummary(text) {
        summaryEl.textContent = text;
      }

      function setLiquidity(text) {
        liquidityEl.textContent = text;
      }

      function escapeHtml(value) {
        return String(value)
          .replaceAll("&", "&amp;")
          .replaceAll("<", "&lt;")
          .replaceAll(">", "&gt;");
      }

      function cardNodes(key) {
        const article = document.querySelector(`[data-card-key="${key}"]`);
        if (!article) {
          return null;
        }
        return {
          article,
          label: article.querySelector("[data-card-label]"),
          status: article.querySelector("[data-card-status]"),
          value: article.querySelector("[data-card-value]"),
          detail: article.querySelector("[data-card-detail]"),
        };
      }

      function ensureSectionGrid(sectionKey) {
        return document.querySelector(`[data-section-key="${sectionKey}"] .card-grid`);
      }

      function ensureCard(sectionKey, key, label) {
        let nodes = cardNodes(key);
        if (nodes) {
          return nodes;
        }
        const grid = ensureSectionGrid(sectionKey);
        if (!grid) {
          return null;
        }
        const existingEmpty = grid.querySelector('[data-card-key="pairs_empty"]');
        if (existingEmpty && sectionKey === "pairs") {
          existingEmpty.remove();
        }
        const article = document.createElement("article");
        article.className = `card ${statusClass("planned")}`;
        article.dataset.cardKey = key;
        article.innerHTML = `
          <header>
            <span class="card-label" data-card-label>${escapeHtml(label)}</span>
            <span class="card-status" data-card-status>planned</span>
          </header>
          <p class="card-value" data-card-value>not available</p>
          <p class="card-detail" data-card-detail>Waiting for public market telemetry.</p>
        `;
        grid.appendChild(article);
        return cardNodes(key);
      }

      function setCard(key, payload) {
        const nodes = cardNodes(key);
        if (!nodes) {
          return;
        }
        const status = payload.status || "info";
        nodes.article.className = `card ${statusClass(status)}`;
        if (nodes.label && payload.label) {
          nodes.label.textContent = payload.label;
        }
        if (nodes.status) {
          nodes.status.textContent = status;
        }
        if (nodes.value && payload.value) {
          nodes.value.textContent = payload.value;
        }
        if (payload.detail !== undefined) {
          if (nodes.detail) {
            nodes.detail.textContent = payload.detail;
          } else if (payload.detail) {
            const detail = document.createElement("p");
            detail.className = "card-detail";
            detail.dataset.cardDetail = "";
            detail.textContent = payload.detail;
            nodes.article.appendChild(detail);
          }
        }
      }

      function computeSpreadBps(bestBid, bestAsk) {
        if (bestBid === null || bestAsk === null || bestBid <= 0 || bestAsk <= 0) {
          return null;
        }
        return ((bestAsk - bestBid) / ((bestAsk + bestBid) / 2)) * 10000;
      }

      function computeImbalance(bidQty, askQty) {
        if (bidQty === null || askQty === null || bidQty + askQty <= 0) {
          return null;
        }
        return bidQty / (bidQty + askQty);
      }

      function computeP90(values) {
        if (!values.length) {
          return null;
        }
        const ordered = [...values].sort((left, right) => left - right);
        const index = Math.min(ordered.length - 1, Math.max(0, Math.ceil(ordered.length * 0.9) - 1));
        return ordered[index];
      }

      function pairBridgeState(pair) {
        if (!bridge.pairs[pair]) {
          bridge.pairs[pair] = {
            lastUpdateMs: 0,
            bestBid: null,
            bestAsk: null,
            bidQty: null,
            askQty: null,
            lastUpdateId: null,
            spreadSamples: [],
            sources: new Set(),
          };
        }
        return bridge.pairs[pair];
      }

      function recordBookTicker(pair, payload) {
        const current = pairBridgeState(pair);
        current.lastUpdateMs = Date.now();
        current.bestBid = payload.bid;
        current.bestAsk = payload.ask;
        current.bidQty = payload.bidQty;
        current.askQty = payload.askQty;
        current.lastUpdateId = payload.updateId;
        current.sources.add("book_ticker");
        const spreadBps = computeSpreadBps(current.bestBid, current.bestAsk);
        if (spreadBps !== null) {
          current.spreadSamples.push(spreadBps);
          if (current.spreadSamples.length > 120) {
            current.spreadSamples = current.spreadSamples.slice(-120);
          }
        }
      }

      function recordDepth(pair, payload) {
        const current = pairBridgeState(pair);
        current.lastUpdateMs = Date.now();
        current.bestBid = payload.bestBid;
        current.bestAsk = payload.bestAsk;
        current.bidQty = payload.bidQty;
        current.askQty = payload.askQty;
        current.lastUpdateId = payload.lastUpdateId;
        current.sources.add("depth");
        const spreadBps = computeSpreadBps(current.bestBid, current.bestAsk);
        if (spreadBps !== null) {
          current.spreadSamples.push(spreadBps);
          if (current.spreadSamples.length > 120) {
            current.spreadSamples = current.spreadSamples.slice(-120);
          }
        }
      }

      function renderLiveBridgeCards() {
        const now = Date.now();
        const stalePairs = [];
        LIVE_PAIRS.forEach(pair => {
          const current = pairBridgeState(pair);
          const card = ensureCard("pairs", `pair_${pair.toLowerCase()}`, pair);
          if (!card) {
            return;
          }
          const freshnessMs = current.lastUpdateMs ? Math.max(0, now - current.lastUpdateMs) : null;
          const stale = freshnessMs === null || freshnessMs > FRESHNESS_WARNING_MS;
          if (stale) {
            stalePairs.push(pair);
          }
          const spreadBps = computeSpreadBps(current.bestBid, current.bestAsk);
          const p90Spread = computeP90(current.spreadSamples);
          const imbalance = computeImbalance(current.bidQty, current.askQty);
          setCard(`pair_${pair.toLowerCase()}`, {
            status: current.lastUpdateMs ? (stale ? "warning" : "healthy") : "planned",
            value: current.lastUpdateMs
              ? `${stale ? "stale" : "healthy"} / fresh=${freshnessMs}ms`
              : "waiting / fresh=n/a",
            detail: current.lastUpdateMs
              ? `spread=${spreadBps !== null ? spreadBps.toFixed(2) : "n/a"} / p90=${p90Spread !== null ? p90Spread.toFixed(2) : "n/a"} / bid=${current.bestBid !== null ? current.bestBid.toFixed(4) : "n/a"} / ask=${current.bestAsk !== null ? current.bestAsk.toFixed(4) : "n/a"} / imbalance=${imbalance !== null ? imbalance.toFixed(2) : "n/a"} / backlog=n/a / source=${Array.from(current.sources).sort().join("+") || "n/a"}`
              : "Waiting for public book_ticker/depth telemetry.",
          });
        });

        const staleChanged = bridge.lastStalePairs.join(",") !== stalePairs.join(",");
        if (staleChanged && bridge.lastStalePairs.length && stalePairs.length) {
          bridge.staleSpikeCount += 1;
        }
        bridge.lastStalePairs = stalePairs;

        ensureCard("data-infra", "infra_queue", "Queue");
        ensureCard("data-infra", "infra_recovery", "Recovery");
        ensureCard("data-infra", "infra_losses", "Losses / Kill");
        ensureCard("alerts", "active_alerts", "Active Alerts");
        ensureCard("alerts", "backlog_stale", "Backlog / Stale");
        ensureCard("alerts", "infra_guardrails", "Infra Guardrails");
        setCard("infra_queue", {
          status: "info",
          value: "backlog=n/a / hwm=n/a / drop=0.0%",
          detail: "Public Binance live bridge does not expose internal runtime queue backlog.",
        });
        setCard("infra_recovery", {
          status: stalePairs.length || bridge.reconnectCount ? "warning" : "healthy",
          value: `reconnect=${bridge.reconnectCount} / retry=0 / stale_spikes=${bridge.staleSpikeCount}`,
          detail: stalePairs.length ? stalePairs.join(", ") : "No stale pair",
        });
        setCard("infra_losses", {
          status: "info",
          value: "dtr=n/a / log=n/a / kill=off",
          detail: "Public market bridge only; loss and kill-switch surfaces still require governed backend runtime.",
        });
        setCard("active_alerts", {
          status: stalePairs.length ? "warning" : "healthy",
          value: String(stalePairs.length),
          detail: stalePairs.length
            ? `Public stale pair alerts: ${stalePairs.join(", ")}`
            : "No public stale-pair alert",
        });
        setCard("backlog_stale", {
          status: stalePairs.length ? "warning" : "healthy",
          value: `backlog=n/a / stale=${stalePairs.length}`,
          detail: stalePairs.length ? stalePairs.join(", ") : "No stale pair",
        });
        setCard("infra_guardrails", {
          status: stalePairs.length || bridge.reconnectCount ? "warning" : "info",
          value: `hwm=n/a / drop=0.0% / spikes=${bridge.staleSpikeCount}`,
          detail: `public_market_bridge / reconnect=${bridge.reconnectCount} / tracked_pairs=${LIVE_PAIRS.join(", ")}`,
        });
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
        drawLiquidity();
      }

      function drawLiquidity() {
        const book = state.lastBookTicker;
        const depth = state.lastDepth;
        if (!book && !depth) {
          setLiquidity("No book_ticker/depth telemetry loaded yet.");
          return;
        }

        const bestBid = book ? book.bid : depth ? depth.bestBid : null;
        const bestAsk = book ? book.ask : depth ? depth.bestAsk : null;
        const spreadBps = (
          bestBid !== null && bestAsk !== null && bestBid > 0 && bestAsk > 0
        )
          ? ((bestAsk - bestBid) / ((bestAsk + bestBid) / 2)) * 10000
          : null;
        const bidQty = book ? book.bidQty : depth ? depth.bidQty : null;
        const askQty = book ? book.askQty : depth ? depth.askQty : null;
        const imbalance = (
          bidQty !== null && askQty !== null && bidQty + askQty > 0
        )
          ? bidQty / (bidQty + askQty)
          : null;
        const depthUpdate = depth ? ` / depth_u=${depth.lastUpdateId}` : "";
        setLiquidity(
          `bid=${bestBid !== null ? bestBid.toFixed(4) : "n/a"} / ask=${bestAsk !== null ? bestAsk.toFixed(4) : "n/a"} / spread_bps=${spreadBps !== null ? spreadBps.toFixed(2) : "n/a"} / bid_qty=${bidQty !== null ? bidQty.toFixed(4) : "n/a"} / ask_qty=${askQty !== null ? askQty.toFixed(4) : "n/a"} / imbalance=${imbalance !== null ? imbalance.toFixed(2) : "n/a"}${depthUpdate}`
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

      function normalizeBookTickerPayload(payload) {
        if (!payload) {
          return null;
        }
        if (payload.e !== "bookTicker" && !(payload.stream || "").endsWith("@bookTicker")) {
          return null;
        }
        return {
          bid: Number(payload.b),
          ask: Number(payload.a),
          bidQty: Number(payload.B),
          askQty: Number(payload.A),
          updateId: payload.u ?? null,
        };
      }

      function normalizeDepthPayload(payload) {
        if (!payload) {
          return null;
        }
        if (payload.e !== "depthUpdate" && !(payload.stream || "").endsWith("@depth")) {
          return null;
        }
        const bids = Array.isArray(payload.b) ? payload.b : [];
        const asks = Array.isArray(payload.a) ? payload.a : [];
        const topBid = Array.isArray(bids[0]) ? bids[0] : [0, 0];
        const topAsk = Array.isArray(asks[0]) ? asks[0] : [0, 0];
        return {
          bestBid: Number(topBid[0] || 0),
          bestAsk: Number(topAsk[0] || 0),
          bidQty: Number(topBid[1] || 0),
          askQty: Number(topAsk[1] || 0),
          lastUpdateId: payload.u ?? null,
        };
      }

      function pairFromStream(stream) {
        if (!stream) {
          return "";
        }
        const [symbol] = String(stream).split("@");
        return symbol ? symbol.toUpperCase() : "";
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
        state.lastBookTicker = null;
        state.lastDepth = null;
        drawLiquidity();
        const symbol = state.pair.toLowerCase();
        const streams = [
          `${symbol}@kline_${state.timeframe}`,
          `${symbol}@bookTicker`,
          `${symbol}@depth`,
        ];
        const streamLabel = streams.join(" / ");
        const endpoint = `wss://stream.binance.com:9443/stream?streams=${streams.join("/")}`;
        const socket = new WebSocket(endpoint);
        state.socket = socket;
        setConnection(`Connecting: ${streamLabel}`, "warning");

        socket.addEventListener("open", () => {
          setConnection(`Connected: ${streamLabel}`, "healthy");
        });

        socket.addEventListener("message", event => {
          try {
            const envelope = JSON.parse(event.data);
            const stream = envelope && typeof envelope === "object" && envelope.data ? String(envelope.stream || "") : "";
            const payload = envelope && typeof envelope === "object" && envelope.data ? envelope.data : envelope;
            if (stream.endsWith("@bookTicker")) {
              const book = normalizeBookTickerPayload({ ...payload, stream });
              if (book) {
                state.lastBookTicker = book;
                recordBookTicker(pairFromStream(stream) || state.pair, book);
                renderLiveBridgeCards();
                drawLiquidity();
              }
              return;
            }
            if (stream.endsWith("@depth")) {
              const depth = normalizeDepthPayload({ ...payload, stream });
              if (depth) {
                state.lastDepth = depth;
                recordDepth(pairFromStream(stream) || state.pair, depth);
                renderLiveBridgeCards();
                drawLiquidity();
              }
              return;
            }
            const candle = normalizeSocketPayload(payload);
            if (candle) {
              upsertCandle(candle);
              drawChart();
            }
          } catch (error) {
            setConnection(`Stream parse error: ${String(error)}`, "critical");
          }
        });

        socket.addEventListener("error", () => {
          setConnection(`WebSocket error on ${streamLabel}`, "critical");
        });

        socket.addEventListener("close", () => {
          if (state.socket === socket) {
            setConnection(`Disconnected: ${streamLabel}`, "warning");
          }
        });
      }

      function connectLiveBridge() {
        if (bridge.socket) {
          bridge.socket.close();
          bridge.socket = null;
        }
        const streams = LIVE_PAIRS.flatMap(pair => {
          const symbol = pair.toLowerCase();
          return [`${symbol}@bookTicker`, `${symbol}@depth`];
        });
        const socket = new WebSocket(
          `wss://stream.binance.com:9443/stream?streams=${streams.join("/")}`
        );
        bridge.socket = socket;

        socket.addEventListener("message", event => {
          try {
            const envelope = JSON.parse(event.data);
            const stream = envelope && typeof envelope === "object" && envelope.data ? String(envelope.stream || "") : "";
            const payload = envelope && typeof envelope === "object" && envelope.data ? envelope.data : envelope;
            const pair = pairFromStream(stream);
            if (!pair || !LIVE_PAIRS.includes(pair)) {
              return;
            }
            if (stream.endsWith("@bookTicker")) {
              const book = normalizeBookTickerPayload({ ...payload, stream });
              if (book) {
                recordBookTicker(pair, book);
                renderLiveBridgeCards();
              }
              return;
            }
            if (stream.endsWith("@depth")) {
              const depth = normalizeDepthPayload({ ...payload, stream });
              if (depth) {
                recordDepth(pair, depth);
                renderLiveBridgeCards();
              }
            }
          } catch (_error) {
            renderLiveBridgeCards();
          }
        });

        socket.addEventListener("error", () => {
          bridge.reconnectCount += 1;
          renderLiveBridgeCards();
        });

        socket.addEventListener("close", () => {
          if (bridge.socket === socket) {
            bridge.reconnectCount += 1;
            renderLiveBridgeCards();
          }
        });
      }

      async function reloadMarketLab() {
        state.pair = pairSelect.value;
        state.timeframe = timeframeSelect.value;
        state.view = viewSelect.value;
        setConnection("Loading public Binance history...", "warning");
        setSummary("Refreshing local chart...");
        setLiquidity("Refreshing book_ticker/depth telemetry...");
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

      renderLiveBridgeCards();
      connectLiveBridge();
      window.setInterval(() => {
        renderLiveBridgeCards();
      }, 1000);
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
    panel_navigation = _render_panel_navigation(future_panels)
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
    .panel-nav-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
    }}
    .panel-nav-card {{
      border-radius: 12px;
      border: 1px solid var(--border);
      padding: 14px;
      display: grid;
      gap: 8px;
      background: #f8fbfd;
    }}
    .panel-nav-card header {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}
    .panel-nav-value {{
      margin: 0;
      font-size: 18px;
      font-weight: 700;
    }}
    .panel-nav-detail {{
      margin: 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }}
    .panel-nav-link {{
      color: #1e5db3;
      font-size: 13px;
      font-weight: 700;
      text-decoration: none;
    }}
    .panel-nav-link:hover {{
      text-decoration: underline;
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
    {panel_navigation}
    {rendered_sections}
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
