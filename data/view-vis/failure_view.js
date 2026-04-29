const state = {
  view: null,
  viewIndex: 0,
  mode: "callGraph",
  nodes: [],
  edges: [],
  visible: new Set(),
  selected: null,
  scale: 1,
  offsetX: 0,
  offsetY: 0,
  query: "",
  dragging: null,
  panning: null
};

const svg = document.getElementById("graph");
const resourceView = document.getElementById("resourceView");
const callGraphTab = document.getElementById("callGraphTab");
const resourceTab = document.getElementById("resourceTab");
const viewSelect = document.getElementById("viewSelect");
const searchBox = document.getElementById("searchBox");
const detailTitle = document.getElementById("detailTitle");
const detailBody = document.getElementById("detailBody");
const emptyState = document.getElementById("emptyState");
const graphLayer = document.createElementNS("http://www.w3.org/2000/svg", "g");
const edgeLayer = document.createElementNS("http://www.w3.org/2000/svg", "g");
const nodeLayer = document.createElementNS("http://www.w3.org/2000/svg", "g");
graphLayer.append(edgeLayer, nodeLayer);
svg.append(graphLayer);

const markerDefs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
markerDefs.innerHTML = `
  <marker id="callEdgeArrow" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto" markerUnits="strokeWidth">
    <path d="M 0 0 L 10 4 L 0 8 z" fill="#9aa8bb"></path>
  </marker>
  <marker id="callEdgeArrowSelected" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto" markerUnits="strokeWidth">
    <path d="M 0 0 L 10 4 L 0 8 z" fill="#b45309"></path>
  </marker>
`;
svg.prepend(markerDefs);

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[ch]));
}

function fmtRatio(value) {
  return `${Math.round((Number(value) || 0) * 1000) / 10}%`;
}

function valueText(value) {
  return value === null || value === undefined || value === "" ? "(null)" : String(value);
}

function errorCodeLabel(node) {
  return `[${valueText(node.error_code)}]`;
}

function colorFor(component) {
  const palette = ["#0f766e", "#2563eb", "#7c3aed", "#c2410c", "#be123c", "#047857", "#4338ca", "#a16207"];
  let hash = 0;
  for (const ch of String(component || "unknown")) {
    hash = ((hash << 5) - hash + ch.charCodeAt(0)) | 0;
  }
  return palette[Math.abs(hash) % palette.length];
}

function radiusFor(node) {
  return 9 + Math.min(18, Math.sqrt(Number(node.hit_count) || 1) * 4);
}

function componentOrder(component) {
  const order = ["ubsocket", "umq", "liburma", "libudma", "urmacore", "udmacore"];
  const index = order.indexOf(String(component || "").toLowerCase());
  return index === -1 ? order.length : index;
}

function edgeEndpoint(src, dst) {
  const dx = dst.x - src.x;
  const dy = dst.y - src.y;
  const dist = Math.sqrt(dx * dx + dy * dy) || 1;
  const srcRadius = radiusFor(src) + 3;
  const dstRadius = radiusFor(dst) + 7;
  return {
    x1: src.x + dx / dist * srcRadius,
    y1: src.y + dy / dist * srcRadius,
    x2: dst.x - dx / dist * dstRadius,
    y2: dst.y - dy / dist * dstRadius
  };
}

function edgePathD(src, dst, edge) {
  const {x1, y1, x2, y2} = edgeEndpoint(src, dst);
  if (Math.abs(y2 - y1) < 8) {
    return {d: `M ${x1} ${y1} L ${x2} ${y2}`, labelX: (x1 + x2) / 2, labelY: y1 - 8};
  }
  const midY = (y1 + y2) / 2;
  const bend = (String(edge.src) + String(edge.dst)).length % 2 === 0 ? 24 : -24;
  return {
    d: `M ${x1} ${y1} C ${x1 + bend} ${midY}, ${x2 - bend} ${midY}, ${x2} ${y2}`,
    labelX: (x1 + x2) / 2 + bend,
    labelY: midY - 7
  };
}

