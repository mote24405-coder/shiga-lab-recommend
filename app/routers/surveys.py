import uuid
from pathlib import Path
from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app import crud

router = APIRouter(prefix="/surveys", tags=["surveys"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("")
async def survey_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
    run_id: str = Query(default=""),
    survey_type: str = Query(default="post_use"),
):
    questions = await crud.get_survey_questions(db, survey_type)
    return templates.TemplateResponse("surveys/form.html", {
        "request": request,
        "questions": questions,
        "run_id": run_id,
        "survey_type": survey_type,
    })


@router.post("")
async def survey_submit(request: Request, db: AsyncSession = Depends(get_db)):
    form = await request.form()
    session_id = request.session.get("session_id", str(uuid.uuid4()))
    survey_type = form.get("survey_type", "post_use")
    run_id_str = form.get("run_id", "")
    run_id = uuid.UUID(run_id_str) if run_id_str else None

    questions = await crud.get_survey_questions(db, survey_type)
    answers = []
    for q in questions:
        val = form.get(f"q_{q.id}")
        if val is None:
            continue
        if q.question_format == "scale":
            answers.append({"question_id": q.id, "answer_value": int(val)})
        else:
            answers.append({"question_id": q.id, "answer_text": val})

    async with db.begin():
        await crud.create_survey_response(db, session_id, survey_type, run_id, answers)

    return RedirectResponse("/surveys/thanks", status_code=303)


@router.get("/thanks")
async def survey_thanks(request: Request):
    return templates.TemplateResponse("surveys/thanks.html", {"request": request})
