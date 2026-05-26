import uuid
from pathlib import Path
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app import crud
from app.services.recommendation import compute_recommendations
from app.services.label_matcher import get_label_extractor, LABEL_RULES

router = APIRouter(prefix="/recommend", tags=["recommend"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("")
async def recommend_form(request: Request, db: AsyncSession = Depends(get_db)):
    method_labels = await crud.get_labels(db, "method")
    data_labels = await crud.get_labels(db, "data")
    theme_labels = await crud.get_labels(db, "theme")
    return templates.TemplateResponse("recommend/form.html", {
        "request": request,
        "method_labels": method_labels,
        "data_labels": data_labels,
        "theme_labels": theme_labels,
    })


@router.post("")
async def recommend_run(
    request: Request,
    db: AsyncSession = Depends(get_db),
    method_ids: list[int] = Form(default=[]),
    data_ids: list[int] = Form(default=[]),
    theme_ids: list[int] = Form(default=[]),
    free_text: str = Form(default=""),
):
    session_id = request.session.get("session_id", str(uuid.uuid4()))

    # 自由入力からラベル推定
    if free_text.strip():
        all_labels = await crud.get_labels(db)
        label_names = [l.name for l in all_labels]
        extractor = get_label_extractor()
        matched_names = extractor.extract(free_text, label_names)
        name_to_id = {l.name: l.id for l in all_labels}
        for name in matched_names:
            lid = name_to_id.get(name)
            if lid and lid not in method_ids + data_ids + theme_ids:
                label_obj = next((l for l in all_labels if l.id == lid), None)
                if label_obj:
                    if label_obj.label_type == "method" and lid not in method_ids:
                        method_ids = list(method_ids) + [lid]
                    elif label_obj.label_type == "data" and lid not in data_ids:
                        data_ids = list(data_ids) + [lid]
                    elif label_obj.label_type == "theme" and lid not in theme_ids:
                        theme_ids = list(theme_ids) + [lid]

    scores = await compute_recommendations(db, method_ids, data_ids, theme_ids)

    async with db.begin():
        run = await crud.create_recommendation_run(
            db, session_id, method_ids, data_ids, theme_ids,
            free_text or None,
        )
        await crud.create_recommendation_results(db, run.id, scores[:10])

    return RedirectResponse(f"/recommend/{run.id}", status_code=303)


@router.get("/{run_id}")
async def recommend_results(
    request: Request,
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    run = await crud.get_recommendation_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="推薦セッションが見つかりません")
    return templates.TemplateResponse("recommend/results.html", {
        "request": request,
        "run": run,
        "results": sorted(run.results, key=lambda r: r.rank),
    })


@router.post("/{run_id}/feedback")
async def recommend_feedback(
    request: Request,
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    result_id: int | None = Form(default=None),
    feedback_type: str = Form(default="run_overall"),
    rating: int | None = Form(default=None),
    comment: str = Form(default=""),
):
    session_id = request.session.get("session_id", str(uuid.uuid4()))
    async with db.begin():
        await crud.create_feedback(
            db, session_id, run_id, result_id,
            feedback_type, rating, comment or None,
        )
    # HTMXリクエストには小さなHTMLを返す
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("recommend/feedback_thanks.html", {"request": request})
    return RedirectResponse(f"/recommend/{run_id}", status_code=303)
