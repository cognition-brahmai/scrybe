from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from scrybe_api.api.dependencies import get_app_state, require_api_key
from scrybe_api.schemas.api import JobSubmitRequest, MarkdownEnvelope, ParseEnvelope
from scrybe_api.schemas.common import JobResponse, JobStatus, OutputFormat, ParseRequest

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("/health")
async def health(request: Request):
    state = get_app_state(request)
    return {
        "status": "ok",
        "app": state.settings.app_name,
        "version": state.settings.version,
    }


@router.get("/capabilities")
async def capabilities(request: Request):
    state = get_app_state(request)
    return {
        "formats": [member.value for member in OutputFormat],
        "playwright_available": state.dynamic_fetcher.is_available(),
        "liteparse_available": state.liteparse.is_available(),
        "openai_configured": state.enricher.is_configured(),
        "auth_enabled": state.settings.enable_auth,
    }


@router.get("/parse/{format}")
async def parse_get(
    format: OutputFormat,
    request: Request,
    url: str = Query(...),
    use_browser: bool = False,
    chunk: bool = False,
    chunk_strategy: str = "semantic",
    max_chunk_tokens: int = 512,
    summarize: bool = False,
    caption_images: bool = False,
    timeout_seconds: int | None = None,
    force_refresh: bool = False,
):
    parse_request = ParseRequest(
        url=url,
        use_browser=use_browser,
        chunk=chunk,
        chunk_strategy=chunk_strategy,
        max_chunk_tokens=max_chunk_tokens,
        summarize=summarize,
        caption_images=caption_images,
        timeout_seconds=timeout_seconds,
        force_refresh=force_refresh,
    )
    return await _handle_parse(request, parse_request, format)


@router.post("/parse/{format}")
async def parse_post(
    format: OutputFormat,
    parse_request: ParseRequest,
    request: Request,
):
    return await _handle_parse(request, parse_request, format)


@router.post("/jobs", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_job(job_request: JobSubmitRequest, request: Request):
    state = get_app_state(request)
    record = await state.job_manager.submit(job_request)
    return JobResponse(
        job_id=record.job_id,
        status=record.status,
        status_url=f"/v1/jobs/{record.job_id}",
        result_url=None,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, request: Request):
    state = get_app_state(request)
    record = await state.job_manager.get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return record


async def _handle_parse(request: Request, parse_request: ParseRequest, format: OutputFormat):
    state = get_app_state(request)
    if _should_redirect_to_job(parse_request):
        record = await state.job_manager.submit(
            JobSubmitRequest(**parse_request.model_dump(), output_format=format)
        )
        return Response(
            content=JobResponse(
                job_id=record.job_id,
                status=record.status,
                status_url=f"/v1/jobs/{record.job_id}",
                result_url=None,
                created_at=record.created_at,
                updated_at=record.updated_at,
            ).model_dump_json(),
            media_type="application/json",
            status_code=status.HTTP_202_ACCEPTED,
        )

    document = await state.pipeline.parse_url(parse_request)
    if format == OutputFormat.json:
        return ParseEnvelope(format=format, document=document)

    envelope = MarkdownEnvelope(
        source=document.source,
        content_type=document.content_type,
        title=document.metadata.title,
        markdown=document.markdown,
        warnings=document.warnings,
        timings=document.timings.model_dump(),
    )
    response = Response(content=document.markdown, media_type="text/markdown")
    response.headers["X-Scrybe-Source"] = _header_safe(document.source)
    response.headers["X-Scrybe-Content-Type"] = _header_safe(document.content_type)
    response.headers["X-Scrybe-Title"] = _header_safe(document.metadata.title or "")
    response.headers["X-Scrybe-Warnings"] = _header_safe(" | ".join(document.warnings)[:500])
    response.headers["X-Scrybe-Meta"] = _header_safe(envelope.model_dump_json()[:4000])
    return response


def _should_redirect_to_job(parse_request: ParseRequest) -> bool:
    url = str(parse_request.url).lower()
    return (
        parse_request.use_browser
        or parse_request.summarize
        or parse_request.caption_images
        or parse_request.chunk
        or url.endswith(".pdf")
        or url.endswith(".docx")
        or url.endswith(".pptx")
        or url.endswith(".xlsx")
    )


def _header_safe(value: str) -> str:
    return value.encode("latin-1", errors="replace").decode("latin-1")