function applyTransform() {
  graphLayer.setAttribute("transform", `translate(${state.offsetX} ${state.offsetY}) scale(${state.scale})`);
}

function resizeViewBox() {
  const rect = svg.getBoundingClientRect();
  svg.setAttribute("viewBox", `0 0 ${Math.max(1, rect.width)} ${Math.max(1, rect.height)}`);
}

function expandNode(nodeId) {
  state.visible.add(nodeId);
  for (const edge of state.edges) {
    if (edge.src === nodeId) state.visible.add(edge.dst);
    if (edge.dst === nodeId) state.visible.add(edge.src);
  }
}

function focusNode(nodeId) {
  const keep = new Set([nodeId]);
  for (const edge of state.edges) {
    if (edge.src === nodeId) keep.add(edge.dst);
    if (edge.dst === nodeId) keep.add(edge.src);
  }
  state.visible = keep;
}

function selectInitialVisible() {
  state.visible.clear();
  state.nodes.forEach(node => state.visible.add(node.id));
}

function simulateLayout() {
  const rect = svg.getBoundingClientRect();
  const groups = new Map();
  for (const node of state.nodes) {
    const key = node.component || "unknown";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(node);
  }
  const components = [...groups.keys()].sort((a, b) => {
    const orderDiff = componentOrder(a) - componentOrder(b);
    if (orderDiff !== 0) return orderDiff;
    return String(a).localeCompare(String(b));
  });

  const left = 210;
  const top = 90;
  const rowGap = 118;
  const colGap = 210;
  for (const [row, component] of components.entries()) {
    const nodes = groups.get(component).sort((a, b) => String(a.id).localeCompare(String(b.id)));
    nodes.forEach((node, index) => {
      node.x = left + index * colGap;
      node.y = top + row * rowGap;
      node.vx = 0;
      node.vy = 0;
    });
  }

  const maxGroupSize = Math.max(1, ...[...groups.values()].map(nodes => nodes.length));
  const minWidth = Math.max(rect.width, left + maxGroupSize * colGap + 240);
  const minHeight = Math.max(rect.height, top + Math.max(1, components.length) * rowGap + 120);
  svg.setAttribute("viewBox", `0 0 ${minWidth} ${minHeight}`);
}

function sortedComponents() {
  return [...new Set(state.nodes.map(node => node.component || "unknown"))].sort((a, b) => {
    const orderDiff = componentOrder(a) - componentOrder(b);
    if (orderDiff !== 0) return orderDiff;
    return String(a).localeCompare(String(b));
  });
}

function renderComponentLabels() {
  sortedComponents().forEach((component, index) => {
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("class", "component-label");
    text.setAttribute("x", 34);
    text.setAttribute("y", 94 + index * 118);
    text.textContent = component;
    nodeLayer.append(text);
  });
}

function renderLegend() {
  const components = [...new Set(state.nodes.map(node => node.component || "unknown"))].sort();
  document.getElementById("legend").innerHTML = components.slice(0, 12).map(component => `
    <div class="legend-row"><span class="swatch" style="background:${colorFor(component)}"></span>${esc(component)}</div>
  `).join("");
}

function matchesQuery(node) {
  if (!state.query) return true;
  return [node.id, node.function_name, node.component, node.error_code].join(" ").toLowerCase().includes(state.query);
}

function visibleEdge(edge) {
  return state.visible.has(edge.src) && state.visible.has(edge.dst);
}

