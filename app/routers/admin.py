from pathlib import Path
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app import crud
from app.models import Lab, Teacher, Thesis, Label, Feedback, SearchLog, SurveyResponse

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

# MVP: 認証なし。将来 Depends(verify_admin) を追加する。


@router.get("")
async def admin_dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    counts = {}
    for model, key in [(Lab, "labs"), (Teacher, "teachers"), (Thesis, "theses"),
                       (Label, "labels"), (Feedback, "feedbacks"), (SearchLog, "search_logs")]:
        r = await db.execute(select(func.count()).select_from(model))
        counts[key] = r.scalar()
    return templates.TemplateResponse("admin/dashboard.html", {"request": request, "counts": counts})


@router.get("/labs")
async def admin_labs(request: Request, db: AsyncSession = Depends(get_db)):
    labs = await crud.get_labs(db, limit=500)
    return templates.TemplateResponse("admin/labs.html", {"request": request, "labs": labs})


@router.get("/labels")
async def admin_labels(request: Request, db: AsyncSession = Depends(get_db)):
    labels = await crud.get_labels(db)
    return templates.TemplateResponse("admin/labels.html", {"request": request, "labels": labels})


@router.get("/theses")
async def admin_theses(request: Request, db: AsyncSession = Depends(get_db)):
    from sqlalchemy.orm import selectinload
    from app.models import ThesisLabel
    stmt = select(Thesis).options(
        selectinload(Thesis.lab),
        selectinload(Thesis.thesis_labels).selectinload(ThesisLabel.label),
    ).order_by(Thesis.year.desc()).limit(500)
    result = await db.execute(stmt)
    theses = result.scalars().all()
    return templates.TemplateResponse("admin/theses.html", {"request": request, "theses": theses})


@router.get("/surveys")
async def admin_surveys(request: Request, db: AsyncSession = Depends(get_db)):
    responses = await crud.get_survey_responses(db, limit=200)
    return templates.TemplateResponse("admin/surveys.html", {"request": request, "responses": responses})


@router.get("/feedbacks")
async def admin_feedbacks(request: Request, db: AsyncSession = Depends(get_db)):
    feedbacks = await crud.get_feedbacks(db, limit=200)
    return templates.TemplateResponse("admin/feedbacks.html", {"request": request, "feedbacks": feedbacks})


@router.get("/search_logs")
async def admin_search_logs(request: Request, db: AsyncSession = Depends(get_db)):
    logs = await crud.get_search_logs(db, limit=200)
    return templates.TemplateResponse("admin/search_logs.html", {"request": request, "logs": logs})
