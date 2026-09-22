#!/usr/bin/env python3
"""渲染诊断报告 HTML（diagnostic-report-generation Skill 的渲染器）。

用法：
    python3 scripts/render_report.py <data.json> [out.html] [--kb-id <id>] [--no-sidecar]
    python3 scripts/render_report.py --spec [section]

约定：
    - 输入是**一个** JSON 文件（即报告的全部模板变量），不要在命令行上传大段 JSON。
    - 默认输出 <WITTY_REPORT_DIR>/<kb_id>/report_<kb_id>_<时间戳>.html，同目录写
      同名侧车 .json（原样报告数据，供前端列表展示与复现渲染）。
      WITTY_REPORT_DIR 未设置时回落 /tmp/reports（本地调试用）。
    - 显式传 out.html 时按该路径输出，侧车写到同目录同名。
    - 成功时只回显 ≤15 行摘要；数据/校验失败 exit 2，模板缺失 exit 3，
      缺 jinja2 exit 4，写盘失败 exit 5。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE = SKILL_DIR / "templates" / "report.html"
FALLBACK_OUT_DIR = Path("/tmp/reports")
KB_SLUG_FALLBACK = "unknown"

ROLE_ENUM = ("primary", "secondary", "independent")
STATUS_ENUM = ("confirmed", "suspected", "excluded")
SEVERITY_ENUM = ("P1", "P2", "P3")
CATEGORY_ENUM = ("error", "latency", "mixed")
STAGE_STATUS_ENUM = ("ok", "warn", "bottleneck")
SHARE_CLS_ENUM = ("s-ok", "s-warn", "s-bottleneck")
TRACE_KIND_ENUM = ("latency", "error")
EVIDENCE_TRACES_MAX = 5

REQUIRED_TOP = ("report", "basic_info", "statistics", "workflow")

# 仅用于识别「同一套 share_bar 里混进了另一种操作」的启发式名单
GET_ONLY_STAGES = (
    "SDK RPC（SDK→Master）",
    "Master 处理",
    "Master RPC（Master→Worker）",
    "Worker 查询元数据",
    "Local Worker 内部",
    "Remote Worker 内部",
)
SET_ONLY_STAGES = ("客户端 SDK 段", "Worker 写处理", "数据面未观测")


class Fatal(Exception):
    """数据/环境级错误：携带一句可直接定位的提示。"""

    def __init__(self, message: str, hint: str = "", code: int = 2):
        super().__init__(message)
        self.message = message
        self.hint = hint
        self.code = code


# --------------------------------------------------------------------------- #
# 校验
# --------------------------------------------------------------------------- #
def _as_num(value):
    try:
        return float(str(value).strip().rstrip("%").replace(",", ""))
    except (TypeError, ValueError):
        return None


def _check_enum(path, value, enum, errors, required=True):
    if value is None or value == "":
        if required:
            errors.append(f"{path}: 缺少必填字段（{ '|'.join(enum) }）")
        return
    if value not in enum:
        errors.append(f"{path}: {value!r} 不是合法取值（{'|'.join(enum)}）")


def _check_evidence_traces(path, traces, errors, warnings):
    """证据锚点校验：可选键，缺省 / null / [] 一律视为零锚点（不产生任何提示）。"""
    if traces is None:
        return
    if not isinstance(traces, list):
        errors.append(f"{path}: 必须是数组（零锚点可省略该键）")
        return
    if len(traces) > EVIDENCE_TRACES_MAX:
        errors.append(f"{path}: 最多 {EVIDENCE_TRACES_MAX} 条，当前 {len(traces)} 条")
    seen_ids: set = set()
    for j, t in enumerate(traces):
        tp = f"{path}[{j}]"
        if not isinstance(t, dict):
            errors.append(f"{tp}: 必须是对象")
            continue
        for field in ("trace_id", "kind", "why"):
            if not t.get(field):
                errors.append(f"{tp}.{field}: 必填")
        _check_enum(f"{tp}.kind", t.get("kind"), TRACE_KIND_ENUM, errors)
        tid = t.get("trace_id")
        if tid:
            if tid in seen_ids:
                warnings.append(f"{tp}.trace_id: {tid!r} 在本故障内重复")
            else:
                seen_ids.add(tid)
        if t.get("kind") == "latency" and t.get("evidence_ms") is None:
            warnings.append(f"{tp}.evidence_ms: latency 锚点建议填证据耗时")
        if t.get("kind") == "error" and not t.get("status_code"):
            warnings.append(f"{tp}.status_code: error 锚点建议填状态码")


def _check_stage_breakdown(path, bd, errors, warnings):
    if not isinstance(bd, dict):
        errors.append(f"{path}: 必须是对象")
        return
    if not bd.get("operation"):
        warnings.append(f"{path}.operation: 建议填 GET 或 SET（阶段表口径标识）")

    stages = bd.get("stages")
    if not stages:
        warnings.append(f"{path}.stages: 为空，阶段表不会渲染")
    elif not isinstance(stages, list):
        errors.append(f"{path}.stages: 必须是数组")
    else:
        for i, st in enumerate(stages):
            if not isinstance(st, dict) or not st.get("name"):
                errors.append(f"{path}.stages[{i}]: 缺少 name")
                continue
            _check_enum(f"{path}.stages[{i}].status", st.get("status"), STAGE_STATUS_ENUM, errors)

    bar = bd.get("share_bar")
    if bar:
        if not isinstance(bar, list):
            errors.append(f"{path}.share_bar: 必须是数组")
            return
        total = 0.0
        for i, seg in enumerate(bar):
            if not isinstance(seg, dict) or not seg.get("name"):
                errors.append(f"{path}.share_bar[{i}]: 缺少 name")
                continue
            _check_enum(f"{path}.share_bar[{i}].cls", seg.get("cls"), SHARE_CLS_ENUM, errors)
            pct = _as_num(seg.get("pct"))
            if pct is None:
                errors.append(f"{path}.share_bar[{i}].pct: 必须是百分比数值（不带 % 符号）")
            else:
                total += pct
        if total and abs(total - 100) > 2:
            warnings.append(f"{path}.share_bar: pct 合计 {total:g}（模板不自动补齐，建议为 100）")

        names = [str(s.get("name", "")) for s in bar if isinstance(s, dict)]
        has_get = any(n in GET_ONLY_STAGES for n in names)
        has_set = any(n in SET_ONLY_STAGES or n.startswith("SET") for n in names)
        if has_get and has_set:
            warnings.append(
                f"{path}.share_bar: 同时出现 GET 与 SET 阶段名，疑似混桶——GET/SET 应各出一套"
            )


def validate(data) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(data, dict):
        raise Fatal("数据根节点必须是 JSON 对象", "检查 JSON 最外层是否为 { }")

    for key in REQUIRED_TOP:
        if not isinstance(data.get(key), dict):
            errors.append(f"{key}: 缺少必填顶层对象")

    report = data.get("report") or {}
    if isinstance(report, dict):
        for field in ("title", "report_id", "generated_at"):
            if not report.get(field):
                warnings.append(f"report.{field}: 为空，页头会留白")

    basic = data.get("basic_info") or {}
    if isinstance(basic, dict):
        for field in ("kb_name", "total_trace_cnt"):
            if basic.get(field) in (None, ""):
                warnings.append(f"basic_info.{field}: 为空")

    faults = data.get("faults")
    if faults is None:
        if not isinstance(data.get("conclusion"), dict):
            errors.append("faults / conclusion: 二者必须至少提供一个（单故障可用扁平 conclusion）")
        else:
            _check_evidence_traces("evidence_traces", data.get("evidence_traces"), errors, warnings)
    elif not isinstance(faults, list) or not faults:
        errors.append("faults: 必须是至少含 1 个故障的数组")
    else:
        seen: set = set()
        primary_cnt = 0
        for i, f in enumerate(faults):
            p = f"faults[{i}]"
            if not isinstance(f, dict):
                errors.append(f"{p}: 必须是对象")
                continue
            if not f.get("id"):
                errors.append(f"{p}.id: 缺少故障编号（如 F01）")
            elif f["id"] in seen:
                errors.append(f"{p}.id: 故障编号 {f['id']!r} 重复")
            else:
                seen.add(f["id"])
            if not f.get("title"):
                errors.append(f"{p}.title: 缺少故障名称")
            if not isinstance(f.get("conclusion"), dict):
                errors.append(f"{p}.conclusion: 必填对象（一句话结论/故障域/影响面）")
            _check_enum(f"{p}.role", f.get("role"), ROLE_ENUM, errors)
            _check_enum(f"{p}.status", f.get("status"), STATUS_ENUM, errors)
            _check_enum(f"{p}.severity", f.get("severity"), SEVERITY_ENUM, errors)
            if f.get("category") is not None:
                _check_enum(f"{p}.category", f.get("category"), CATEGORY_ENUM, errors)
            elif len(faults) > 1:
                warnings.append(f"{p}.category: 多故障建议填 error|latency|mixed（档案头标签）")
            if f.get("role") == "primary":
                primary_cnt += 1
            _check_evidence_traces(f"{p}.evidence_traces", f.get("evidence_traces"), errors, warnings)
            lat = f.get("latency")
            if isinstance(lat, dict):
                for j, st in enumerate(lat.get("stages") or []):
                    if isinstance(st, dict):
                        _check_enum(
                            f"{p}.latency.stages[{j}].status",
                            st.get("status"),
                            STAGE_STATUS_ENUM,
                            errors,
                        )
        if primary_cnt != 1:
            warnings.append(f"faults[].role: primary 数量为 {primary_cnt}（多故障建议恰好 1 个）")
        if len(faults) > 1:
            if not isinstance(data.get("incident_summary"), dict):
                errors.append("incident_summary: 多故障必填（事件诊断摘要）")
            else:
                pid = data["incident_summary"].get("primary_fault_id")
                if pid and pid not in seen:
                    warnings.append(f"incident_summary.primary_fault_id: {pid!r} 不在 faults[].id 中")
                for field in ("one_line_conclusion", "fault_count"):
                    if data["incident_summary"].get(field) in (None, ""):
                        errors.append(f"incident_summary.{field}: 多故障必填")
            if not data.get("fault_relations"):
                errors.append("fault_relations: 多故障必填（from/to/type/confidence/evidence）")
            else:
                rel_type = ("causes", "common_cause", "independent", "correlated")
                for i, rel in enumerate(data["fault_relations"]):
                    if not isinstance(rel, dict):
                        errors.append(f"fault_relations[{i}]: 必须是对象")
                        continue
                    for field in ("from", "to", "type", "evidence"):
                        if not rel.get(field):
                            errors.append(f"fault_relations[{i}].{field}: 必填")
                    if rel.get("type") and rel["type"] not in rel_type:
                        errors.append(
                            f"fault_relations[{i}].type: {rel['type']!r} 不是合法取值（{'|'.join(rel_type)}）"
                        )

    stats = data.get("statistics")
    if isinstance(stats, dict):
        bds = stats.get("stage_breakdowns")
        if bds is not None:
            if not isinstance(bds, list):
                errors.append("statistics.stage_breakdowns: 必须是数组（GET/SET 各一套）")
            else:
                ops: list = []
                for i, bd in enumerate(bds):
                    _check_stage_breakdown(f"statistics.stage_breakdowns[{i}]", bd, errors, warnings)
                    if isinstance(bd, dict) and bd.get("operation"):
                        ops.append(str(bd["operation"]))
                dup = {o for o in ops if ops.count(o) > 1}
                if dup:
                    warnings.append(f"statistics.stage_breakdowns: operation 重复 {sorted(dup)}")
            if stats.get("stage_breakdown"):
                warnings.append(
                    "statistics.stage_breakdown: 与 stage_breakdowns 同时存在，只渲染 stage_breakdowns"
                )
        elif stats.get("stage_breakdown"):
            _check_stage_breakdown("statistics.stage_breakdown", stats["stage_breakdown"], errors, warnings)
        else:
            warnings.append("statistics: 没有阶段分解（stage_breakdown/stage_breakdowns），阶段表章节为空")

        heat = stats.get("time_heatmap")
        if heat not in (None, []):
            if not isinstance(heat, list):
                errors.append("statistics.time_heatmap: 必须是数组")
            else:
                for i, slot in enumerate(heat):
                    if not isinstance(slot, dict) or slot.get("time") in (None, ""):
                        errors.append(f"statistics.time_heatmap[{i}]: 缺少 time（HH:MM）")
                        continue
                    if _as_num(slot.get("pct")) is None:
                        errors.append(f"statistics.time_heatmap[{i}].pct: 必须是百分比数值")

    workflow = data.get("workflow")
    if isinstance(workflow, dict) and not workflow.get("steps"):
        warnings.append("workflow.steps: 为空，工作追踪只剩汇总数字")

    return errors, warnings


# --------------------------------------------------------------------------- #
# 章节回显
# --------------------------------------------------------------------------- #
def section_names(data) -> list[str]:
    names = ["日志基本信息", "事件诊断摘要"]
    if len(data.get("faults") or []) > 1:
        names.append("故障清单与关系")
    if data.get("action_plan"):
        names.append("综合处置计划")
    names += ["统计分析", "故障档案", "诊断工作追踪"]
    return [f"{i:02d} {n}" for i, n in enumerate(names, 1)]


def stats_line(data) -> str:
    stats = data.get("statistics") or {}
    bds = stats.get("stage_breakdowns") or ([stats["stage_breakdown"]] if stats.get("stage_breakdown") else [])
    parts = []
    if bds:
        parts.append(
            "阶段表 " + " / ".join(f"{b.get('operation', '?')} {len(b.get('stages') or [])} 行" for b in bds if isinstance(b, dict))
        )
    donuts = sum(1 for k in ("top_error_codes", "top_failure_domains", "top_pods", "top_hosts") if stats.get(k))
    if donuts:
        parts.append(f"饼图 {donuts}")
    if stats.get("time_heatmap"):
        parts.append(f"热点 {len(stats['time_heatmap'])} 槽")
    return " · ".join(parts) or "—"


def faults_line(data) -> str:
    faults = data.get("faults") or []
    if not faults:
        return "扁平单故障（conclusion 兼容路径）"
    items = []
    for f in faults:
        if not isinstance(f, dict):
            continue
        mark = "简化" if f.get("simplified") else "完整"
        items.append(
            f"{f.get('id')} {f.get('role')}/{f.get('status')}/{f.get('severity')} {mark}"
        )
    return f"{len(faults)} 个：" + " · ".join(items)


# --------------------------------------------------------------------------- #
# 字段清单（--spec）
# --------------------------------------------------------------------------- #
SPEC = {
    "top": """顶层变量（全部为 JSON 键）