function render() {
  if (state.mode !== "callGraph") {
    return;
  }
  edgeLayer.textContent = "";
  nodeLayer.textContent = "";
  renderComponentLabels();

  const byId = new Map(state.nodes.map(node => [node.id, node]));
  const highlighted = state.selected?.type === "node" ? state.selected.id : null;
  const related = new Set();
  if (highlighted) {
    related.add(highlighted);
    state.edges.forEach(edge => {
      if (edge.src === highlighted) related.add(edge.dst);
      if (edge.dst === highlighted) related.add(edge.src);
    });
  }

  for (const edge of state.edges.filter(visibleEdge)) {
    const src = byId.get(edge.src);
    const dst = byId.get(edge.dst);
    if (!src || !dst) continue;
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    const selected = state.selected?.type === "edge" && state.selected.edge === edge;
    const dim = highlighted && edge.src !== highlighted && edge.dst !== highlighted;
    const edgeShape = edgePathD(src, dst, edge);
    path.setAttribute("class", `edge${selected ? " selected" : ""}${dim ? " dim" : ""}`);
    path.setAttribute("d", edgeShape.d);
    path.setAttribute("stroke-width", 1.4 + Math.min(7, Math.sqrt(Number(edge.hit_count) || 1)));
    path.setAttribute("marker-end", selected ? "url(#callEdgeArrowSelected)" : "url(#callEdgeArrow)");
    path.addEventListener("click", event => {
      event.stopPropagation();
      state.selected = {type: "edge", edge};
      showEdge(edge);
      render();
    });
    edgeLayer.append(path);

    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("class", `edge-label${dim ? " dim" : ""}`);
    label.setAttribute("x", edgeShape.labelX);
    label.setAttribute("y", edgeShape.labelY);
    label.setAttribute("text-anchor", "middle");
    label.textContent = `${edge.hit_count} · ${fmtRatio(edge.ratio)}`;
    edgeLayer.append(label);
  }

  const visibleNodes = state.nodes.filter(node => state.visible.has(node.id));
  for (const node of visibleNodes) {
    const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    const selected = state.selected?.type === "node" && state.selected.id === node.id;
    const dim = (highlighted && !related.has(node.id)) || !matchesQuery(node);
    group.setAttribute("class", `node${selected ? " selected" : ""}${dim ? " dim" : ""}`);
    group.setAttribute("transform", `translate(${node.x} ${node.y})`);

    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("r", radiusFor(node));
    circle.setAttribute("fill", colorFor(node.component));

    const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
    title.textContent = node.id;

    const nameText = document.createElementNS("http://www.w3.org/2000/svg", "text");
    nameText.setAttribute("class", "name");
    nameText.setAttribute("x", radiusFor(node) + 7);
    nameText.setAttribute("y", -2);
    nameText.textContent = node.function_name || node.id;

    group.append(title, circle, nameText);
    const errorText = document.createElementNS("http://www.w3.org/2000/svg", "text");
    errorText.setAttribute("class", "error-code");
    errorText.setAttribute("x", radiusFor(node) + 7);
    errorText.setAttribute("y", 14);
    errorText.textContent = errorCodeLabel(node);
    group.append(errorText);
    group.addEventListener("click", event => {
      event.stopPropagation();
      state.selected = {type: "node", id: node.id};
      expandNode(node.id);
      showNode(node);
      render();
    });
    group.addEventListener("dblclick", event => {
      event.stopPropagation();
      state.selected = {type: "node", id: node.id};
      focusNode(node.id);
      showNode(node);
      render();
      fit();
    });
    group.addEventListener("pointerdown", event => {
      state.dragging = {node, sx: event.clientX, sy: event.clientY, ox: node.x, oy: node.y};
      group.setPointerCapture(event.pointerId);
    });
    nodeLayer.append(group);
  }

  document.getElementById("nodeCount").textContent = state.nodes.length;
  document.getElementById("edgeCount").textContent = state.edges.length;
  document.getElementById("visibleCount").textContent = visibleNodes.length;
  document.getElementById("maxHit").textContent = Math.max(0, ...state.nodes.map(node => Number(node.hit_count) || 0));
  emptyState.style.display = state.nodes.length ? "none" : "flex";
  applyTransform();
}

function nodePill(edge, nodeId) {
  return `<div class="pill" data-node="${esc(nodeId)}">${esc(nodeId)} · ${esc(edge.hit_count)} · ${fmtRatio(edge.ratio)}</div>`;
}

