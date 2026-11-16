def main() -> None:
    import argparse

    import uvicorn

    from .logging_config import LOGGING_CONFIG

    parser = argparse.ArgumentParser(description="Run the Etienne web server.")
    parser.add_argument("--host", default="127.0.0.1", help="Address to listen on.")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on.")
    parser.add_argument(
        "--reload", action="store_true", help="Restart on code changes (development)."
    )
    args = parser.parse_args()

    # Keep the import string so Uvicorn can load the app in its reload process.
    uvicorn.run(
        "etienne.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_config=LOGGING_CONFIG,
    )
