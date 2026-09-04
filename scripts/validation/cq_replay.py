"""Replay the tool calls named in each CQ's workflow_steps against the in-process
gateway of the current checkout and record the wire JSON.

usage: uv run python scripts/validation/cq_replay.py <cq_dataset.json> <out.json> [--dry-run]
Run from inside the checkout whose gateway you want to exercise.
"""

import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path

from fastmcp import Client

CALL = re.compile(r"\b([a-z]+_[a-z_]+)\((.*?)\)")
ARG = re.compile(r"(\w+)=('[^']*'|\"[^\"]*\"|[^,]+)|('[^']*'|\"[^\"]*\")")
SKIP = {"add_memory"}
DELAY = float(os.environ.get("CQ_REPLAY_DELAY", "3"))
CALL_TIMEOUT = float(os.environ.get("CQ_CALL_TIMEOUT", "90"))


def parse_calls(rows: list[dict]) -> list[dict]:
    calls = []
    for row in rows:
        for i, step in enumerate(row["workflow_steps"]):
            for m in CALL.finditer(step):
                tool, raw = m.group(1), m.group(2)
                if tool in SKIP:
                    continue
                kwargs: dict[str, str] = {}
                positional: list[str] = []
                for name, value, bare in ARG.findall(raw):
                    if name:
                        kwargs[name] = value.strip("'\"")
                    elif bare:
                        positional.append(bare.strip("'\""))
                calls.append(
                    {
                        "cq_id": row["cq_id"],
                        "step": i,
                        "text": step,
                        "tool": tool,
                        "positional": positional,
                        "kwargs": kwargs,
                    }
                )
    return calls


def bind_args(call: dict, schema: dict) -> dict[str, str]:
    props = list(schema.get("properties", {}).keys())
    required = schema.get("required") or props[:1]
    args = dict(call["kwargs"])
    for name, value in zip(required, call["positional"], strict=False):
        args.setdefault(name, value)
    return args


async def replay(calls: list[dict], dry: bool) -> list[dict]:
    from biosciences_mcp.servers.gateway import mcp

    results = []
    async with Client(mcp) as client:
        schemas = {t.name: t.inputSchema for t in await client.list_tools()}
        for call in calls:
            schema = schemas.get(call["tool"])
            if schema is None:
                call["error"] = "unknown tool"
                results.append(call)
                continue
            call["args"] = bind_args(call, schema)
            if not call["args"]:
                call["error"] = "no literal arguments in step (depends on a prior result)"
                results.append(call)
                continue
            if dry:
                results.append(call)
                continue
            started = time.monotonic()
            try:
                res = await asyncio.wait_for(
                    client.call_tool(call["tool"], call["args"], raise_on_error=False), CALL_TIMEOUT
                )
                text = res.content[0].text if res.content else ""
                try:
                    call["result"] = json.loads(text)
                except ValueError:
                    call["raw"] = text[:500]
            except TimeoutError:
                call["error"] = f"no response within {CALL_TIMEOUT}s (client hang?)"
            except Exception as exc:  # record and continue
                call["error"] = f"{type(exc).__name__}: {exc}"[:300]
            call["seconds"] = round(time.monotonic() - started, 2)
            status = "ERR" if "error" in call or "raw" in call else "ok"
            print(f"{call['cq_id']:5} {call['tool']:40} {call['seconds']:6}s {status}", flush=True)
            results.append(call)
            await asyncio.sleep(DELAY)
    return results


def main() -> None:
    dataset, out = Path(sys.argv[1]), Path(sys.argv[2])
    dry = "--dry-run" in sys.argv
    rows = json.loads(dataset.read_text())
    results = asyncio.run(replay(parse_calls(rows), dry))
    out.write_text(json.dumps(results, indent=1))
    print("calls:", len(results), "->", out)


if __name__ == "__main__":
    main()