function bindNodePills() {
  detailBody.querySelectorAll("[data-node]").forEach(el => {
    el.addEventListener("click", () => {
      const node = state.nodes.find(item => item.id === el.dataset.node);
      if (!node) return;
      state.selected = {type: "node", id: node.id};
      expandNode(node.id);
      showNode(node);
      render();
    });
  });
}

function showNode(node) {
  const upstream = state.edges.filter(edge => edge.dst === node.id);
  const downstream = state.edges.filter(edge => edge.src === node.id);
  detailTitle.textContent = "Node";
  detailBody.innerHTML = `
    <div class="kv"><span>ID</span><strong>${esc(node.id)}</strong></div>
    <div class="kv"><span>Function</span><strong>${esc(node.function_name)}</strong></div>
    <div class="kv"><span>Component</span><strong>${esc(node.component || "unknown")}</strong></div>
    <div class="kv"><span>Error code</span><strong>${esc(node.error_code ?? "null")}</strong></div>
    <div class="kv"><span>Hit count</span><strong>${esc(node.hit_count)}</strong></div>
    <div class="kv"><span>Downstream</span><div class="list">${downstream.map(edge => nodePill(edge, edge.dst)).join("") || "None"}</div></div>
    <div class="kv"><span>Upstream</span><div class="list">${upstream.map(edge => nodePill(edge, edge.src)).join("") || "None"}</div></div>
  `;
  bindNodePills();
}

function showEdge(edge) {
  detailTitle.textContent = "Edge";
  detailBody.innerHTML = `
    <div class="kv"><span>Source</span><strong>${esc(edge.src)}</strong></div>
    <div class="kv"><span>Destination</span><strong>${esc(edge.dst)}</strong></div>
    <div class="kv"><span>Hit count</span><strong>${esc(edge.hit_count)}</strong></div>
    <div class="kv"><span>Ratio</span><strong>${fmtRatio(edge.ratio)}</strong></div>
  `;
}

function showOverview() {
  detailTitle.textContent = "Details";
  detailBody.innerHTML = `
    <div class="kv"><span>Top function</span><strong>${esc(state.view?.top_function ?? "null")}</strong></div>
    <div class="kv"><span>Interaction</span><strong>Click a node or edge to inspect it. Double click a node to focus one-hop neighborhood.</strong></div>
  `;
}

function resourceViewForCurrentIndex() {
  return (FAILURE_VIEW_DATA.resource_views || [])[state.viewIndex] || {tids: []};
}

function countResourceItems(view) {
  let tids = 0;
  let eids = 0;
  let jetties = 0;
  let remoteJetties = 0;
  let remoteEids = 0;
  for (const tid of view.tids || []) {
    tids += 1;
    for (const eid of tid.eids || []) {
      eids += 1;
      for (const jetty of eid.jetty_ids || []) {
        jetties += 1;
        for (const remoteJetty of jetty.remote_jetty_ids || []) {
          remoteJetties += 1;
          remoteEids += (remoteJetty.remote_eids || []).length;
        }
      }
    }
  }
  return {tids, eids, jetties, remoteJetties, remoteEids};
}

function setMetricValues(values) {
  document.getElementById("nodeCount").textContent = values.first;
  document.getElementById("edgeCount").textContent = values.second;
  document.getElementById("visibleCount").textContent = values.third;
  document.getElementById("maxHit").textContent = values.fourth;
}


function resourceTypeLabel(type) {
  return {
    top_function: "Top Function",
    tid: "TID",
    eid: "EID",
    jetty: "Jetty",
    remote_jetty: "Remote Jetty",
    remote_eid: "Remote EID"
  }[type] || type;
}

function resourceNodeId(type, value) {
  return `${type}:${valueText(value)}`;
}

function resourceNodeColor(type) {
  return {
    top_function: "#111827",
    tid: "#2563eb",
    eid: "#0f766e",
    jetty: "#7c3aed",
    remote_jetty: "#c2410c",
    remote_eid: "#be123c"
  }[type] || "#667085";
}