report{title,report_id,generated_at}
basic_info{kb_id,kb_name,log_file,operation,time_range_start,time_range_end,total_trace_cnt,fault_trace_cnt,fault_ratio,parse_ok,diagnosis_ok}
faults[]{id,title,role,status,severity,confidence,category,affected_scope,conclusion,latency,root_cause,propagation,evidence_traces,knowledge_matches,solution,source_code,simplified,upstream,need_independent_fix}
incident_summary{one_line_conclusion,fault_count,primary_fault_id,secondary_fault_count,independent_fault_count,overall_impact,confidence}
fault_relations[]{from,to,type,confidence,evidence}
action_plan[]{priority,fault_ids,action,depends_on,expected_effect,verify}
statistics{stage_breakdown|stage_breakdowns,heatmap_metric,dist_total,top_error_codes,top_failure_domains,top_pods,top_hosts,time_heatmap}
workflow{session_id,total_steps,api_calls,duration,steps[]}
枚举：role=primary|secondary|independent; status=confirmed|suspected|excluded; severity=P1|P2|P3
     category=error|latency|mixed; stage.status=ok|warn|bottleneck; share_bar.cls=s-ok|s-warn|s-bottleneck
     fault_relations.type=causes|common_cause|independent|correlated; evidence_traces[].kind=latency|error
