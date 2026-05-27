from pathlib import Path
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Teacher

router = APIRouter(prefix="/teachers", tags=["teachers"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("")
async def teachers_index(request: Request, db: AsyncSession = Depends(get_db)):
    stmt = select(Teacher).options(selectinload(Teacher.lab)).order_by(Teacher.name)
    result = await db.execute(stmt)
    teachers = result.scalars().all()
    return templates.TemplateResponse("teachers/index.html", {"request": request, "teachers": teachers})
