"""Generate claims_ops.lvdash.json (AI/BI dashboard) from dashboard_datasets.DS. Run: python src/monitor/build_dashboard.py"""
import json, os
from dashboard_datasets import DS

def lines(sql):  # queryLines must end with a space/newline
    return [l + "\n" for l in sql.split("\n")]

def text(name, md, x, y, w, h=1):
    return {"widget": {"name": name, "multilineTextboxSpec": {"lines": [md]}}, "position": {"x": x, "y": y, "width": w, "height": h}}

def counter(name, ds, expr, title, x, y, fmt=None, w=4):
    enc = {"fieldName": "v", "displayName": title}
    if fmt: enc["format"] = fmt
    return {"widget": {"name": name, "queries": [{"name": "main_query", "query": {"datasetName": ds,
            "fields": [{"name": "v", "expression": expr}], "disaggregated": False}}],
            "spec": {"version": 2, "widgetType": "counter", "encodings": {"value": enc},
                     "frame": {"title": title, "showTitle": True}}},
            "position": {"x": x, "y": y, "width": w, "height": 3}}

def chart(name, kind, ds, xf, xexpr, xtype, yexpr, ytitle, title, x, y, w=6, color=None, yfmt=None, mappings=None):
    fields = [{"name": xf, "expression": xexpr}, {"name": "y", "expression": yexpr}]
    enc = {"x": {"fieldName": xf, "scale": {"type": xtype}, "displayName": xf},
           "y": {"fieldName": "y", "scale": {"type": "quantitative"}, "displayName": ytitle}}
    if yfmt: enc["y"]["format"] = yfmt
    if color:
        fields.append({"name": color, "expression": f"`{color}`"})
        enc["color"] = {"fieldName": color, "scale": {"type": "categorical", **({"mappings": mappings} if mappings else {})}, "displayName": color}
    return {"widget": {"name": name, "queries": [{"name": "main_query", "query": {"datasetName": ds, "fields": fields, "disaggregated": False}}],
            "spec": {"version": 3, "widgetType": kind, "encodings": enc, "frame": {"title": title, "showTitle": True}}},
            "position": {"x": x, "y": y, "width": w, "height": 6}}

def table(name, ds, cols, title, x, y, w=12, h=5):
    return {"widget": {"name": name, "queries": [{"name": "main_query", "query": {"datasetName": ds,
            "fields": [{"name": c, "expression": f"`{c}`"} for c, _, _ in cols], "disaggregated": True}}],
            "spec": {"version": 2, "widgetType": "table", "encodings": {"columns": [
                {"fieldName": c, "displayName": d, **({"format": f} if f else {})} for c, d, f in cols]},
                "frame": {"title": title, "showTitle": True}}},
            "position": {"x": x, "y": y, "width": w, "height": h}}

PCT = {"type": "number-percent", "decimalPlaces": {"type": "max", "places": 1}}
USD = {"type": "number-currency", "currencyCode": "USD", "abbreviation": "compact", "decimalPlaces": {"type": "max", "places": 1}}
CMP = {"type": "number-plain", "abbreviation": "compact"}
OUTCOME = [{"value": "Answered", "color": "#1192E8"}, {"value": "Blocked by policy", "color": "#FA4D56"}, {"value": "Error", "color": "#9F1853"}]
HOUR = 'DATE_TRUNC("HOUR", `hour`)'

