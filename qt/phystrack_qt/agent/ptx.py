"""
The agent tools from a shell (for people, scripts, and agents with only a shell):

    python ptx.py tools                       one line per tool: name(params): what it does
    python ptx.py state                       a tool with no arguments
    python ptx.py trim start=10 end=200       key=value (values are JSON where they can be)
    python ptx.py mark box=[300,500,24,24] auto=true
    python ptx.py ruler '{"length": 50, "unit": "cm"}'

Prints the app's answer as compact JSON; exits 1 on an error. Same tools and answers as MCP
(mcp_server.py), through the running app's bridge (PHYSTRACK_BRIDGE_PORT, else cache/bridge.port).
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from phystrack_qt.agent.mcp_server import bridge_call  # noqa: E402
from phystrack_qt.agent.specs import SPECS  # noqa: E402


def parse(words: list) -> dict:
    if len(words) == 1 and words[0].lstrip().startswith("{"):
        return json.loads(words[0])
    args = {}
    for word in words:
        key, sep, value = word.partition("=")
        if not sep:
            raise SystemExit(f"arguments are key=value, not {word!r}")
        try:
            args[key] = json.loads(value)
        except ValueError:
            args[key] = value
    return args


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help", "tools"):
        print("Every tool also takes w=<window id> (default: your current window).")
        for name, (desc, params, _) in SPECS.items():
            print(f"{name}({', '.join(f'{k}:{t}' for k, t in params.items())}): {desc}")
        return 0
    out = bridge_call(sys.argv[1], parse(sys.argv[2:]))
    print(json.dumps(out.get("ok", out), separators=(",", ":"), ensure_ascii=False))
    return 1 if "error" in out else 0


if __name__ == "__main__":
    sys.exit(main())
