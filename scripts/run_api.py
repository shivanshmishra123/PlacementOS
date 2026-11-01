"""Run the local API with psycopg's required selector loop on Windows."""

from __future__ import annotations

import argparse
import asyncio
import selectors
import sys

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    args = parser.parse_args()
    config = uvicorn.Config(
        "placementos.main:app",
        host=args.host,
        port=args.port,
        server_header=False,
    )
    server = uvicorn.Server(config)
    try:
        if sys.platform == "win32":
            asyncio.run(
                server.serve(),
                loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()),
            )
        else:
            asyncio.run(server.serve())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