单故障可用扁平 conclusion/root_cause/propagation/evidence_traces/knowledge_matches/solution/source_code，模板自动包成 F01
示例与逐字段说明：references/REPORT_BLOCKS.md""",
    "basic_info": "kb_id,kb_name,log_file,operation,time_range_start,time_range_end,total_trace_cnt,fault_trace_cnt,fault_ratio,parse_ok,diagnosis_ok",
    "conclusion": "one_line_conclusion,fault_domain,fault_component,fault_function,fault_function_loc,affected_scope_pct,affected_scope_desc,confidence,key_findings[]",
    "latency": "metrics[]{label,value,sub,tone},stages[]{name,p99,baseline,ratio,share,status,detail},conclusion",
    "root_cause": "reasoning_chain[]{step_label,title,description,evidence,excluded,confirmed},confirmed_root_cause,supporting_knowledge",
    "evidence_traces": "可选，0~5 条；trace_id(必填,逐字来自工具响应),kind(必填,latency|error),why(必填,含桶key或过滤条件),evidence_ms,client_ms,status_code,failure_mode_id,pod,host,timestamp；latency 类取 /stats/stages 归因桶 top_traces[]；缺省/[]/null 均不渲染",
    "propagation": "chain[]{label,detail,type,transition,branches[{label,nodes[]}]},impact_scope[]",
    "solution": "short_term[],long_term[],verification[]",
    "knowledge": "rank,id,stars,match_logic,symptom,root_cause,solution,adoption_class,adoption_label,phenomenon_fit,log_fit,rc_consistency,env_diff,adaptation,applicability",
    "statistics": """stage_breakdowns[]{operation,total_p99_ms,share_bar[]{name,pct,cls},stages[]{name,p99,anomaly_rate,fail_share,status,fault,detail},conclusion}
