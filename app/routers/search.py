from pathlib import Path
from fastapi import APIRouter, Request, Depends, Query
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app import crud
from app.services.search import search_labs

router = APIRouter(prefix="/search", tags=["search"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("")
async def search_view(
    request: Request,
    db: AsyncSession = Depends(get_db),
    q: str = Query(default=""),
    label_ids: list[int] = Query(default=[]),
):
    results, expanded = [], []
    if q.strip():
        results, expanded = await search_labs(db, q.strip(), label_ids or None)
        from app.crud import create_search_log
        await create_search_log(
            db,
            session_id=request.session.get("session_id", ""),
            query_text=q,
            expanded_keywords=expanded,
            result_count=len(results),
        )
        await db.commit()

    return templates.TemplateResponse("search/results.html", {
        "request": request,
        "query": q,
        "results": results,
        "expanded": expanded,
        "label_ids": label_ids,
    })


@router.get("/suggestions")
async def search_suggestions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    q: str = Query(default=""),
):
    """HTMX用：入力候補を返す。"""
    suggestions = []
    if len(q.strip()) >= 2:
        results, _ = await search_labs(db, q.strip())
        suggestions = [r.lab_name for r in results[:5]]
    return templates.TemplateResponse("search/suggestions.html", {
        "request": request,
        "suggestions": suggestions,
        "query": q,
    })
