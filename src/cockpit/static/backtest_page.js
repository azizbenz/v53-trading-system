// backtest.html inline scripts extracted to a static asset (Patch A 2026-05-31).
// Pure JS, zero Jinja interpolation -> served static + browser-cached,
// removing ~985 lines from pages/backtest.html.

(() => {
    const modal = document.getElementById("folder-picker-modal");
    const drivesHost = document.getElementById("folder-picker-drives");
    const dirsHost = document.getElementById("folder-picker-directories");
    const currentHost = document.getElementById("folder-picker-current");
    const closeBtn = document.getElementById("folder-picker-close");
    const upBtn = document.getElementById("folder-picker-up");
    const selectBtn = document.getElementById("folder-picker-select");
    const pickerStateKey = "patch6_folder_picker_state";
    let currentTargetId = "";
    let currentPath = "";

    if (!modal || !drivesHost || !dirsHost || !currentHost || !closeBtn || !upBtn || !selectBtn) {
        return;
    }

    async function fetchJson(url) {
        const response = await fetch(url, {headers: {"Accept": "application/json"}});
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return response.json();
    }

    function savePickerState() {
        if (!currentTargetId) {
            return;
        }
        window.sessionStorage.setItem(
            pickerStateKey,
            JSON.stringify({targetId: currentTargetId, currentPath}),
        );
    }

    function folderSeedFromValue(rawValue) {
        const value = (rawValue || "").trim();
        if (!value) {
            return "";
        }
        const normalized = value.replaceAll("/", "\\");
        const lastSegment = normalized.split("\\").filter(Boolean).pop() || "";
        if (lastSegment.includes(".")) {
            return normalized.slice(0, Math.max(normalized.lastIndexOf("\\"), 0));
        }
        return value;
    }

    function clearPickerState() {
        window.sessionStorage.removeItem(pickerStateKey);
    }

    function openModal(targetId, initialPath = "") {
        currentTargetId = targetId;
        modal.style.display = "block";
        savePickerState();
        loadDrives();
        const input = document.getElementById(targetId);
        const initial = folderSeedFromValue(initialPath || (input && input.value ? input.value : ""));
        if (initial) {
            loadDirectory(initial);
        } else {
            currentHost.textContent = "select a drive";
            dirsHost.innerHTML = "";
            currentPath = "";
            savePickerState();
        }
    }

    function closeModal() {
        modal.style.display = "none";
        currentTargetId = "";
        currentPath = "";
        clearPickerState();
    }

    async function loadDrives() {
        const payload = await fetchJson("/backtest/picker/drives");
        drivesHost.innerHTML = "";
        for (const drive of payload.drives || []) {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "button button--ghost";
            button.textContent = drive.label || drive.path;
            button.addEventListener("click", () => loadDirectory(drive.path));
            drivesHost.appendChild(button);
        }
    }

    async function loadDirectory(path) {
        const payload = await fetchJson(`/backtest/picker/browse?path=${encodeURIComponent(path)}`);
        currentPath = payload.current_path || "";
        currentHost.textContent = currentPath || "n/a";
        dirsHost.innerHTML = "";
        savePickerState();
        for (const directory of payload.directories || []) {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "button button--ghost";
            button.style.textAlign = "left";
            button.textContent = directory.name;
            button.addEventListener("click", () => loadDirectory(directory.path));
            dirsHost.appendChild(button);
        }
        upBtn.dataset.parentPath = payload.parent_path || "";
    }

    async function tryNativePicker(targetId) {
        const input = document.getElementById(targetId);
        const initial = folderSeedFromValue(input && input.value ? input.value : currentPath);
        const payload = await fetchJson(`/backtest/picker/native?path=${encodeURIComponent(initial || "")}`);
        if (payload.status === "FOLDER_PICKER_SELECTED" && payload.selected_path && input) {
            input.value = payload.selected_path;
            clearPickerState();
            return true;
        }
        if (payload.status === "FOLDER_PICKER_CANCELLED") {
            clearPickerState();
            return true;
        }
        return false;
    }

    document.querySelectorAll(".js-browse-folder").forEach((button) => {
        button.addEventListener("click", async () => {
            const targetId = button.dataset.target || "";
            if (!targetId) {
                return;
            }
            try {
                const handled = await tryNativePicker(targetId);
                if (handled) {
                    return;
                }
            } catch (error) {
                console.warn("native folder picker unavailable", error);
            }
            openModal(targetId);
        });
    });
    closeBtn.addEventListener("click", closeModal);
    modal.addEventListener("click", (event) => {
        if (event.target === modal) {
            closeModal();
        }
    });
    upBtn.addEventListener("click", () => {
        const parentPath = upBtn.dataset.parentPath || "";
        if (parentPath) {
            loadDirectory(parentPath);
        }
    });
    selectBtn.addEventListener("click", () => {
        if (!currentTargetId || !currentPath) {
            return;
        }
        const input = document.getElementById(currentTargetId);
        if (input) {
            input.value = currentPath;
        }
        closeModal();
    });
    try {
        const persisted = JSON.parse(window.sessionStorage.getItem(pickerStateKey) || "null");
        if (persisted && persisted.targetId) {
            openModal(persisted.targetId, persisted.currentPath || "");
        }
    } catch (error) {
        console.warn("folder picker state restore failed", error);
        clearPickerState();
    }
})();