function addResourceNode(nodeMap, type, value, extra = {}) {
  const id = resourceNodeId(type, value);
  if (!nodeMap.has(id)) {
    nodeMap.set(id, {
      id,
      type,
      value,
      hitCount: 0,
      ratio: null,
      refCount: 0,
      parents: new Set(),
      children: new Set()
    });
  }
  const node = nodeMap.get(id);
  node.hitCount += Number(extra.hitCount || 0);
  node.refCount += 1;
  if (extra.ratio !== undefined && extra.ratio !== null) {
    node.ratio = node.ratio === null ? Number(extra.ratio) : Math.max(node.ratio, Number(extra.ratio));
  }
  return node;
}

function addResourceEdge(edgeMap, src, dst, type, hitCount = 1) {
  const key = `${src.id}->${dst.id}`;
  if (!edgeMap.has(key)) {
    edgeMap.set(key, {src: src.id, dst: dst.id, type, hitCount: 0});
  }
  const edge = edgeMap.get(key);
  edge.hitCount += Number(hitCount || 1);
  src.children.add(dst.id);
  dst.parents.add(src.id);
  return edge;
}

function buildResourceGraph(view) {
  const nodeMap = new Map();
  const edgeMap = new Map();
  const topFunctionNode = addResourceNode(nodeMap, "top_function", view.top_function ?? state.view?.top_function ?? "(null)");

  for (const tid of view.tids || []) {
    const tidNode = addResourceNode(nodeMap, "tid", tid.tid, {hitCount: tid.hit_count, ratio: tid.ratio});
    addResourceEdge(edgeMap, topFunctionNode, tidNode, "top_function_tid", tid.hit_count);
    for (const eid of tid.eids || []) {
      const eidNode = addResourceNode(nodeMap, "eid", eid.eid, {hitCount: eid.hit_count, ratio: eid.ratio});
      addResourceEdge(edgeMap, tidNode, eidNode, "tid_eid", eid.hit_count);
      for (const jetty of eid.jetty_ids || []) {
        const jettyNode = addResourceNode(nodeMap, "jetty", jetty.jetty_id);
        addResourceEdge(edgeMap, eidNode, jettyNode, "eid_jetty", 1);
        for (const remoteJetty of jetty.remote_jetty_ids || []) {
          const remoteJettyNode = addResourceNode(nodeMap, "remote_jetty", remoteJetty.remote_jetty_id);
          addResourceEdge(edgeMap, jettyNode, remoteJettyNode, "jetty_remote_jetty", 1);
          for (const remoteEid of remoteJetty.remote_eids || []) {
            const remoteEidNode = addResourceNode(nodeMap, "remote_eid", remoteEid.remote_eid);
            addResourceEdge(edgeMap, remoteJettyNode, remoteEidNode, "remote_jetty_remote_eid", 1);
          }
        }
      }
    }
  }

  const levelByType = {top_function: 0, tid: 1, eid: 2, jetty: 3, remote_jetty: 4, remote_eid: 5};
  const nodes = [...nodeMap.values()].sort((a, b) => {
    const levelDiff = levelByType[a.type] - levelByType[b.type];
    if (levelDiff !== 0) return levelDiff;
    return valueText(a.value).localeCompare(valueText(b.value));
  });
  const levels = new Map();
  for (const node of nodes) {
    const level = levelByType[node.type] ?? 0;
    if (!levels.has(level)) levels.set(level, []);
    levels.get(level).push(node);
  }
  for (const [level, levelNodes] of levels) {
    levelNodes.forEach((node, index) => {
      node.x = 240 + level * 230;
      node.y = 60 + index * 86;
      node.width = node.type === "top_function" ? 54 : 172;
      node.height = 54;
    });
  }

  return {nodes, edges: [...edgeMap.values()], nodeById: nodeMap};
}

function resourceMeta(node) {
  const pieces = [];
  if (node.hitCount) pieces.push(`${node.hitCount} hits`);
  if (node.ratio !== null && node.ratio !== undefined) pieces.push(fmtRatio(node.ratio));
  if (node.refCount > 1) pieces.push(`${node.refCount} paths`);
  return pieces.join(" · ");
}

