const state = {
  treeIndex: 0,
  nodes: [],
  edges: [],
  selected: null,
  selectedTraceId: null,
  query: "",
  scale: 1,
  offsetX: 0,
  offsetY: 0,
  panning: null
};

const svg = document.getElementById("graph");
const treeTabs = document.getElementById("treeTabs");
const traceList = document.getElementById("traceList");
const searchBox = document.getElementById("searchBox");
const fitBtn = document.getElementById("fitBtn");
const resetBtn = document.getElementById("resetBtn");
const detailTitle = document.getElementById("detailTitle");
const detailBody = document.getElementById("detailBody");
const emptyState = document.getElementById("emptyState");
const graphLayer = document.createElementNS("http://www.w3.org/2000/svg", "g");
const edgeLayer = document.createElementNS("http://www.w3.org/2000/svg", "g");
const nodeLayer = document.createElementNS("http://www.w3.org/2000/svg", "g");
graphLayer.append(edgeLayer, nodeLayer);
svg.append(graphLayer);

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[ch]));
}

function applyTransform() {
  graphLayer.setAttribute("transform", `translate(${state.offsetX} ${state.offsetY}) scale(${state.scale})`);
}

function treeLabel(tree, index) {
  const id = tree?.id || `tree-${index + 1}`;
  const name = tree?.name ? ` · ${tree.name}` : "";
  return `${id}${name}`;
}

function traces() {
  return Array.isArray(FAILURE_MODE_VIEW_DATA.traces) ? FAILURE_MODE_VIEW_DATA.traces : [];
}

function selectedTrace() {
  if (!state.selectedTraceId) return null;
  return currentTraces().find(trace => trace.trace_id === state.selectedTraceId) || null;
}

function currentTreeModeIds() {
  return new Set(state.nodes.map(node => node.id).filter(Boolean));
}

function scopedTraceLogs(trace) {
  const modeIds = currentTreeModeIds();
  return (trace?.logs || []).filter(log => modeIds.has(log.failure_mode_id));
}

function traceInCurrentTree(trace) {
  return scopedTraceLogs(trace).length > 0;
}

function currentTraces() {
  return traces().filter(traceInCurrentTree);
}

function traceModeIds(trace) {
  return new Set(scopedTraceLogs(trace).map(log => log.failure_mode_id).filter(Boolean));
}

function traceEdgeKeys(trace) {
  const keys = new Set();
  const logs = scopedTraceLogs(trace);
  for (let index = 0; index + 1 < logs.length; index += 1) {
    const src = logs[index].failure_mode_id;
    const dst = logs[index + 1].failure_mode_id;
    if (src && dst) keys.add(`${src}->${dst}`);
  }
  return keys;
}

function traceMatchesQuery(trace) {
  if (!state.query) return true;
  const logs = scopedTraceLogs(trace);
  const text = [
    trace.trace_id,
    trace.start_time,
    trace.end_time,
    ...logs.flatMap(log => [log.failure_mode_id, log.message, log.pod_name, log.cluster_name])
  ].join(" ").toLowerCase();
  return text.includes(state.query);
}

function flattenTree(root) {
  const nodes = [];
  const edges = [];
  let leafIndex = 0;
  let maxDepth = 0;

  function visit(node, depth, parentUid, siblingIndex, path) {
    const uid = `${path}/${siblingIndex}:${node.id || "unknown"}`;
    const children = Array.isArray(node.children) ? node.children : [];
    const current = {...node, uid, depth, childrenCount: children.length, x: 0, y: 70 + depth * 120};
    nodes.push(current);
    maxDepth = Math.max(maxDepth, depth + 1);
    if (parentUid) {
      edges.push({src: parentUid, dst: uid});
    }

    if (!children.length) {
      current.x = 80 + leafIndex * 280;
      leafIndex += 1;
    } else {
      const childXs = children.map((child, index) => visit(child, depth + 1, uid, index, uid));
      current.x = childXs.reduce((sum, value) => sum + value, 0) / childXs.length;
    }
    return current.x;
  }

  if (root) {
    visit(root, 0, null, 0, "root");
  }
  return {nodes, edges, maxDepth};
}

