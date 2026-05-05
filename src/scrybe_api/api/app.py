from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from scrybe_api.adapters.liteparse import LiteParseAdapter
from scrybe_api.api.routes import router
from scrybe_api.config import get_settings
from scrybe_api.core.pipeline import ParsePipeline
from scrybe_api.fetchers.dynamic import DynamicFetcher
from scrybe_api.fetchers.static import StaticFetcher
from scrybe_api.jobs.manager import JobManager
from scrybe_api.llm.openai_enricher import OpenAIEnricher
from scrybe_api.parsers.html import HtmlParser
from scrybe_api.parsers.misc import MiscParser
from scrybe_api.parsers.pdf import PdfParser
from scrybe_api.parsers.router import ParserRouter
from scrybe_api.storage.artifacts import ArtifactStore
from scrybe_api.storage.cache import FileCache
from scrybe_api.storage.db import Database
from scrybe_api.storage.repository import JobRepository


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.version, debug=settings.debug)
    web_dir = Path(__file__).resolve().parent.parent / "web"

    liteparse = LiteParseAdapter(settings)
    dynamic_fetcher = DynamicFetcher(settings)
    enricher = OpenAIEnricher(settings)
    pipeline = ParsePipeline(
        settings=settings,
        static_fetcher=StaticFetcher(),
        dynamic_fetcher=dynamic_fetcher,
        parser_router=ParserRouter(
            html_parser=HtmlParser(),
            pdf_parser=PdfParser(liteparse),
            misc_parser=MiscParser(liteparse),
        ),
        cache=FileCache(settings),
        enricher=enricher,
    )
    database = Database(settings)
    repository = JobRepository(database)
    job_manager = JobManager(repository, pipeline)

    app.state.settings = settings
    app.state.liteparse = liteparse
    app.state.dynamic_fetcher = dynamic_fetcher
    app.state.enricher = enricher
    app.state.pipeline = pipeline
    app.state.database = database
    app.state.repository = repository
    app.state.job_manager = job_manager
    app.state.artifacts = ArtifactStore(settings)

    @app.on_event("startup")
    async def startup() -> None:
        await app.state.database.initialize()

    app.mount("/assets", StaticFiles(directory=web_dir), name="assets")

    @app.get("/", include_in_schema=False)
    async def landing() -> FileResponse:
        return FileResponse(web_dir / "index.html")

    app.include_router(router, prefix="/v1")
    return app
