from pathlib import Path
from fastapi import APIRouter, Request, Depends, Query
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app import crud

router = APIRouter(prefix="/labs", tags=["labs"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("")
async def labs_index(
    request: Request,
    db: AsyncSession = Depends(get_db),
    label_ids: list[int] = Query(default=[]),
):
    labels_all = await crud.get_labels(db)
    labs = await crud.get_labs(db, label_ids=label_ids or None)
    return templates.TemplateResponse("labs/index.html", {
        "request": request,
        "labs": labs,
        "labels_all": labels_all,
        "selected_label_ids": label_ids,
    })


@router.get("/partial")
async def labs_partial(
    request: Request,
    db: AsyncSession = Depends(get_db),
    label_ids: list[int] = Query(default=[]),
):
    """HTMX用：ラベル絞り込み後の研究室リスト断片を返す。"""
    labs = await crud.get_labs(db, label_ids=label_ids or None)
    return templates.TemplateResponse("labs/partial_list.html", {
        "request": request,
        "labs": labs,
    })


@router.get("/compare")
async def labs_compare(
    request: Request,
    db: AsyncSession = Depends(get_db),
    ids: str = Query(default=""),
):
    lab_ids = [int(i) for i in ids.split(",") if i.strip().isdigit()]
    labs = await crud.get_labs_by_ids(db, lab_ids) if lab_ids else []
    return templates.TemplateResponse("labs/compare.html", {
        "request": request,
        "labs": labs,
    })


@router.get("/{lab_id}")
async def lab_detail(
    request: Request,
    lab_id: int,
    db: AsyncSession = Depends(get_db),
):
    lab = await crud.get_lab(db, lab_id)
    if lab is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="研究室が見つかりません")
    return templates.TemplateResponse("labs/detail.html", {
        "request": request,
        "lab": lab,
    })
