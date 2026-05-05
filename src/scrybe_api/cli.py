from __future__ import annotations

import uvicorn
import typer

from scrybe_api.config import get_settings

app = typer.Typer(help="SCRYBE API command line.")


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8420, reload: bool = False) -> None:
    settings = get_settings()
    uvicorn.run(
        "scrybe_api.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="debug" if settings.debug else "info",
    )