function showResourceNode(node) {
  detailTitle.textContent = "Resource Node";
  detailBody.innerHTML = `
    <div class="kv"><span>Type</span><strong>${esc(resourceTypeLabel(node.type))}</strong></div>
    <div class="kv"><span>ID</span><strong>${esc(valueText(node.value))}</strong></div>
    <div class="kv"><span>Hit count</span><strong>${esc(node.hitCount || 0)}</strong></div>
    <div class="kv"><span>Ratio</span><strong>${node.ratio === null || node.ratio === undefined ? "(null)" : fmtRatio(node.ratio)}</strong></div>
    <div class="kv"><span>Paths</span><strong>${esc(node.refCount)}</strong></div>
    <div class="kv"><span>Upstream</span><strong>${esc(node.parents.size)}</strong></div>
    <div class="kv"><span>Downstream</span><strong>${esc(node.children.size)}</strong></div>
  `;
}

function showResourceEdge(edge) {
  detailTitle.textContent = "Resource Edge";
  detailBody.innerHTML = `
    <div class="kv"><span>Source</span><strong>${esc(edge.src)}</strong></div>
    <div class="kv"><span>Destination</span><strong>${esc(edge.dst)}</strong></div>
    <div class="kv"><span>Type</span><strong>${esc(edge.type)}</strong></div>
    <div class="kv"><span>Hit count</span><strong>${esc(edge.hitCount)}</strong></div>
  `;
}

