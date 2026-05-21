"""Resource (PDF) gating endpoints."""

from pathlib import Path

import structlog
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse

from app.api.deps import DBSession
from app.core.config import get_settings
from app.schemas.resource import ResourceRequestCreate, ResourceRequestResponse
from app.services.email_service import EmailService
from app.services.pdf_service import PdfService
from app.services.slack_service import SlackChannel, SlackService

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/resources", tags=["resources"])


@router.post(
    "/{slug}/request",
    response_model=ResourceRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def request_resource(
    slug: str, payload: ResourceRequestCreate, db: DBSession
) -> ResourceRequestResponse:
    if not PdfService.known_resource(slug):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown resource")
    if not payload.consent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please confirm you want to receive the guide by email.",
        )

    settings = get_settings()
    pdf = PdfService(db)
    download = await pdf.request_download(
        email=payload.email,
        resource_slug=slug,
        posthog_distinct_id=payload.posthog_distinct_id,
    )

    title = PdfService.resource_title(slug)
    web_origin = settings.cors_origins[0] if settings.cors_origins else "https://career-flow.com"
    download_url = f"{web_origin}/api/download/{download.download_token}"

    await SlackService().post(
        SlackChannel.LEADS,
        text=f"📚 Resource requested: {title} → {payload.email}",
    )
    await EmailService().send(
        to=payload.email,
        from_address=settings.resend_from_noreply,
        subject=f"Your free guide: {title}",
        html=(
            f"<p>Thanks for asking for the {title}.</p>"
            f'<p><a href="{download_url}">Click here to download the PDF</a>. '
            f"This link is valid for 7 days and can be used once.</p>"
            f"<p>— The Career Flow team</p>"
        ),
    )

    return ResourceRequestResponse(message="Check your inbox for the download link.")


@router.get("/{slug}/download", response_model=None)
async def download_resource(slug: str, token: str, db: DBSession) -> FileResponse | JSONResponse:
    pdf = PdfService(db)
    if not PdfService.known_resource(slug):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown resource")
    download = await pdf.validate_token(token)
    if not download or download.resource_slug != slug:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This download link is invalid or has expired.",
        )

    file_path = PdfService.resource_path(slug)
    if not file_path or not Path(file_path).exists():
        # Fall back to JSON if the PDF hasn't been added to the repo yet.
        log.warning("resource.file_missing", slug=slug, file_path=file_path)
        await pdf.mark_downloaded(download)
        return JSONResponse(
            {
                "ok": True,
                "message": (
                    "Your link was valid, but the PDF hasn't been added to the backend yet. "
                    "You'll hear from us shortly with the file."
                ),
            },
            status_code=status.HTTP_200_OK,
        )

    await pdf.mark_downloaded(download)
    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=f"{slug}.pdf",
    )
