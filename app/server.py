import argparse
import asyncio

import uvicorn


def selector_loop_factory() -> asyncio.AbstractEventLoop:
    """Use an event loop compatible with psycopg async connections on Windows."""
    return asyncio.SelectorEventLoop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the FECHAT backend")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    uvicorn.run(
        "app.main:sio_asgi_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        loop="app.server:selector_loop_factory",
    )


if __name__ == "__main__":
    main()
