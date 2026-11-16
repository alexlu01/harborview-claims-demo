"""Print each cell's state and output from a job run. usage: run_cells.py <task_run_id>"""
import base64, json, re, subprocess, sys, urllib.parse

def notebook_model(task_run_id: str) -> dict:
    out = subprocess.run(["databricks", "jobs", "export-run", task_run_id, "--views-to-export", "CODE",
                          "--profile", "e2e-ai-workshop", "-o", "json"], capture_output=True, text=True, check=True).stdout
    html = json.loads(out)["views"][0]["content"]
    enc = re.search(r"__DATABRICKS_NOTEBOOK_MODEL = '([^']+)'", html).group(1)
    return json.loads(urllib.parse.unquote(base64.b64decode(enc).decode()))

if __name__ == "__main__":
    for c in notebook_model(sys.argv[1])["commands"]:
        if c["command"].lstrip().startswith("%md"):
            continue
        print("---", c.get("state"), c["command"][:60].replace("\n", " | "))
        r = c.get("results") or {}
        if r.get("data"):
            print("   ", str(r["data"])[:500])
        if c.get("error"):
            print("    ERR", c["error"][:500])
