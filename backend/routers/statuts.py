import asyncio
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/entreprises", tags=["statuts"])


def _clean_bce(bce: str) -> str:
    return bce.replace(".", "").strip()


async def statuts_event_generator(bce: str):
    """Lance le scraping stapor.py en thread, streame chaque statut des reception (SSE)."""
    import sys
    sys.path.insert(0, "/app")
    from stapor import get_session, get_statutes, download_statute_pdf

    bce_clean = _clean_bce(bce)
    loop = asyncio.get_event_loop()

    try:
        session = await loop.run_in_executor(None, get_session)
        statutes = await loop.run_in_executor(None, get_statutes, session, bce_clean)

        if not statutes:
            yield f"data: {json.dumps({'type': 'end', 'message': 'Aucun statut trouve'})}\n\n"
            return

        for statute in statutes:
            pdf_path = await loop.run_in_executor(
                None, download_statute_pdf, session, bce_clean, statute
            )
            payload = {
                "type": "document",
                "deed_date": statute.get("deedDate"),
                "document_title": statute.get("documentTitle"),
                "document_id": statute.get("documentId"),
                "downloaded": pdf_path is not None,
            }
            yield f"data: {json.dumps(payload)}\n\n"
            await asyncio.sleep(0.1)

        yield f"data: {json.dumps({'type': 'end', 'message': f'{len(statutes)} statuts traites'})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"


@router.get("/{bce}/statuts")
async def stream_statuts(bce: str):
    """Streame les statuts notaire au fur et a mesure (SSE)."""
    return StreamingResponse(
        statuts_event_generator(bce),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )