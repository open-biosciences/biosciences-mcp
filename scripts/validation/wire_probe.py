"""Re-run the strict/list probes recorded as <server>.<tool>.<arg>.json under a
snapshot directory against the current checkout's gateway, writing the same
file names into an output directory.

usage: uv run python scripts/validation/wire_probe.py <snapshot_dir> <out_dir>
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

from fastmcp import Client

DELAY = float(os.environ.get("CQ_REPLAY_DELAY", "3"))


async def probe(names: list[str], dst: Path) -> None:
    from biosciences_mcp.servers.gateway import mcp

    async with Client(mcp) as client:
        schemas = {t.name: t.inputSchema for t in await client.list_tools()}
        for name in names:
            server, tool, arg = name[:-5].split(".", 2)
            gw_tool = f"{server}_{tool}"
            schema = schemas.get(gw_tool)
            if schema is None:
                print("skip (no tool):", name)
                continue
            param = (schema.get("required") or list(schema["properties"]))[0]
            started = time.monotonic()
            res = await client.call_tool(gw_tool, {param: arg}, raise_on_error=False)
            text = res.content[0].text if res.content else ""
            try:
                payload = json.loads(text)
            except ValueError:
                payload = {"_raw": text[:500]}
            await asyncio.to_thread(
                (dst / name).write_text, json.dumps(payload, indent=1, sort_keys=True)
            )
            print(f"{name:55} {round(time.monotonic() - started, 2):6}s", flush=True)
            await asyncio.sleep(DELAY)


def main() -> None:
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    dst.mkdir(parents=True, exist_ok=True)
    asyncio.run(probe(sorted(p.name for p in src.glob("*.json")), dst))


if __name__ == "__main__":
    main()