/* ---- block ---- */

(() => {
    const form = document.getElementById("backtest-run-form");
    if (!form) {
        return;
    }
    const phaseSelect = form.querySelector('select[name="action_name"]');
    const launchButton = document.getElementById("backtest-launch-button");
    const previewIdInput = form.querySelector('input[name="preview_id"]');
    const requestHashInput = form.querySelector('input[name="request_hash"]');
    if (!phaseSelect || !launchButton || !previewIdInput || !requestHashInput) {
        return;
    }

    function syncLaunchButton() {
        const selectedAction = String(phaseSelect.value || "").trim();
        const hasPreview = Boolean(
            String(previewIdInput.value || "").trim()
            && String(requestHashInput.value || "").trim()
        );
        const allowLaunch = hasPreview && selectedAction !== "PHASE_A1_PREVIEW";
        launchButton.disabled = !allowLaunch;
        launchButton.title = allowLaunch
            ? ""
            : selectedAction === "PHASE_A1_PREVIEW"
                ? "Phase A1 is preview-only."
                : "Generate a matching preview before launching this phase.";
    }

    phaseSelect.addEventListener("change", syncLaunchButton);
    syncLaunchButton();
})();

/* ---- block ---- */

(() => {
    const featureHost = document.getElementById("candidate-feature-table-host");
    const wiringHost = document.getElementById("feature-engine-ml-wiring-host");
    const featureStatusToken = document.getElementById("candidate-feature-status-token");
    const activeFeatureCountToken = document.getElementById("candidate-active-feature-count");
    const wiringStatusToken = document.getElementById("candidate-wiring-status-token");
    const sourceUrl =
        featureHost?.dataset.featureTableUrl
        || wiringHost?.dataset.featureTableUrl
        || "/backtest/candidate-feature-table.json";

    if (!featureHost && !wiringHost) {
        return;
    }

    function esc(value) {
        return String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#39;");
    }

    function normalizeList(value) {
        if (Array.isArray(value)) {
            return value.filter(Boolean).map((item) => String(item));
        }
        if (value === null || value === undefined || value === "") {
            return [];
        }
        return [String(value)];
    }

    function renderFeatureMetrics(payload) {
        const featureNames = Array.isArray(payload?.active_feature_names)
            ? payload.active_feature_names.filter(Boolean).map((item) => String(item))
            : [];
        const rows = Array.isArray(payload?.rows) ? payload.rows : [];
        const status = payload?.status || "CANDIDATE_FEATURE_TABLE_NOT_PROVEN";
        if (featureNames.length === 0) {
            return `<p class="muted">${esc(status)}</p>`;
        }
        if (rows.length === 0) {
            return `<p class="muted">${esc(status)}</p>`;
        }
        const head = featureNames.map((name) => `<th>${esc(name)}</th>`).join("");
        const body = rows.map((row) => {
            const reasonCodes = normalizeList(row.reason_codes).join(", ") || "none";
            const featureCells = featureNames
                .map((name) => `<td>${esc(row[name] ?? "n/a")}</td>`)
                .join("");
            return `
                <tr>
                    <td><code>${esc(row.candidate_id || "")}</code></td>
                    <td>${esc(row.pair || "")}</td>
                    <td>${esc(row.engine_id || "")}</td>
                    <td>${esc(row.timeframe || "")}</td>
                    <td>${esc(row.outcome_status || "")}</td>
                    <td>${esc(row.accepted_or_refused || "")}</td>
                    <td>${esc(reasonCodes)}</td>
                    ${featureCells}
                </tr>
            `;
        }).join("");
        return `
            <table class="data-table data-table--compact">
                <thead>
                    <tr>
                        <th>Candidate</th>
                        <th>Pair</th>
                        <th>Engine</th>
                        <th>TF</th>
                        <th>Outcome</th>
                        <th>Accepted / refused</th>
                        <th>Reason codes</th>
                        ${head}
                    </tr>
                </thead>
                <tbody>${body}</tbody>
            </table>
        `;
    }

    function renderWiringAudit(payload) {
        const rows = Array.isArray(payload?.wiring_rows) ? payload.wiring_rows : [];
        const status = payload?.wiring_status || "FEATURE_ENGINE_ML_WIRING_NOT_PROVEN";
        if (rows.length === 0) {
            return `<p class="muted">${esc(status)}</p>`;
        }
        const body = rows.map((row) => `
            <tr>
                <td><code>${esc(row.feature_name || "")}</code></td>
                <td>${row.training_selected ? "true" : "false"}</td>
                <td>${row.artifact_selected ? "true" : "false"}</td>
                <td>${row.runtime_payload_available ? "true" : "false"}</td>
                <td>${esc(row.native_engine_origin || "")}</td>
                <td>${esc(row.native_engine_consumption_status || "")}</td>
                <td>${row.ml_runtime_wired ? "true" : "false"}</td>
                <td>${esc(row.ml_block_reason || "none")}</td>
            </tr>
        `).join("");
        return `
            <table class="data-table data-table--compact">
                <thead>
                    <tr>
                        <th>Feature</th>
                        <th>Training selected</th>
                        <th>Artifact selected</th>
                        <th>Runtime payload</th>
                        <th>Native origin</th>
                        <th>Native consumption</th>
                        <th>ML wired</th>
                        <th>ML block reason</th>
                    </tr>
                </thead>
                <tbody>${body}</tbody>
            </table>
        `;
    }

    async function loadCandidateFeatureAudits() {
        try {
            const response = await fetch(sourceUrl, {
                headers: {"Accept": "application/json"},
            });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(payload.error || `HTTP ${response.status}`);
            }
            if (featureStatusToken) {
                featureStatusToken.textContent = String(
                    payload.status || "CANDIDATE_FEATURE_TABLE_NOT_PROVEN"
                );
            }
            if (activeFeatureCountToken) {
                activeFeatureCountToken.textContent = String(
                    Array.isArray(payload.active_feature_names)
                        ? payload.active_feature_names.length
                        : 0
                );
            }
            if (wiringStatusToken) {
                wiringStatusToken.textContent = String(
                    payload.wiring_status || "FEATURE_ENGINE_ML_WIRING_NOT_PROVEN"
                );
            }
            if (featureHost) {
                featureHost.innerHTML = `
                    <h5>Candidate Feature Metrics</h5>
                    ${renderFeatureMetrics(payload)}
                `;
            }
            if (wiringHost) {
                wiringHost.innerHTML = renderWiringAudit(payload);
            }
        } catch (error) {
            console.warn("candidate feature audit fetch failed", error);
            if (featureHost) {
                featureHost.innerHTML = `
                    <h5>Candidate Feature Metrics</h5>
                    <p class="muted">CANDIDATE_FEATURE_TABLE_NOT_AVAILABLE</p>
                `;
            }
            if (wiringHost) {
                wiringHost.innerHTML =
                    '<p class="muted">FEATURE_ENGINE_ML_WIRING_NOT_AVAILABLE</p>';
            }
        }
    }

    const schedule = window.requestIdleCallback
        ? () => window.requestIdleCallback(loadCandidateFeatureAudits, {timeout: 1500})
        : () => window.setTimeout(loadCandidateFeatureAudits, 0);
    schedule();
})();