function renderResourceView() {
  const view = resourceViewForCurrentIndex();
  const counts = countResourceItems(view);
  const graph = buildResourceGraph(view);
  resourceView.textContent = "";

  const header = document.createElement("div");
  header.className = "resource-header";
  header.innerHTML = `
    <h2>${esc(view.top_function ?? state.view?.top_function ?? "(null)")}</h2>
    <span class="resource-meta">${graph.nodes.length} merged nodes · ${graph.edges.length} merged edges</span>
  `;

  if (!graph.nodes.length) {
    const empty = document.createElement("div");
    empty.className = "metric";
    empty.textContent = "No resource data";
    resourceView.append(header, empty);
  } else {
    const svgEl = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svgEl.setAttribute("class", "resource-svg");
    const maxX = Math.max(...graph.nodes.map(node => node.x + node.width)) + 80;
    const maxY = Math.max(...graph.nodes.map(node => node.y + node.height)) + 80;
    svgEl.setAttribute("viewBox", `0 0 ${maxX} ${maxY}`);

    const edgeLayerEl = document.createElementNS("http://www.w3.org/2000/svg", "g");
    const nodeLayerEl = document.createElementNS("http://www.w3.org/2000/svg", "g");
    svgEl.append(edgeLayerEl, nodeLayerEl);

    for (const edge of graph.edges) {
      const src = graph.nodeById.get(edge.src);
      const dst = graph.nodeById.get(edge.dst);
      if (!src || !dst) continue;
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      const x1 = src.x + src.width;
      const y1 = src.y + src.height / 2;
      const x2 = dst.x;
      const y2 = dst.y + dst.height / 2;
      const mid = Math.max(50, (x2 - x1) / 2);
      path.setAttribute("class", "resource-edge");
      path.setAttribute("d", `M ${x1} ${y1} C ${x1 + mid} ${y1}, ${x2 - mid} ${y2}, ${x2} ${y2}`);
      path.setAttribute("stroke-width", 1.4 + Math.min(5, Math.sqrt(edge.hitCount || 1)));
      path.addEventListener("click", event => {
        event.stopPropagation();
        resourceView.querySelectorAll(".selected").forEach(el => el.classList.remove("selected"));
        path.classList.add("selected");
        showResourceEdge(edge);
      });
      edgeLayerEl.append(path);
    }

    for (const node of graph.nodes) {
      const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
      group.setAttribute("class", `resource-node${node.type === "top_function" ? " root" : ""}`);
      group.setAttribute("transform", `translate(${node.x} ${node.y})`);

      const name = valueText(node.value);
      const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
      title.textContent = `${resourceTypeLabel(node.type)} ${valueText(node.value)}`;
      group.append(title);

      if (node.type === "top_function") {
        const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        circle.setAttribute("cx", node.width / 2);
        circle.setAttribute("cy", node.height / 2);
        circle.setAttribute("r", 18);
        circle.setAttribute("fill", resourceNodeColor(node.type));

        const nameText = document.createElementNS("http://www.w3.org/2000/svg", "text");
        nameText.setAttribute("class", "name");
        nameText.setAttribute("x", -10);
        nameText.setAttribute("y", node.height / 2 + 4);
        nameText.setAttribute("text-anchor", "end");
        nameText.textContent = name.length > 22 ? `${name.slice(0, 21)}...` : name;
        group.append(circle, nameText);
      } else {
        const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        rect.setAttribute("width", node.width);
        rect.setAttribute("height", node.height);
        rect.setAttribute("rx", 6);

        const stripe = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        stripe.setAttribute("width", 6);
        stripe.setAttribute("height", node.height);
        stripe.setAttribute("rx", 3);
        stripe.setAttribute("fill", resourceNodeColor(node.type));

        const typeText = document.createElementNS("http://www.w3.org/2000/svg", "text");
        typeText.setAttribute("class", "type");
        typeText.setAttribute("x", 16);
        typeText.setAttribute("y", 18);
        typeText.textContent = resourceTypeLabel(node.type);

        const nameText = document.createElementNS("http://www.w3.org/2000/svg", "text");
        nameText.setAttribute("class", "name");
        nameText.setAttribute("x", 16);
        nameText.setAttribute("y", 35);
        nameText.textContent = name.length > 18 ? `${name.slice(0, 17)}...` : name;

        const metaText = document.createElementNS("http://www.w3.org/2000/svg", "text");
        metaText.setAttribute("class", "meta");
        metaText.setAttribute("x", 16);
        metaText.setAttribute("y", 49);
        metaText.textContent = resourceMeta(node);
        group.append(rect, stripe, typeText, nameText, metaText);
      }
      group.addEventListener("click", event => {
        event.stopPropagation();
        resourceView.querySelectorAll(".selected").forEach(el => el.classList.remove("selected"));
        group.classList.add("selected");
        showResourceNode(node);
      });
      nodeLayerEl.append(group);
    }

    resourceView.append(header, svgEl);
  }

  setMetricValues({
    first: graph.nodes.length,
    second: graph.edges.length,
    third: counts.tids,
    fourth: counts.remoteEids
  });
  detailTitle.textContent = "Resource";
  detailBody.innerHTML = `
    <div class="kv"><span>Top function</span><strong>${esc(view.top_function ?? state.view?.top_function ?? "null")}</strong></div>
    <div class="kv"><span>Merged nodes</span><strong>${esc(graph.nodes.length)}</strong></div>
    <div class="kv"><span>Merged edges</span><strong>${esc(graph.edges.length)}</strong></div>
    <div class="kv"><span>Raw TIDs</span><strong>${esc(counts.tids)}</strong></div>
    <div class="kv"><span>Raw remote EIDs</span><strong>${esc(counts.remoteEids)}</strong></div>
  `;
}

function setMode(mode) {
  state.mode = mode;
  callGraphTab.classList.toggle("active", mode === "callGraph");
  resourceTab.classList.toggle("active", mode === "resource");
  svg.classList.toggle("hidden", mode !== "callGraph");
  resourceView.classList.toggle("hidden", mode !== "resource");
  document.getElementById("fitBtn").disabled = mode !== "callGraph";

  if (mode === "resource") {
    emptyState.style.display = "none";
    renderResourceView();
  } else {
    showOverview();
    render();
    fit();
  }
}