function edgePath(src, dst) {
  const x1 = src.x + 115;
  const y1 = src.y + 64;
  const x2 = dst.x + 115;
  const y2 = dst.y;
  const mid = (y1 + y2) / 2;
  return `M ${x1} ${y1} C ${x1} ${mid}, ${x2} ${mid}, ${x2} ${y2}`;
}

function matchesQuery(node) {
  if (!state.query) return true;
  return [node.id, node.name].join(" ").toLowerCase().includes(state.query);
}

function renderTabs() {
  const trees = FAILURE_MODE_VIEW_DATA.trees || [];
  treeTabs.textContent = "";
  trees.forEach((tree, index) => {
    const button = document.createElement("button");
    button.className = `tab${index === state.treeIndex ? " active" : ""}`;
    button.type = "button";
    button.textContent = treeLabel(tree, index);
    button.addEventListener("click", () => {
      state.treeIndex = index;
      state.selected = null;
      state.selectedTraceId = null;
      state.query = "";
      searchBox.value = "";
      loadTree();
    });
    treeTabs.append(button);
  });
}

function renderTraceList() {
  traceList.textContent = "";
  const visibleTraces = currentTraces().filter(traceMatchesQuery);
  if (!visibleTraces.length) {
    const empty = document.createElement("div");
    empty.className = "empty-traces";
    empty.textContent = "No traces";
    traceList.append(empty);
    return;
  }

  visibleTraces.forEach(trace => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `trace-item${trace.trace_id === state.selectedTraceId ? " active" : ""}`;
    button.innerHTML = `
      <strong>${esc(trace.trace_id || "(empty)")}</strong>
    `;
    button.addEventListener("click", () => {
      state.selectedTraceId = trace.trace_id;
      state.selected = null;
      showTrace(trace);
      renderTraceList();
      render();
    });
    traceList.append(button);
  });
}

function render() {
  edgeLayer.textContent = "";
  nodeLayer.textContent = "";
  const byUid = new Map(state.nodes.map(node => [node.uid, node]));
  const related = new Set();
  const trace = selectedTrace();
  const traceModes = traceModeIds(trace);
  const traceEdges = traceEdgeKeys(trace);
  if (state.selected) {
    related.add(state.selected.uid);
    state.edges.forEach(edge => {
      if (edge.src === state.selected.uid) related.add(edge.dst);
      if (edge.dst === state.selected.uid) related.add(edge.src);
    });
  }

  for (const edge of state.edges) {
    const src = byUid.get(edge.src);
    const dst = byUid.get(edge.dst);
    if (!src || !dst) continue;
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    const selected = state.selected && (edge.src === state.selected.uid || edge.dst === state.selected.uid);
    const inTrace = traceEdges.has(`${src.id}->${dst.id}`);
    const dim = trace && !inTrace;
    path.setAttribute("class", `edge${selected ? " selected" : ""}${inTrace ? " trace" : ""}${dim ? " dim" : ""}`);
    path.setAttribute("d", edgePath(src, dst));
    edgeLayer.append(path);
  }

  for (const node of state.nodes) {
    const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    const selected = state.selected?.uid === node.uid;
    const inTrace = traceModes.has(node.id);
    const dim = (state.selected && !related.has(node.uid)) || !matchesQuery(node) || (trace && !inTrace);
    group.setAttribute("class", `node${selected ? " selected" : ""}${inTrace ? " trace" : ""}${dim ? " dim" : ""}`);
    group.setAttribute("transform", `translate(${node.x} ${node.y})`);

    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("width", 230);
    rect.setAttribute("height", 64);
    rect.setAttribute("rx", 6);

    const idText = document.createElementNS("http://www.w3.org/2000/svg", "text");
    idText.setAttribute("class", "id");
    idText.setAttribute("x", 14);
    idText.setAttribute("y", 21);
    idText.textContent = node.id || "(unknown)";

    const nameText = document.createElementNS("http://www.w3.org/2000/svg", "text");
    nameText.setAttribute("class", "name");
    nameText.setAttribute("x", 14);
    nameText.setAttribute("y", 41);
    nameText.textContent = String(node.name || "").slice(0, 26);

    const hitText = document.createElementNS("http://www.w3.org/2000/svg", "text");
    hitText.setAttribute("class", "hit");
    hitText.setAttribute("x", 164);
    hitText.setAttribute("y", 21);
    hitText.textContent = `${Number(node.hit_count) || 0} hits`;

    const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
    title.textContent = `${node.id || ""} ${node.name || ""}`;

    group.append(title, rect, idText, nameText, hitText);
    group.addEventListener("click", event => {
      event.stopPropagation();
      state.selected = node;
      state.selectedTraceId = null;
      showNode(node);
      renderTraceList();
      render();
    });
    nodeLayer.append(group);
  }

  emptyState.style.display = state.nodes.length ? "none" : "flex";
  renderTraceList();
  applyTransform();
}

function showNode(node) {
  const logs = Array.isArray(node.log_infos) ? node.log_infos : [];
  const logRows = logs.length ? logs.map(log => `
    <div class="log-row">
      <div class="log-fields">
        <div class="log-field"><span>Time</span><strong>${esc(log.time)}</strong></div>
        <div class="log-field"><span>Pod</span><strong>${esc(log.pod_name)}</strong></div>
        <div class="log-field"><span>PID</span><strong>${esc(log.pid)}</strong></div>
        <div class="log-field"><span>TID</span><strong>${esc(log.tid)}</strong></div>
        <div class="log-field"><span>Trace ID</span><strong>${esc(log.trace_id)}</strong></div>
        <div class="log-field"><span>Cluster</span><strong>${esc(log.cluster_name)}</strong></div>
        <div class="log-field"><span>Message</span><strong>${esc(log.message)}</strong></div>
      </div>
    </div>
  `).join("") : `<div class="empty-logs">No matched logs.</div>`;

  detailTitle.textContent = "Failure Mode";
  detailBody.innerHTML = `
    <div class="kv"><span>ID</span><strong>${esc(node.id)}</strong></div>
    <div class="kv"><span>Name</span><strong>${esc(node.name)}</strong></div>
    <div class="kv"><span>Hit count</span><strong>${esc(node.hit_count)}</strong></div>
    <div class="kv"><span>Root cause</span><div>${esc(node.cause || "None")}</div></div>
    <div class="kv"><span>Suggestion</span><div>${esc(node.suggestion || "None")}</div></div>
    <div class="kv"><span>Validation</span><div>${esc(node.validation || "None")}</div></div>
    <div class="kv"><span>Matched logs</span><div class="log-list">${logRows}</div></div>
  `;
}

function showTrace(trace) {
  const logs = scopedTraceLogs(trace);
  const rows = logs.length ? logs.map((log, index) => `
    <div class="trace-step">
      <div class="step-index">${index + 1}</div>
      <div class="step-body">
        <strong>${esc(log.failure_mode_id || "(unknown)")}</strong>
        <span>${esc(log.time || "")}</span>
        <p>${esc(log.message || "")}</p>
        <small>${esc(log.pod_name || "")} · ${esc(log.pid || "")}:${esc(log.tid || "")} · ${esc(log.cluster_name || "")}</small>
      </div>
    </div>
  `).join("") : `<div class="empty-logs">No trace logs.</div>`;

  detailTitle.textContent = "Trace";
  detailBody.innerHTML = `
    <div class="kv"><span>Trace ID</span><strong>${esc(trace.trace_id)}</strong></div>
    <div class="kv"><span>Start</span><strong>${esc(trace.start_time || "")}</strong></div>
    <div class="kv"><span>End</span><strong>${esc(trace.end_time || "")}</strong></div>
    <div class="kv"><span>Duration</span><strong>${esc(trace.duration_us || 0)} us</strong></div>
    <div class="kv"><span>Failure path</span><div class="trace-steps">${rows}</div></div>
  `;
}

