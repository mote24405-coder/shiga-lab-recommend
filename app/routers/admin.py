import os
import secrets
from pathlib import Path
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app import crud
from app.models import Lab, Teacher, Thesis, Label, Feedback, SearchLog, SurveyResponse, LabView

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

_security = HTTPBasic()
_ADMIN_USER = os.environ.get("ADMIN_USERNAME", "admin")
_ADMIN_PASS = os.environ.get("ADMIN_PASSWORD", "admin")


def verify_admin(credentials: HTTPBasicCredentials = Depends(_security)):
    ok_user = secrets.compare_digest(credentials.username.encode(), _ADMIN_USER.encode())
    ok_pass = secrets.compare_digest(credentials.password.encode(), _ADMIN_PASS.encode())
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証が必要です",
            headers={"WWW-Authenticate": "Basic"},
        )


@router.get("")
async def admin_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_admin),
):
    counts = {}
    for model, key in [(Lab, "labs"), (Teacher, "teachers"), (Thesis, "theses"),
                       (Label, "labels"), (Feedback, "feedbacks"), (SearchLog, "search_logs"),
                       (LabView, "lab_views")]:
        r = await db.execute(select(func.count()).select_from(model))
        counts[key] = r.scalar()

    popular_labs    = await crud.get_popular_labs(db, limit=5)
    popular_labels  = await crud.get_popular_labels(db, limit=10)

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "counts": counts,
        "popular_labs": popular_labs,
        "popular_labels": popular_labels,
    })


@router.get("/labs")
async def admin_labs(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_admin),
):
    labs = await crud.get_labs(db, limit=500)
    return templates.TemplateResponse("admin/labs.html", {"request": request, "labs": labs})


@router.get("/labels")
async def admin_labels(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_admin),
):
    labels = await crud.get_labels(db)
    return templates.TemplateResponse("admin/labels.html", {"request": request, "labels": labels})


@router.get("/theses")
async def admin_theses(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_admin),
):
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
async def admin_surveys(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_admin),
):
    responses = await crud.get_survey_responses(db, limit=200)
    return templates.TemplateResponse("admin/surveys.html", {"request": request, "responses": responses})


@router.get("/feedbacks")
async def admin_feedbacks(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_admin),
):
    feedbacks = await crud.get_feedbacks(db, limit=200)
    return templates.TemplateResponse("admin/feedbacks.html", {"request": request, "feedbacks": feedbacks})


@router.get("/search_logs")
async def admin_search_logs(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_admin),
):
    logs = await crud.get_search_logs(db, limit=200)
    return templates.TemplateResponse("admin/search_logs.html", {"request": request, "logs": logs})