function fit() {
  const nodes = state.nodes.filter(node => state.visible.has(node.id));
  if (!nodes.length) return;
  const rect = svg.getBoundingClientRect();
  const minX = Math.min(...nodes.map(node => node.x));
  const maxX = Math.max(...nodes.map(node => node.x));
  const minY = Math.min(...nodes.map(node => node.y));
  const maxY = Math.max(...nodes.map(node => node.y));
  const width = Math.max(80, maxX - minX);
  const height = Math.max(80, maxY - minY);
  state.scale = Math.min(2.2, Math.max(0.25, Math.min((rect.width - 70) / width, (rect.height - 70) / height)));
  state.offsetX = rect.width / 2 - ((minX + maxX) / 2) * state.scale;
  state.offsetY = rect.height / 2 - ((minY + maxY) / 2) * state.scale;
  applyTransform();
}

function loadView(index) {
  state.viewIndex = index;
  state.view = FAILURE_VIEW_DATA.callstack_views[index] || {nodes: [], edges: []};
  state.nodes = (state.view.nodes || []).map(node => ({...node}));
  state.edges = (state.view.edges || []).map(edge => ({...edge}));
  state.selected = null;
  resizeViewBox();
  simulateLayout();
  selectInitialVisible();
  renderLegend();
  if (state.mode === "resource") {
    renderResourceView();
  } else {
    showOverview();
    render();
    setTimeout(fit, 20);
  }
}

function init() {
  const views = FAILURE_VIEW_DATA.callstack_views || [];
  viewSelect.innerHTML = views.map((view, index) => {
    const name = view.top_function ?? "(null)";
    return `<option value="${index}">${esc(name)} (${(view.nodes || []).length}/${(view.edges || []).length})</option>`;
  }).join("");
  if (!views.length) {
    showOverview();
    render();
    return;
  }
  loadView(0);
}

viewSelect.addEventListener("change", () => loadView(Number(viewSelect.value)));
callGraphTab.addEventListener("click", () => setMode("callGraph"));
resourceTab.addEventListener("click", () => setMode("resource"));
document.getElementById("resetBtn").addEventListener("click", () => {
  state.selected = null;
  selectInitialVisible();
  if (state.mode === "resource") {
    renderResourceView();
  } else {
    showOverview();
    render();
    fit();
  }
});
document.getElementById("fitBtn").addEventListener("click", fit);
searchBox.addEventListener("input", () => {
  state.query = searchBox.value.trim().toLowerCase();
  if (state.query) {
    state.nodes.filter(matchesQuery).forEach(node => expandNode(node.id));
  }
  render();
});
svg.addEventListener("click", () => {
  state.selected = null;
  showOverview();
  render();
});
svg.addEventListener("wheel", event => {
  event.preventDefault();
  const rect = svg.getBoundingClientRect();
  const beforeX = (event.clientX - rect.left - state.offsetX) / state.scale;
  const beforeY = (event.clientY - rect.top - state.offsetY) / state.scale;
  const nextScale = Math.min(4, Math.max(0.18, state.scale * (event.deltaY > 0 ? 0.88 : 1.14)));
  state.offsetX = event.clientX - rect.left - beforeX * nextScale;
  state.offsetY = event.clientY - rect.top - beforeY * nextScale;
  state.scale = nextScale;
  applyTransform();
}, {passive: false});
svg.addEventListener("pointerdown", event => {
  if (event.target !== svg) return;
  state.panning = {sx: event.clientX, sy: event.clientY, ox: state.offsetX, oy: state.offsetY};
});
svg.addEventListener("pointermove", event => {
  if (state.dragging) {
    const {node, sx, sy, ox, oy} = state.dragging;
    node.x = ox + (event.clientX - sx) / state.scale;
    node.y = oy + (event.clientY - sy) / state.scale;
    render();
  } else if (state.panning) {
    state.offsetX = state.panning.ox + event.clientX - state.panning.sx;
    state.offsetY = state.panning.oy + event.clientY - state.panning.sy;
    applyTransform();
  }
});
svg.addEventListener("pointerup", () => {
  state.dragging = null;
  state.panning = null;
});
window.addEventListener("resize", () => {
  resizeViewBox();
  fit();
});

init();
