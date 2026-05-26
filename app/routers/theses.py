from pathlib import Path
from fastapi import APIRouter, Request, Depends, Query
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Thesis, ThesisLabel

router = APIRouter(prefix="/theses", tags=["theses"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("")
async def theses_index(
    request: Request,
    db: AsyncSession = Depends(get_db),
    year: int | None = Query(default=None),
):
    stmt = (
        select(Thesis)
        .options(
            selectinload(Thesis.lab),
            selectinload(Thesis.thesis_labels).selectinload(ThesisLabel.label),
        )
        .order_by(Thesis.year.desc(), Thesis.title)
    )
    if year:
        stmt = stmt.where(Thesis.year == year)
    result = await db.execute(stmt)
    theses = result.scalars().all()
    return templates.TemplateResponse("theses/index.html", {"request": request, "theses": theses, "year": year})
