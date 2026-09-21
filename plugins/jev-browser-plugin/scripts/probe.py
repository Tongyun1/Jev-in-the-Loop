"""Use the actual MCP wire protocol. --request runs a paid browser task."""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def run(args):
    env = dict(os.environ)
    if args.env_file:
        env["JEV_ENV_FILE"] = str(Path(args.env_file).resolve())
    params = StdioServerParameters(command=sys.executable, args=["-m", "jev_browser.server"], env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            if args.request:
                data = json.loads(Path(args.request).read_text())
                result = await session.call_tool("jev_run", {"request": data})
            else:
                result = await session.call_tool("jev_health", {})
            print(json.dumps(result.structuredContent, ensure_ascii=False))
            if result.isError or result.structuredContent is None:
                raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file")
    parser.add_argument("--request", help="JSON input; opens Chrome and makes paid Jev requests")
    asyncio.run(run(parser.parse_args()))
