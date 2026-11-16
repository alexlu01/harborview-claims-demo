import sys
sys.path.insert(0, "scripts")
from prerender import to_ipynb


def cmds(*c):
    return {"commands": [dict(position=i, **x) for i, x in enumerate(c)]}


def test_markdown_command_becomes_markdown_cell():
    nb = to_ipynb(cmds({"command": "%md\n# Title\ntext"}))
    assert nb["cells"][0]["cell_type"] == "markdown"
    assert "".join(nb["cells"][0]["source"]) == "# Title\ntext"


def test_ansi_result_becomes_stream_output():
    nb = to_ipynb(cmds({"command": "print(1)", "results": {"type": "ansi", "data": "1\n"}}))
    out = nb["cells"][0]["outputs"][0]
    assert nb["cells"][0]["cell_type"] == "code"
    assert out["output_type"] == "stream" and out["text"] == "1\n"


def test_table_result_becomes_html_display():
    res = {"type": "table", "data": [["safety_monitor", 1.0]],
           "schema": [{"name": "name"}, {"name": "rate"}]}
    out = to_ipynb(cmds({"command": "display(x)", "results": res}))["cells"][0]["outputs"][0]
    html = out["data"]["text/html"]
    assert out["output_type"] == "display_data"
    assert "<th>name</th>" in html and "<td>safety_monitor</td>" in html


def test_cells_ordered_by_position():
    nb = to_ipynb({"commands": [{"position": 2, "command": "b"}, {"position": 1, "command": "a"}]})
    assert ["".join(c["source"]) for c in nb["cells"]] == ["a", "b"]


def test_html_is_escaped_in_table_cells():
    res = {"type": "table", "data": [["<b>x</b>"]], "schema": [{"name": "v"}]}
    html = to_ipynb(cmds({"command": "d", "results": res}))["cells"][0]["outputs"][0]["data"]["text/html"]
    assert "&lt;b&gt;" in html