function showOverview() {
  const tree = (FAILURE_MODE_VIEW_DATA.trees || [])[state.treeIndex];
  detailTitle.textContent = "Tree";
  detailBody.innerHTML = `
    <div class="kv"><span>Root</span><strong>${esc(treeLabel(tree, state.treeIndex))}</strong></div>
    <div class="kv"><span>Traces</span><strong>${esc(currentTraces().length)}</strong></div>
    <div class="kv"><span>Details</span><div>Select a node to inspect root cause, suggestion, validation method, and matched logs.</div></div>
  `;
}

function fit() {
  const rect = svg.getBoundingClientRect();
  if (!state.nodes.length) {
    state.scale = 1;
    state.offsetX = 0;
    state.offsetY = 0;
    applyTransform();
    return;
  }

  const minX = Math.min(...state.nodes.map(node => node.x));
  const minY = Math.min(...state.nodes.map(node => node.y));
  const maxX = Math.max(...state.nodes.map(node => node.x + 250));
  const maxY = Math.max(...state.nodes.map(node => node.y + 90));
  const graphWidth = Math.max(1, maxX - minX);
  const graphHeight = Math.max(1, maxY - minY);
  state.scale = Math.min(1.25, Math.max(0.18, Math.min(rect.width / (graphWidth + 80), rect.height / (graphHeight + 80))));
  state.offsetX = rect.width / 2 - ((minX + maxX) / 2) * state.scale;
  state.offsetY = rect.height / 2 - ((minY + maxY) / 2) * state.scale;
  applyTransform();
}

function reset() {
  fit();
}

function resizeViewBox() {
  const rect = svg.getBoundingClientRect();
  svg.setAttribute("viewBox", `0 0 ${Math.max(1, rect.width)} ${Math.max(1, rect.height)}`);
}

function loadTree() {
  renderTabs();
  const tree = (FAILURE_MODE_VIEW_DATA.trees || [])[state.treeIndex];
  const flattened = flattenTree(tree);
  state.nodes = flattened.nodes;
  state.edges = flattened.edges;
  state.selected = null;
  state.selectedTraceId = null;
  showOverview();
  render();
  fit();
}

searchBox.addEventListener("input", () => {
  state.query = searchBox.value.trim().toLowerCase();
  render();
});
fitBtn.addEventListener("click", fit);
resetBtn.addEventListener("click", reset);
svg.addEventListener("click", () => {
  state.selected = null;
  state.selectedTraceId = null;
  showOverview();
  render();
});
svg.addEventListener("wheel", event => {
  event.preventDefault();
  const delta = event.deltaY > 0 ? 0.9 : 1.1;
  state.scale = Math.max(0.12, Math.min(2.8, state.scale * delta));
  applyTransform();
}, {passive: false});
svg.addEventListener("pointerdown", event => {
  if (event.target.closest(".node")) return;
  state.panning = {x: event.clientX, y: event.clientY, ox: state.offsetX, oy: state.offsetY};
  svg.classList.add("panning");
  svg.setPointerCapture(event.pointerId);
});
svg.addEventListener("pointermove", event => {
  if (!state.panning) return;
  state.offsetX = state.panning.ox + event.clientX - state.panning.x;
  state.offsetY = state.panning.oy + event.clientY - state.panning.y;
  applyTransform();
});
svg.addEventListener("pointerup", event => {
  state.panning = null;
  svg.classList.remove("panning");
  if (svg.hasPointerCapture(event.pointerId)) {
    svg.releasePointerCapture(event.pointerId);
  }
});
window.addEventListener("resize", () => {
  resizeViewBox();
  fit();
});

resizeViewBox();
loadTree();
