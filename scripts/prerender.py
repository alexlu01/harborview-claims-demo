"""Turn a job run's output into a pre-rendered workspace notebook (outputs kept, cells still runnable).
usage: prerender.py <job_run_id> <workspace_path> [task_key]"""
import html, json, subprocess, sys, tempfile


def _src(text: str) -> list[str]:
    return text.splitlines(keepends=True)


def _table_html(res: dict) -> str:
    cols = [c["name"] for c in res.get("schema") or []]
    head = "".join(f"<th>{html.escape(str(c))}</th>" for c in cols)
    rows = "".join("<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in r) + "</tr>"
                   for r in res.get("data") or [])
    return f"<table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>"


def _outputs(c: dict) -> list[dict]:
    r = c.get("results") or {}
    kind, outs = r.get("type"), []
    if kind == "ansi" and r.get("data"):
        outs.append({"output_type": "stream", "name": "stdout", "text": r["data"]})
    elif kind == "table":
        outs.append({"output_type": "display_data", "metadata": {}, "data": {"text/html": _table_html(r)}})
    elif kind in ("html", "htmlSandbox") and r.get("data"):
        outs.append({"output_type": "display_data", "metadata": {}, "data": {"text/html": r["data"]}})
    elif kind == "mimeBundle" and isinstance(r.get("data"), dict):
        outs.append({"output_type": "display_data", "metadata": {}, "data": r["data"]})
    elif kind == "listResults":
        for item in r.get("data") or []:
            outs += _outputs({"results": item})
    return outs


def to_ipynb(model: dict) -> dict:
    cells = []
    for c in sorted(model["commands"], key=lambda x: x.get("position", 0)):
        text = c["command"]
        if text.lstrip().startswith("%md"):
            body = text.lstrip()[3:].lstrip("\n")
            cells.append({"cell_type": "markdown", "metadata": {}, "source": _src(body)})
        else:
            cells.append({"cell_type": "code", "metadata": {}, "execution_count": None,
                          "source": _src(text), "outputs": _outputs(c)})
    return {"nbformat": 4, "nbformat_minor": 5, "cells": cells,
            "metadata": {"language_info": {"name": "python"}}}


if __name__ == "__main__":
    from run_cells import notebook_model
    run_id, dest = sys.argv[1], sys.argv[2]
    task = json.loads(subprocess.run(["databricks", "jobs", "get-run", run_id, "--profile", "e2e-ai-workshop",
                                      "-o", "json"], capture_output=True, text=True, check=True).stdout)["tasks"]
    task = next(t for t in task if len(sys.argv) < 4 or t["task_key"] == sys.argv[3])
    nb = to_ipynb(notebook_model(str(task["run_id"])))
    with tempfile.NamedTemporaryFile("w", suffix=".ipynb", delete=False) as f:
        json.dump(nb, f)
    subprocess.run(["databricks", "workspace", "mkdirs", dest.rsplit("/", 1)[0], "--profile", "e2e-ai-workshop"],
                   check=True)
    subprocess.run(["databricks", "workspace", "import", dest, "--file", f.name, "--format", "JUPYTER",
                    "--language", "PYTHON", "--overwrite", "--profile", "e2e-ai-workshop"], check=True)
    print(f"{dest}: {sum(1 for c in nb['cells'] if c.get('outputs'))} cells with output")
