"""
The local model runner's client: any server with the OpenAI-compatible chat API and tool calls.
Standard library only. It streams, so a reply shows as it is written and Stop cuts it off.

- Ollama (the default): installed on this Mac. It runs models on the CPU through llama.cpp (the
  Radeon Pro 560X is not used). Measured here (i9-8950HK): qwen3:4b-instruct answers a tool
  call in 2-3 s (prompts ~650 tokens/s once warm, writing ~9 tokens/s). Thinking models are
  much slower here: qwen3:4b writes 500-950 tokens of reasoning before each call (60-125 s), and
  no setting turned that off. So an instruct model is the default.
- Strata (github.com/Niko1221/Strata): http://127.0.0.1:8080/v1, on a machine it supports:
  Apple Silicon, or a 12 GB+ NVIDIA/AMD GPU with 32 GB+ of RAM and VRAM together. Not this
  Intel Mac.
- llama.cpp's llama-server, LM Studio, vLLM: their /v1 URL.

PHYSTRACK_LLM_URL and PHYSTRACK_LLM_MODEL choose (the assistant panel also lists the runner's
models). Finding, starting and stopping the runner is runner.py's job; this module only talks to it.
"""

import json
import os
import urllib.error
import urllib.request

from . import ollama_models

DEFAULT_URL = "http://127.0.0.1:11434/v1"   # Ollama
DEFAULT_MODEL = "qwen3:4b-instruct"


class LLMError(Exception):
    """The runner could not be reached, or refused the request (the message says which)."""


class Cancelled(Exception):
    """The user stopped the reply being written."""


class _ThinkTags:
    """Splits text that carries its reasoning inline, between <think> and </think> (some models on
    some runners), into (reasoning, reply) pieces as it streams. A tag cut between two pieces is
    held back until the next piece shows what it is."""

    TAGS = ("<think>", "</think>")

    def __init__(self) -> None:
        self.inside, self.held = False, ""

    def feed(self, piece: str) -> list:
        text, out = self.held + piece, []
        self.held = ""
        while text:
            tag = self.TAGS[1] if self.inside else self.TAGS[0]
            at = text.find(tag)
            if at >= 0:
                if at:
                    out.append((self.inside, text[:at]))
                text, self.inside = text[at + len(tag):], not self.inside
                continue
            # The end may be the start of a tag: hold it back
            keep = next((n for n in range(min(len(tag) - 1, len(text)), 0, -1) if tag.startswith(text[-n:])), 0)
            if len(text) > keep:
                out.append((self.inside, text[:len(text) - keep]))
            self.held = text[len(text) - keep:]
            break
        return out

    def flush(self) -> list:
        held, self.held = self.held, ""
        return [(self.inside, held)] if held else []


class LLM:
    def __init__(self, url: str | None = None, model: str | None = None, key: str | None = None) -> None:
        self.url = (url or os.environ.get("PHYSTRACK_LLM_URL") or DEFAULT_URL).rstrip("/")
        self.model = model or os.environ.get("PHYSTRACK_LLM_MODEL") or DEFAULT_MODEL
        self.key = key or os.environ.get("PHYSTRACK_LLM_KEY") or "local"

    @property
    def is_ollama(self) -> bool:
        return ":11434" in self.url

    def _open(self, path: str, body: dict | None = None, timeout: float = 10.0):
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(self.url + path, data, {
            "Content-Type": "application/json", "Authorization": f"Bearer {self.key}"})
        return urllib.request.urlopen(request, timeout=timeout)

    def models(self) -> list[str]:
        """The runner's models (raises OSError if it cannot be reached)."""
        with self._open("/models", timeout=3.0) as response:
            return sorted(m["id"] for m in json.loads(response.read()).get("data") or [])   # Ollama sends null with no models

    def available_models(self) -> list[str]:
        """What the model list shows: the runner's models, and for Ollama also those on disk in any of its
        folders (models() stays the runner's own list, which says what it can answer with now)."""
        names = set(self.models())
        if self.is_ollama:
            names.update(ollama_models.on_disk())
        return sorted(names)

    def chat(self, messages: list, tools: list, on_text=None, cancelled=None,
             max_tokens: int = 400, on_reasoning=None) -> dict:
        """
        One reply: {"content": text, "reasoning": text,
                    "tool_calls": [{"id", "name", "arguments": dict, "bad": text}]}.
        `on_text(piece)` gets the text as it is written, and `on_reasoning(piece)` a thinking
        model's reasoning: from the reasoning field (Ollama, OpenRouter), reasoning_content
        (llama.cpp, vLLM) or <think> tags in the text. `cancelled()` is asked between pieces
        (True: the reply stops, and Cancelled is raised). "bad" is set when a call's arguments
        are not JSON (they are then {}), so the caller can say so to the model.
        """
        body = {"model": self.model, "messages": messages, "tools": tools, "stream": True,
                "temperature": 0.2, "max_tokens": max_tokens}
        try:
            response = self._open("/chat/completions", body, timeout=600.0)
        except urllib.error.HTTPError as e:
            detail = e.read()[:300].decode("utf-8", "replace")
            has_image = any(isinstance(m.get("content"), list) and any(
                part.get("type") == "image_url" for part in m["content"] if isinstance(part, dict))
                for m in messages)
            if has_image:
                detail += "; this request includes an image, so use a vision-capable model and a runner " \
                          "that supports OpenAI-compatible image_url content"
            raise LLMError(f"the model runner refused the request ({e.code}): {detail}") from None
        except OSError as e:
            raise LLMError(f"cannot reach the model runner at {self.url} ({e})") from None
        content, reasoning, calls, tags = [], [], {}, _ThinkTags()

        def take(pieces: list) -> None:
            for is_reasoning, text in pieces:
                (reasoning if is_reasoning else content).append(text)
                callback = on_reasoning if is_reasoning else on_text
                if callback is not None:
                    callback(text)
        with response:
            for raw in response:
                if cancelled is not None and cancelled():
                    raise Cancelled()
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except ValueError:
                    continue
                for choice in chunk.get("choices") or []:
                    delta = choice.get("delta") or {}
                    thought = delta.get("reasoning") or delta.get("reasoning_content")
                    if isinstance(thought, str) and thought:
                        take([(True, thought)])
                    if delta.get("content"):
                        take(tags.feed(delta["content"]))
                    # A call comes whole (Ollama) or in pieces (OpenAI, llama.cpp): its name once,
                    # its arguments as text in pieces
                    for tc in delta.get("tool_calls") or []:
                        slot = calls.setdefault(tc.get("index", len(calls)), {"id": "", "name": "", "args": ""})
                        slot["id"] = tc.get("id") or slot["id"]
                        fn = tc.get("function") or {}
                        slot["name"] = fn.get("name") or slot["name"]
                        args = fn.get("arguments")
                        if isinstance(args, dict):
                            slot["args"] = json.dumps(args)
                        elif args:
                            slot["args"] += args
        take(tags.flush())
        out = []
        for i, slot in sorted(calls.items()):
            entry = {"id": slot["id"] or f"call_{i}", "name": slot["name"], "arguments": {}}
            try:
                parsed = json.loads(slot["args"]) if slot["args"].strip() else {}
                entry["arguments"] = parsed if isinstance(parsed, dict) else {}
            except ValueError:
                entry["bad"] = slot["args"]
            out.append(entry)
        return {"content": "".join(content), "reasoning": "".join(reasoning), "tool_calls": out}
