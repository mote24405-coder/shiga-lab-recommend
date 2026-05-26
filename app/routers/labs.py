from pathlib import Path
from fastapi import APIRouter, Request, Depends, Query, Form
from fastapi.responses import Response
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
    match: str = Query(default="or"),
    group_by: str = Query(default="method"),
):
    labels_all = await crud.get_labels(db)
    labs = await crud.get_labs(db, label_ids=label_ids or None, match=match)
    return templates.TemplateResponse("labs/index.html", {
        "request": request,
        "labs": labs,
        "labels_all": labels_all,
        "selected_label_ids": label_ids,
        "match_mode": match,
        "group_by": group_by,
    })


@router.get("/partial")
async def labs_partial(
    request: Request,
    db: AsyncSession = Depends(get_db),
    label_ids: list[int] = Query(default=[]),
    match: str = Query(default="or"),
    group_by: str = Query(default="method"),
):
    """HTMX用：ラベル絞り込み後の研究室リスト断片を返す。"""
    labs = await crud.get_labs(db, label_ids=label_ids or None, match=match)
    return templates.TemplateResponse("labs/partial_list.html", {
        "request": request,
        "labs": labs,
        "group_by": group_by,
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


@router.post("/{lab_id}/view", status_code=204)
async def record_lab_view(
    lab_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    duration_sec: int = Form(default=0),
):
    """Beacon API から呼ばれる滞在時間記録エンドポイント。"""
    session_id = request.session.get("session_id", "")
    await crud.record_lab_view(db, session_id=session_id, lab_id=lab_id, duration_sec=duration_sec)
    await db.commit()
    return Response(status_code=204)


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
