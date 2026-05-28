from pathlib import Path
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app import crud

router = APIRouter(prefix="/explore", tags=["explore"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("")
async def explore_index(request: Request, db: AsyncSession = Depends(get_db)):
    landscape = await crud.get_data_landscape(db)
    labels_all = await crud.get_labels(db)
    labels_by_type: dict[str, list] = {}
    for label in labels_all:
        labels_by_type.setdefault(label.label_type, []).append(label)
    return templates.TemplateResponse("explore/index.html", {
        "request": request,
        **landscape,
        "labels_by_type": labels_by_type,
    })
