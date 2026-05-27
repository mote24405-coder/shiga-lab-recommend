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
    return templates.TemplateResponse("explore/index.html", {
        "request": request,
        **landscape,
    })
