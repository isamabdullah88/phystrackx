"""
MCP server (stdio) for the PhysTrackX Qt app: lists the agent tools and forwards each call to the
running app's bridge (bridge.py). No Qt and no packages beyond the standard library, so it starts
at once; the app does the work.

    claude mcp add phystrack -- ~/.venvs/phystrackx-qt/bin/python \\
        "<repo>/qt/phystrack_qt/agent/mcp_server.py"

The app must be running (qt/run.py starts the bridge). The bridge's port: PHYSTRACK_BRIDGE_PORT,
else the one the app wrote to qt/cache/bridge.port, else 8765.

QUICK-AND-DIRTY (see docs/AGENT_PLAN.md): MCP's JSON-RPC over stdio by hand (initialize,
tools/list, tools/call, ping), one request at a time, rather than the official SDK.
"""

import json
import os
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))   # qt/, for phystrack_qt.agent.specs

from phystrack_qt import paths  # noqa: E402
from phystrack_qt.agent.specs import INSTRUCTIONS, SPECS, json_schema  # noqa: E402

PORT_FILE = os.path.join(paths.cache_dir(), "bridge.port")
PROTOCOL = "2025-06-18"


def bridge_port() -> int:
    if os.environ.get("PHYSTRACK_BRIDGE_PORT"):
        return int(os.environ["PHYSTRACK_BRIDGE_PORT"])
    try:
        with open(PORT_FILE) as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return 8765


def bridge_call(name: str, args: dict, timeout: float = 1800.0) -> dict:
    """The app's answer to a tool call, or an error saying the app is not running."""
    data = json.dumps({"tool": name, "args": args}).encode()
    request = urllib.request.Request(f"http://127.0.0.1:{bridge_port()}/call", data,
                                     {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read())
    except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
        return {"error": f"PhysTrackX is not running or not answering ({e}). Ask the user to start "
                         "it: ~/.venvs/phystrackx-qt/bin/python qt/run.py"}


def tools_list() -> list:
    return [{"name": name, "description": desc, "inputSchema": json_schema(params)}
            for name, (desc, params, _) in SPECS.items()]


def handle(msg: dict):
    method, params = msg.get("method"), msg.get("params") or {}
    if method == "initialize":
        return {"protocolVersion": params.get("protocolVersion", PROTOCOL),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "phystrack", "version": "0.1"},
                "instructions": INSTRUCTIONS}
    if method == "tools/list":
        return {"tools": tools_list()}
    if method == "tools/call":
        out = bridge_call(params.get("name", ""), params.get("arguments") or {})
        text = json.dumps(out.get("ok", out), separators=(",", ":"), ensure_ascii=False)
        return {"content": [{"type": "text", "text": text}], "isError": "error" in out}
    if method == "ping":
        return {}
    raise KeyError(method)


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        if "id" not in msg:   # A notification (initialized, cancelled): no answer
            continue
        try:
            reply = {"jsonrpc": "2.0", "id": msg["id"], "result": handle(msg)}
        except KeyError:
            reply = {"jsonrpc": "2.0", "id": msg["id"],
                     "error": {"code": -32601, "message": f"no method {msg.get('method')}"}}
        except Exception as e:
            reply = {"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32603, "message": str(e)}}
        sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