pages = [
 {"name": "gateway", "displayName": "Unity Gateway: usage & cost", "layout": [
   text("t1", "## Harborview Claims Agent: operations", 0, 0, 12),
   text("s1", "Every LLM call goes through the Unity Gateway model service `agent.claims_llm`: guardrails, rate limits, fallback and usage by request tag.", 0, 1, 12),
   counter("k_req", "ds_usage", "COUNT(`event_time`)", "Requests", 0, 2),
   counter("k_blk", "ds_usage", "SUM(`blocked`)", "Blocked by service policy", 4, 2),
   counter("k_tok", "ds_usage", "SUM(`total_tokens`)", "Tokens", 8, 2, CMP),
   chart("c_out", "bar", "ds_usage", "hour", HOUR, "temporal", "COUNT(`event_time`)", "Requests", "Requests by outcome", 0, 5, color="outcome", mappings=OUTCOME),
   chart("c_tag", "bar", "ds_usage", "step", "`step`", "categorical", "SUM(`total_tokens`)", "Tokens", "Tokens by request tag (step)", 6, 5),
 ]},
 {"name": "quality", "displayName": "Agent quality", "layout": [
   text("t2", "## Agent quality: judges on every evaluated and production trace", 0, 0, 12),
   counter("k_tr", "ds_traces", "COUNT(`trace_id`)", "Traced questions", 0, 1),
   counter("k_lat", "ds_traces", "AVG(`seconds`)", "Avg response time (s)", 4, 1, {"type": "number-plain", "decimalPlaces": {"type": "max", "places": 1}}),
   counter("k_cov", "ds_quality", "AVG(`passed`)", "Judge pass rate (all judges)", 8, 1, PCT),
   chart("c_judge", "bar", "ds_quality", "judge", "`judge`", "categorical", "AVG(`passed`)", "Pass rate", "Pass rate by judge", 0, 4, yfmt=PCT),
   chart("c_vol", "line", "ds_traces", "hour", HOUR, "temporal", "COUNT(`trace_id`)", "Traces", "Questions handled per hour", 6, 4),
 ]},
 {"name": "dq", "displayName": "Data quality", "layout": [
   text("t3", "## Data quality: Lakeflow pipeline expectations (latest update)", 0, 0, 12),
   counter("k_dq", "ds_dq", "MIN(`pass_rate`)", "Lowest expectation pass rate", 0, 1, PCT, w=6),
   counter("k_dqf", "ds_dq", "SUM(`failed`)", "Records dropped or flagged", 6, 1, w=6),
   table("tb_dq", "ds_dq", [("dataset_name", "Table", None), ("expectation", "Expectation", None), ("passed", "Passed", None),
                            ("failed", "Failed", None), ("pass_rate", "Pass rate", PCT)], "Expectations", 0, 4),
 ]},
 {"name": "business", "displayName": "Claims KPIs", "layout": [
   text("t4", "## Claims book: what the agent is working on", 0, 0, 12),
   counter("k_cl", "ds_claims", "COUNT(`claim_id`)", "Claims", 0, 1),
   counter("k_amt", "ds_claims", "SUM(`claim_amount`)", "Claimed amount", 4, 1, USD),
   counter("k_avg", "ds_claims", "AVG(`claim_amount`)", "Avg claim", 8, 1, USD),
   chart("c_st", "bar", "ds_claims", "status", "`status`", "categorical", "SUM(`claim_amount`)", "Amount", "Claimed amount by status", 0, 4, yfmt=USD),
   chart("c_lt", "bar", "ds_claims", "loss_type", "`loss_type`", "categorical", "COUNT(`claim_id`)", "Claims", "Claims by loss type", 6, 4),
 ]},
]
for p in pages:
    p.update({"pageType": "PAGE_TYPE_CANVAS", "layoutVersion": "GRID_V1"})

dash = {"datasets": [{"name": k, "displayName": k.replace("ds_", "").title(), "queryLines": lines(v)} for k, v in DS.items()],
        "pages": pages,
        "uiSettings": {"theme": {
            "canvasBackgroundColor": {"light": "#FCFCFC", "dark": "#1F272D"},
            "widgetBackgroundColor": {"light": "#FFFFFF", "dark": "#11171C"},
            "fontColor": {"light": "#11171C", "dark": "#E8ECF0"},
            "selectionColor": {"light": "#2272B4", "dark": "#8ACAFF"},
            "visualizationColors": ["#1192E8", "#6929C4", "#005D5D", "#9F1853", "#FA4D56", "#198038", "#B28600"],
            "widgetHeaderAlignment": "LEFT"}}}
out = os.path.join(os.path.dirname(__file__), "claims_ops.lvdash.json")
json.dump(dash, open(out, "w"), indent=1)
print("wrote", out, sum(len(p["layout"]) for p in pages), "widgets")