heatmap_metric=fault|latency, dist_total
top_error_codes[]{code,name,pct,fault}, top_failure_domains[]{domain,pct,fault}
top_pods[]{pod,host,pct,fault}, top_hosts[]{host,pct,fault}
time_heatmap[]{time,level,pct,spike,lat_ms,fault}
GET/SET 阶段清单（报告阶段名 ↔ 字段 ↔ 阈值）：references/REPORT_BLOCKS.md""",
    "workflow": "session_id,total_steps,api_calls,duration,steps[]{title,api_calls[],result}",
    "source_code": "component,failure_mode_id,call_chain[]{function,file,line,role,role_label,call_site,code[]{num,text,highlight,ellipsis},analysis},fix_suggestion",
    "incident": "one_line_conclusion,fault_count,primary_fault_id,secondary_fault_count,independent_fault_count,overall_impact,confidence",
    "action_plan": "priority,fault_ids[],action,depends_on,expected_effect,verify",
}


def print_spec(which: str) -> int:
    keys = list(SPEC) if which in ("all", "") else [which]
    for k in keys:
        if k not in SPEC:
            print(f"未知板块 {k!r}；可用：{'|'.join(SPEC)}", file=sys.stderr)
            return 2
        print(f"### {k}")
        print(SPEC[k])
    return 0


# --------------------------------------------------------------------------- #
def report_root() -> Path:
    """报告根目录：运行时读 WITTY_REPORT_DIR，未设置时回落 /tmp/reports。"""
    return Path(os.environ.get("WITTY_REPORT_DIR") or FALLBACK_OUT_DIR)


def kb_slug(kb_id) -> str:
    """把知识库 ID 清洗成可用作目录名/文件名的一段（同时挡住路径穿越）。"""
    slug = re.sub(r"[^A-Za-z0-9_-]", "_", str(kb_id or "").strip())
    return slug or KB_SLUG_FALLBACK


def sidecar_payload(data: dict, out_path: Path) -> dict:
    """侧车 JSON：渲染入参原样保留，仅补齐 report.report_id / report.generated_at。"""
    payload = dict(data)
    report = payload.get("report")
    if isinstance(report, dict):
        report = dict(report)
        if not report.get("report_id"):
            report["report_id"] = out_path.stem
        if not report.get("generated_at"):
            report["generated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        payload["report"] = report
    return payload


# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(add_help=True, description="渲染诊断报告 HTML")
    parser.add_argument("data", nargs="?", help="报告数据 JSON 文件")
    parser.add_argument("out", nargs="?",
                        help="输出 HTML 路径（默认 $WITTY_REPORT_DIR/<kb_id>/report_<kb_id>_<ts>.html）")
    parser.add_argument("--kb-id", default=None, metavar="ID",
                        help="知识库 ID（默认取 basic_info.kb_id），决定默认输出目录与文件名")
    parser.add_argument("--no-sidecar", action="store_true",
                        help="不写同名侧车 JSON（前端列表将缺少标题/故障数）")
    parser.add_argument("--spec", nargs="?", const="all", default=None, metavar="SECTION",
                        help="打印紧凑字段清单（top|basic_info|statistics|... 或 all）后退出")
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE), help="模板路径")
    args = parser.parse_args(argv)

    if args.spec is not None:
        return print_spec(args.spec)
    if not args.data:
        parser.error("需要提供数据 JSON 路径（或用 --spec 查字段清单）")

    data_path = Path(args.data)
    if not data_path.is_file():
        print(f"✘ 数据文件不存在: {data_path}", file=sys.stderr)
        print(f"  提示：先把报告变量写入该 JSON，再执行 {Path(__file__).name} <data.json>", file=sys.stderr)
        return 2
    try:
        data = json.loads(data_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"✘ JSON 解析失败 {data_path}:{exc.lineno}:{exc.colno} — {exc.msg}", file=sys.stderr)
        return 2

    try:
        errors, warnings = validate(data)
    except Fatal as exc:
        print(f"✘ {exc.message}", file=sys.stderr)
        if exc.hint:
            print(f"  提示：{exc.hint}", file=sys.stderr)
        return exc.code

    if errors:
        print(f"✘ 数据校验未通过（{len(errors)} 处）：", file=sys.stderr)
        for line in errors[:6]:
            print(f"  - {line}", file=sys.stderr)
        if len(errors) > 6:
            print(f"  ... 另有 {len(errors) - 6} 处", file=sys.stderr)
        print(f"  提示：修正 {data_path} 中上述字段后重跑；字段清单见 --spec top", file=sys.stderr)
        return 2

    try:
        from jinja2 import Environment, FileSystemLoader, select_autoescape
    except ImportError:
        print("✘ 缺少 jinja2 模块", file=sys.stderr)
        print("  提示：dnf install -y python3-jinja2（镜像已内置；本地调试可用 pip3 install jinja2）", file=sys.stderr)
        return 4

    template_path = Path(args.template)
    if not template_path.is_file():
        print(f"✘ 模板不存在: {template_path}", file=sys.stderr)
        print("  提示：--template 指向 report.html", file=sys.stderr)
        return 3

    env = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=False,
        lstrip_blocks=False,
    )
    try:
        html = env.get_template(template_path.name).render(**data)
    except Exception as exc:  # 模板语法/结构问题：给出模板侧定位
        print(f"✘ 渲染失败: {type(exc).__name__}: {exc}", file=sys.stderr)
        print(f"  提示：模板 {template_path}；数据 {data_path}", file=sys.stderr)
        return 2

    if args.out:
        out_path = Path(args.out)
    else:
        slug = kb_slug(args.kb_id or (data.get("basic_info") or {}).get("kb_id"))
        base = f"report_{slug}_{time.strftime('%Y%m%d_%H%M%S')}"
        out_path = report_root() / slug / f"{base}.html"
        seq = 0
        while out_path.exists() or (not args.no_sidecar and out_path.with_suffix(".json").exists()):
            seq += 1
            out_path = out_path.with_name(f"{base}_{seq}.html")

    sidecar_path = None if args.no_sidecar else out_path.with_suffix(".json")
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")
        if sidecar_path is not None:
            payload = json.dumps(sidecar_payload(data, out_path), ensure_ascii=False, indent=2)
            sidecar_path.write_text(payload + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"✘ 写盘失败: {exc}", file=sys.stderr)
        print(f"  提示：确认 {out_path.parent} 可写（WITTY_REPORT_DIR={report_root()}），或显式传 out 路径", file=sys.stderr)
        return 5

    print(f"✔ {out_path}  ({len(html.encode('utf-8')):,} bytes)")
    if sidecar_path is not None:
        print(f"  侧车 {sidecar_path.name}  ({sidecar_path.stat().st_size:,} bytes)")
    print("  章节 " + str(len(section_names(data))) + ": " + " · ".join(section_names(data)))
    print("  故障 " + faults_line(data))
    print("  统计 " + stats_line(data))
    if warnings:
        shown = warnings[:3]
        for line in shown:
            print(f"  ⚠ {line}")
        if len(warnings) > len(shown):
            print(f"  ⚠ ... 另有 {len(warnings) - len(shown)} 条提示（不影响渲染）")
    return 0


if __name__ == "__main__":
    sys.exit(main())