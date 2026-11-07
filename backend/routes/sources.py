"""Official source locators only; no arbitrary file serving or URL input."""
from urllib.parse import urlparse
from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix='/api/sources', tags=['sources'])

@router.get('/{document_id}')
def source(document_id: str, request: Request):
    state = request.app.state.backend
    if not state.rag_ready:
        raise HTTPException(status_code=503, detail='rag_not_ready')
    try:
        locator = state.runtime.source_locator(document_id)
    except KeyError:
        raise HTTPException(status_code=404, detail='source_not_found') from None
    if document_id in ('runtime_catalog_ar','runtime_catalog_en') and locator.get('source_type')=='runtime_catalog':
        return {'document_id':document_id, **locator}
    parsed = urlparse(locator.get('source_url') or '')
    host = parsed.hostname or ''
    if parsed.scheme != 'https' or not (host == 'najah.edu' or host.endswith('.najah.edu')):
        raise HTTPException(status_code=404, detail='official_source_unavailable')
    return {'document_id': document_id, **locator}