/* ---- block ---- */

(() => {
    const detailUrl = "/backtest/candidate-detail.json";
    const detailHost = document.getElementById("candidate-detail-host");
    const windowHost = document.getElementById("candidate-window-host");
    const selectionToken = document.getElementById("candidate-selection-token");
    const candidateRows = Array.from(document.querySelectorAll("[data-candidate-row]"));
    const candidateForms = Array.from(document.querySelectorAll("[data-candidate-select-form]"));
    let currentCandidateId = detailHost?.dataset.selectedCandidateId || "";
    let requestToken = 0;

    if (!detailHost || !windowHost || candidateForms.length === 0) {
        return;
    }

    function esc(value) {
        return String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#39;");
    }

    function normalizeList(value) {
        if (Array.isArray(value)) {
            return value.filter(Boolean).map((item) => String(item));
        }
        if (value === null || value === undefined || value === "") {
            return [];
        }
        return [String(value)];
    }

    function renderListItems(values, emptyLabel = "not_available") {
        const items = normalizeList(values);
        if (items.length === 0) {
            return `<li>${esc(emptyLabel)}</li>`;
        }
        return items.map((item) => `<li><code>${esc(item)}</code></li>`).join("");
    }

    function renderCandidateDetail(payload) {
        const detail = payload?.detail || {};
        const replay = payload?.replay || {};
        if (!detail.candidate_id) {
            return '<p class="muted">CANDIDATE_DETAIL_NOT_AVAILABLE</p>';
        }
        const featureValues = JSON.stringify(detail.feature_values || {}, null, 2);
        const reasonCodes = normalizeList(detail.reason_codes).join(", ") || "not_available";
        const executionState = replay.execution_state || replay.detailed_replay_status || "NOT_PROVEN";
        return `
            <div class="candidate-detail-panel">
                <div class="candidate-detail-hero">
                    <div>
                        <h4><code>${esc(detail.candidate_id || "")}</code></h4>
                        <div class="muted">Selected candidate detail without full-page reload.</div>
                    </div>
                    <div class="candidate-chip-list">
                        <span class="candidate-chip candidate-chip--pair">${esc(detail.pair || "n/a")}</span>
                        <span class="candidate-chip candidate-chip--engine">${esc(detail.engine_id || "n/a")}</span>
                        <span class="candidate-chip candidate-chip--timeframe">${esc(detail.timeframe || "n/a")}</span>
                        <span class="candidate-chip candidate-chip--status">${esc(executionState)}</span>
                    </div>
                </div>
                <div class="candidate-proof-banner">Replay/fill/cost remains model-only, not proven live.</div>
                <div class="candidate-detail-grid">
                    <div class="candidate-metric">
                        <span class="candidate-metric__label">Strategy</span>
                        <span class="candidate-metric__value">${esc(detail.strategy_id || "n/a")}</span>
                    </div>
                    <div class="candidate-metric">
                        <span class="candidate-metric__label">Reason codes</span>
                        <span class="candidate-metric__value">${esc(reasonCodes)}</span>
                    </div>
                    <div class="candidate-metric">
                        <span class="candidate-metric__label">Score raw / penalized / final</span>
                        <span class="candidate-metric__value">${esc(detail.score_raw ?? "n/a")} / ${esc(detail.score_penalized ?? "n/a")} / ${esc(detail.score_final ?? "n/a")}</span>
                    </div>
                    <div class="candidate-metric">
                        <span class="candidate-metric__label">Spread / slippage / edge (bps)</span>
                        <span class="candidate-metric__value">${esc(detail.spread_bps ?? "n/a")} / ${esc(detail.slippage_bps ?? "n/a")} / ${esc(detail.expected_edge_bps ?? "n/a")}</span>
                    </div>
                    <div class="candidate-metric">
                        <span class="candidate-metric__label">Replay status</span>
                        <span class="candidate-metric__value">${esc(replay.detailed_replay_status || "DETAILED_REPLAY_NOT_PROVEN")}</span>
                    </div>
                    <div class="candidate-metric">
                        <span class="candidate-metric__label">Execution state</span>
                        <span class="candidate-metric__value">${esc(replay.execution_state || "NOT_PROVEN")}</span>
                    </div>
                </div>
                <div class="candidate-detail-section">
                    <h5>Feature refs</h5>
                    <ul>${renderListItems(detail.feature_refs, "not_available")}</ul>
                </div>
                <div class="candidate-detail-section">
                    <h5>Replay proof</h5>
                    <ul>
                        <li>Expected CE: ${esc(replay.expected_ce_net ?? "NOT_PROVEN")}</li>
                        <li>Net return (bps): ${esc(replay.net_return_bps ?? "NOT_PROVEN")}</li>
                        <li>Reason codes: ${esc(normalizeList(replay.reason_codes).join(", ") || "none")}</li>
                        <li>Fee / impact / fill / parity: ${esc(replay.fee_source_status || "n/a")} / ${esc(replay.impact_source_status || "n/a")} / ${esc(replay.fill_realism_status || "n/a")} / ${esc(replay.cost_parity_status || "n/a")}</li>
                    </ul>
                </div>
                <div class="candidate-detail-section">
                    <h5>Feature values</h5>
                    <pre class="candidate-code-box"><code>${esc(featureValues)}</code></pre>
                </div>
            </div>
        `;
    }

    function renderCandidateWindow(payload) {
        if (!payload || !Object.keys(payload).length) {
            return '<p class="muted">WINDOW_DATA_NOT_AVAILABLE</p>';
        }
        return `
            <table class="data-table data-table--compact">
                <tbody>
                    <tr><th>Window status</th><td>${esc(payload.raw_window_status || "RAW_WINDOW_NOT_PROVEN")}</td></tr>
                    <tr><th>Depth status</th><td>${esc(payload.book_depth_source_status || "BOOK_DEPTH_NOT_PROVEN")}</td></tr>
                    <tr><th>Coverage status</th><td>${esc(payload.source_coverage_status || "RAW_WINDOW_SOURCE_NOT_PROVEN")}</td></tr>
                    <tr><th>Trade path</th><td><code>${esc(payload.raw_trade_path || "not_available")}</code></td></tr>
                    <tr><th>Orderbook path</th><td><code>${esc(payload.raw_book_path || "not_available")}</code></td></tr>
                    <tr><th>OHLCV path</th><td><code>${esc(payload.raw_ohlcv_path || "not_available")}</code></td></tr>
                    <tr><th>Replay artifact</th><td><code>${esc(payload.replay_artifact_path || "not_available")}</code></td></tr>
                </tbody>
            </table>
        `;
    }

    function applySelectedState(candidateId) {
        currentCandidateId = candidateId || "";
        detailHost.dataset.selectedCandidateId = currentCandidateId;
        if (selectionToken) {
            selectionToken.textContent = currentCandidateId || "none";
        }
        candidateRows.forEach((row) => {
            const rowCandidateId = row.dataset.candidateId || "";
            const selected = rowCandidateId === currentCandidateId;
            row.classList.toggle("candidate-row--selected", selected);
            const button = row.querySelector(".candidate-select-button");
            if (button) {
                button.setAttribute("aria-pressed", selected ? "true" : "false");
                button.textContent = selected ? "Selected" : "Inspect";
            }
        });
    }

    async function fetchCandidatePayload(candidateId) {
        const response = await fetch(`${detailUrl}?candidate_id=${encodeURIComponent(candidateId)}`, {
            headers: {"Accept": "application/json"},
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(payload.error || `HTTP ${response.status}`);
        }
        return payload;
    }

    async function selectCandidate(candidateId, {updateHistory = true} = {}) {
        const nextCandidateId = (candidateId || "").trim();
        if (!nextCandidateId) {
            return;
        }
        const token = ++requestToken;
        detailHost.innerHTML = '<p class="muted">Loading candidate detail...</p>';
        windowHost.innerHTML = '<p class="muted">Loading replay window...</p>';
        try {
            const payload = await fetchCandidatePayload(nextCandidateId);
            if (token !== requestToken) {
                return;
            }
            detailHost.innerHTML = renderCandidateDetail(payload);
            windowHost.innerHTML = renderCandidateWindow(payload.window || {});
            applySelectedState(payload.selected_candidate_id || nextCandidateId);
            if (updateHistory) {
                const url = new URL(window.location.href);
                url.searchParams.set("candidate_id", nextCandidateId);
                window.history.replaceState({candidateId: nextCandidateId}, "", url);
            }
        } catch (error) {
            console.warn("candidate detail fetch failed", error);
            detailHost.innerHTML = '<p class="muted">CANDIDATE_DETAIL_NOT_AVAILABLE</p>';
            windowHost.innerHTML = '<p class="muted">WINDOW_DATA_NOT_AVAILABLE</p>';
        }
    }

    candidateForms.forEach((form) => {
        form.addEventListener("submit", (event) => {
            event.preventDefault();
            const input = form.querySelector('input[name="candidate_id"]');
            const candidateId = input ? input.value : "";
            void selectCandidate(candidateId);
        });
    });

    candidateRows.forEach((row) => {
        row.addEventListener("click", (event) => {
            if (event.target instanceof HTMLElement && event.target.closest("button, input, form, a")) {
                return;
            }
            const candidateId = row.dataset.candidateId || "";
            void selectCandidate(candidateId);
        });
    });

    window.addEventListener("popstate", () => {
        const url = new URL(window.location.href);
        const candidateId = url.searchParams.get("candidate_id") || "";
        if (candidateId && candidateId !== currentCandidateId) {
            void selectCandidate(candidateId, {updateHistory: false});
        }
    });

    applySelectedState(currentCandidateId);
})();

/* ---- block ---- */

(() => {
    function repairBacktestContentPlacement() {
        const layout = document.querySelector("body > .layout");
        const main = layout?.querySelector(":scope > .main");
        const content = main?.querySelector(":scope > main.content");
        if (!layout || !main || !content) {
            return;
        }

        const misplacedSections = Array.from(layout.children).filter((node) => {
            if (!(node instanceof HTMLElement)) {
                return false;
            }
            if (node === main || node.matches("aside.sidebar")) {
                return false;
            }
            return node.matches("section");
        });

        misplacedSections.forEach((section) => {
            content.appendChild(section);
        });

        const footer = layout.querySelector(":scope > footer.footer");
        if (footer && footer.parentElement !== main) {
            main.appendChild(footer);
        }
    }

    repairBacktestContentPlacement();

    const statusUrl = "/backtest/status.json";
    const pollIntervalMs = 4000;
    let requestInFlight = false;

    function esc(value) {
        return String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#39;");
    }

    function setText(id, value) {
        const node = document.getElementById(id);
        if (node) {
            node.textContent = value;
        }
    }

    function setProgress(barId, fillId, pctId, pctValue) {
        const pct = Number.isFinite(pctValue) ? Math.max(0, Math.min(100, pctValue)) : 0;
        const bar = document.getElementById(barId);
        const fill = document.getElementById(fillId);
        if (bar) {
            bar.setAttribute("aria-valuenow", String(pct));
        }
        if (fill) {
            fill.style.width = `${pct}%`;
        }
        setText(pctId, `${pct}%`);
    }

    function formatDuration(value) {
        return Number.isFinite(value) ? `${value.toFixed(1)}s` : "n/a";
    }

    function formatEta(value) {
        return Number.isFinite(value) && value > 0 ? `${value.toFixed(1)} min` : "-";
    }

    function formatStdout(value) {
        return Number.isFinite(value) ? `${value.toFixed(1)} KB` : "0.0 KB";
    }

    function renderLatestJob(job) {
        const host = document.getElementById("backtest-progress-body");
        if (!host) {
            return;
        }
        if (!job) {
            host.innerHTML = '<p class="muted">No audited backtest runner activity recorded yet.</p>';
            return;
        }
        const cancelForm = job.can_cancel
            ? `
            <form action="/backtest/cancel" method="post" style="margin-top:0.5rem;">
                <input type="hidden" name="job_id" value="${esc(job.job_id)}">
                <input type="text" name="operator_reason" placeholder="reason (optional)" value="operator_requested_cancel">
                <button class="button button--danger" type="submit">Cancel Job</button>
            </form>`
            : "";
        host.innerHTML = `
            <table class="data-table data-table--compact">
                <tbody>
                    <tr><th>Job</th><td><code id="backtest-latest-job-id">${esc(job.job_id || "n/a")}</code></td></tr>
                    <tr><th>Status</th><td id="backtest-latest-job-status">${esc(job.status || "n/a")}</td></tr>
                    <tr><th>PID</th><td id="backtest-latest-job-pid">${job.pid ? esc(job.pid) : "n/a"}</td></tr>
                    <tr><th>PID signal</th><td id="backtest-latest-job-pid-state">${job.pid_alive ? "alive" : "dead_or_missing"}</td></tr>
                    <tr>
                        <th>Progress</th>
                        <td>
                            <div id="backtest-latest-progress-bar" class="progress-bar" role="progressbar" aria-valuenow="${esc(job.progress_pct ?? 0)}" aria-valuemin="0" aria-valuemax="100" style="background:#222;border:1px solid #555;width:120px;height:14px;display:inline-block;vertical-align:middle;">
                                <div id="backtest-latest-progress-fill" class="progress-bar__fill" style="background:#3a8;width:${esc(job.progress_pct ?? 0)}%;height:100%;"></div>
                            </div>
                            <span id="backtest-latest-progress-pct" class="muted">${esc(job.progress_pct ?? 0)}%</span>
                        </td>
                    </tr>
                    <tr><th>ETA</th><td id="backtest-latest-job-eta">${esc(formatEta(job.eta_minutes))}</td></tr>
                    <tr><th>Latest activity</th><td id="backtest-latest-job-activity">${esc(job.latest_activity_iso || "n/a")}</td></tr>
                    <tr><th>Progress detail</th><td id="backtest-latest-job-health">${esc(job.progress_health_status || "n/a")} <span class="muted">${esc(job.progress_health_message || "")}</span></td></tr>
                    <tr><th>Duration</th><td id="backtest-latest-job-duration">${esc(formatDuration(job.duration_seconds))}</td></tr>
                    <tr><th>Produced files</th><td id="backtest-latest-job-produced">${esc(job.produced_file_count ?? 0)}</td></tr>
                    <tr><th>Output refs</th><td id="backtest-latest-job-output-refs">${esc(job.output_ref_count ?? 0)}</td></tr>
                    <tr><th>Stdout log</th><td id="backtest-latest-job-stdout">${esc(formatStdout(job.stdout_log_size_kb))}</td></tr>
                </tbody>
            </table>
            ${cancelForm}
        `;
    }

    function renderRecentJobs(jobs) {
        const host = document.getElementById("backtest-jobs-table-host");
        if (!host) {
            return;
        }
        if (!Array.isArray(jobs) || jobs.length === 0) {
            host.innerHTML = '<p class="muted">No audited backtest runner activity recorded yet.</p>';
            return;
        }
        const rows = jobs.map((job, index) => `
            <tr${index === 0 ? ' id="backtest-latest-table-row"' : ""}>
                <td>
                    <div><code${index === 0 ? ' id="backtest-latest-table-job-id"' : ""}>${esc(job.job_id || "n/a")}</code></div>
                    <div class="muted">${esc(job.job_kind || "unknown")}</div>
                </td>
                <td${index === 0 ? ' id="backtest-latest-table-status"' : ""}>${esc(job.status || "n/a")}</td>
                <td>
                    <div${index === 0 ? ' id="backtest-latest-table-progress-bar"' : ""} class="progress-bar" role="progressbar" aria-valuenow="${esc(job.progress_pct ?? 0)}" aria-valuemin="0" aria-valuemax="100" style="background:#222;border:1px solid #555;width:120px;height:14px;display:inline-block;vertical-align:middle;">
                        <div${index === 0 ? ' id="backtest-latest-table-progress-fill"' : ""} class="progress-bar__fill" style="background:#3a8;width:${esc(job.progress_pct ?? 0)}%;height:100%;"></div>
                    </div>
                    <span${index === 0 ? ' id="backtest-latest-table-progress-pct"' : ""} class="muted">${esc(job.progress_pct ?? 0)}%</span>
                    <div${index === 0 ? ' id="backtest-latest-table-activity"' : ""}>${esc(job.latest_activity_iso || "n/a")}</div>
                    <div class="muted">${esc(formatDuration(job.duration_seconds))}</div>
                </td>
                <td>${index === 0 ? `<span id="backtest-latest-table-eta">${esc(formatEta(job.eta_minutes))}</span>` : esc(formatEta(job.eta_minutes))}</td>
                <td>
                    <div>${esc(job.produced_file_count ?? 0)} files</div>
                    <div${index === 0 ? ' id="backtest-latest-table-output-refs"' : ""} class="muted">${esc(job.output_ref_count ?? 0)} refs</div>
                </td>
                <td>
                    <div>${esc(formatStdout(job.stdout_log_size_kb))}</div>
                    <div class="muted"><code>${esc(job.stdout_log_path || "")}</code></div>
                </td>
                <td>${esc(job.error_summary || "none")}</td>
            </tr>
        `).join("");
        host.innerHTML = `
            <div class="recent-jobs-scroll">
                <table class="data-table data-table--compact">
                    <thead>
                        <tr><th>Job</th><th>Status</th><th>Progress</th><th>ETA (min)</th><th>Outputs</th><th>Logs</th><th>Error</th></tr>
                    </thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>
        `;
    }

    function applyService(service) {
        if (!service) {
            return;
        }
        const dot = document.getElementById("shadow-service-dot");
        const text = document.getElementById("shadow-service-text");
        if (dot) {
            dot.classList.toggle("status-dot--up", !!service.running);
            dot.classList.toggle("status-dot--down", !service.running);
        }
        if (text) {
            text.textContent = service.status_text || "Shadow Service offline";
        }
    }

    function applyMonitorState(isActive) {
        const active = !!isActive;
        [
            "backtest-progress-card",
            "backtest-recent-jobs-card",
            "backtest-runner-coverage-card",
        ].forEach((id) => {
            const node = document.getElementById(id);
            if (node) {
                node.classList.toggle("backtest-monitor-card--active", active);
            }
        });
        [
            ["backtest-progress-badge", active ? "active monitoring" : "idle snapshot"],
            ["backtest-recent-jobs-badge", active ? "watch here" : "latest queue view"],
            ["backtest-runner-coverage-badge", active ? "live reading" : "proof surface"],
        ].forEach(([id, label]) => {
            const badge = document.getElementById(id);
            if (badge) {
                badge.textContent = label;
                badge.classList.toggle("monitor-badge--active", active);
                badge.classList.toggle("monitor-badge--idle", !active);
            }
        });
    }

    function applySummary(summary) {
        if (!summary) {
            return;
        }
        setText("backtest-latest-status", summary.latest_status || "not_present");
        setText("backtest-summary-requested", String(summary.requested_count ?? 0));
        setText("backtest-summary-running", String(summary.running_count ?? 0));
        setText("backtest-summary-completed", String(summary.completed_count ?? 0));
        setText("backtest-summary-failed", String(summary.failed_count ?? 0));
        applyMonitorState((summary.running_count ?? 0) > 0);
    }

    function applyLatestJob(job) {
        renderLatestJob(job);
    }

    function applyJobs(jobs) {
        renderRecentJobs(jobs);
    }

    async function refreshStatus() {
        if (requestInFlight) {
            return;
        }
        requestInFlight = true;
        try {
            const response = await fetch(statusUrl, {headers: {"Accept": "application/json"}});
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const payload = await response.json();
            applyService(payload.service || null);
            applySummary(payload.summary || null);
            applyLatestJob(payload.latest_job || null);
            applyJobs(payload.backtest_jobs || []);
        } catch (error) {
            console.warn("backtest status polling failed", error);
        } finally {
            requestInFlight = false;
        }
    }

    window.setInterval(refreshStatus, pollIntervalMs);
    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible") {
            refreshStatus();
        }
    });
    refreshStatus();
})();

/* ---- block ---- */

(() => {
    const hiddenInput = document.getElementById("backtest_timeframes_value");
    const trainingMirror = document.getElementById("backtest_training_timeframe");
    const singleWrap = document.getElementById("backtest_timeframe_single_wrap");
    const multiWrap = document.getElementById("backtest_timeframe_multi_wrap");
    const singleSelect = document.getElementById("backtest_timeframe_single");
    const previewNode = document.getElementById("backtest_timeframe_scope_preview");
    const modeInputs = Array.from(document.querySelectorAll('input[name="backtest_timeframe_mode_ui"]'));
    const multiInputs = Array.from(document.querySelectorAll(".js-backtest-timeframe-multi"));
    const orderedTimeframes = ["1m", "5m", "10m", "15m"];
    if (!hiddenInput || !trainingMirror || !singleWrap || !multiWrap || !singleSelect || !modeInputs.length || !multiInputs.length) {
        return;
    }

    function normalizeTimeframes(rawValue) {
        const seen = new Set();
        return String(rawValue || "")
            .split(",")
            .map((value) => value.trim())
            .filter((value) => value && orderedTimeframes.includes(value) && !seen.has(value) && seen.add(value));
    }

    function getMode() {
        return modeInputs.find((input) => input.checked)?.value || "single";
    }

    function setMode(mode) {
        modeInputs.forEach((input) => {
            input.checked = input.value === mode;
        });
        const multiMode = mode === "multi";
        singleWrap.hidden = multiMode;
        multiWrap.hidden = !multiMode;
    }

    function updatePreview(scope) {
        const effectiveScope = scope.length ? scope : ["1m"];
        const value = effectiveScope.join(",");
        hiddenInput.value = value;
        trainingMirror.value = effectiveScope[0] || "1m";
        if (previewNode) {
            previewNode.innerHTML = `submitted value: <code>${value}</code>`;
        }
    }

    function syncFromControls() {
        if (getMode() === "multi") {
            const scope = multiInputs.filter((input) => input.checked).map((input) => input.value);
            if (!scope.length) {
                multiInputs[0].checked = true;
                updatePreview([multiInputs[0].value]);
                return;
            }
            updatePreview(scope);
            return;
        }
        updatePreview([singleSelect.value || "1m"]);
    }

    const initialScope = normalizeTimeframes(hiddenInput.value);
    const effectiveInitialScope = initialScope.length ? initialScope : ["1m"];
    setMode(effectiveInitialScope.length > 1 ? "multi" : "single");
    singleSelect.value = effectiveInitialScope[0];
    multiInputs.forEach((input) => {
        input.checked = effectiveInitialScope.includes(input.value);
    });
    updatePreview(effectiveInitialScope);
    modeInputs.forEach((input) => {
        input.addEventListener("change", () => {
            setMode(input.value);
            syncFromControls();
        });
    });
    singleSelect.addEventListener("change", syncFromControls);
    multiInputs.forEach((input) => {
        input.addEventListener("change", syncFromControls);
    });
})();

/* ---- block ---- */

(() => {
    const form = document.getElementById("backtest-run-form");
    if (!form) {
        return;
    }
    const csvMirror = form.querySelector('input[name="selected_features_csv"]');
    const legacyMirror = form.querySelector('input[name="feature_names"]');
    const countHost = document.getElementById("backtest-feature-selection-count");
    const featureInputs = Array.from(form.querySelectorAll('input[name="selected_features"]'));
    if (!csvMirror || !legacyMirror || !featureInputs.length) {
        return;
    }

    function syncSelectedFeatures() {
        const selected = featureInputs
            .filter((input) => input.checked)
            .map((input) => String(input.value || "").trim())
            .filter(Boolean);
        const csv = selected.join(",");
        csvMirror.value = csv;
        legacyMirror.value = csv;
        if (countHost) {
            countHost.textContent = String(selected.length);
        }
    }

    featureInputs.forEach((input) => {
        input.addEventListener("change", syncSelectedFeatures);
    });
    form.addEventListener("submit", syncSelectedFeatures);
    syncSelectedFeatures();
})();
