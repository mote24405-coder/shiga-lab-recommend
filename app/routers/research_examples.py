from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.database import get_db
from app.services.research_examples import (
    count_examples_by_theme,
    filter_examples_by_theme,
    sort_research_examples,
)

router = APIRouter(prefix="/research-examples", tags=["research-examples"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("")
async def research_examples_index(
    request: Request,
    db: AsyncSession = Depends(get_db),
    theme: int | None = Query(default=None),
):
    examples = sort_research_examples(await crud.list_research_example_candidates(db))
    themes = count_examples_by_theme(examples)
    selected_theme = next((research_theme for research_theme in themes if research_theme.id == theme), None)
    return templates.TemplateResponse("research_examples/index.html", {
        "request": request,
        "examples": filter_examples_by_theme(examples, theme),
        "themes": themes,
        "selected_theme_id": theme,
        "selected_theme": selected_theme,
        "total_count": len(examples),
    })


@router.get("/{thesis_id}")
async def open_research_example(thesis_id: int, db: AsyncSession = Depends(get_db)):
    thesis = await crud.find_thesis(db, thesis_id)
    if thesis is None:
        raise HTTPException(status_code=404, detail="論文が見つかりません")
    if thesis.lab_id is None:
        return RedirectResponse(url=f"/theses#thesis-{thesis.id}", status_code=303)
    return RedirectResponse(url=f"/labs/{thesis.lab_id}#thesis-{thesis.id}", status_code=303)
