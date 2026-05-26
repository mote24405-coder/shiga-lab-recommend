import uuid
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.routers import labs, teachers, theses, recommend, search, surveys, admin

settings = get_settings()

app = FastAPI(title="滋賀大学DS研究科 研究室探索", docs_url="/api/docs" if settings.debug else None)

# SessionMiddleware を最後に add → 最外層になり最初に実行される
# その後 ensure_session_id が実行されるためセッションが利用可能
class EnsureSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if "session_id" not in request.session:
            request.session["session_id"] = str(uuid.uuid4())
        return await call_next(request)

app.add_middleware(EnsureSessionMiddleware)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

BASE_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app.include_router(labs.router)
app.include_router(teachers.router)
app.include_router(theses.router)
app.include_router(recommend.router)
app.include_router(search.router)
app.include_router(surveys.router)
app.include_router(admin.router)


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health():
    return {"status": "ok"}
