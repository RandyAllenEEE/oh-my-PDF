from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    BackgroundTasks,
    HTTPException,
    File,
    UploadFile,
    Query,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import json
import os
import sys
import asyncio
import socket
import traceback
import re
import threading
import webbrowser
from urllib.parse import quote
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import uuid

from src.services.ocr_service import OCRService

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("pdf_toolbox")

APP_VERSION = "0.2.0"

app = FastAPI(title="PDF Toolbox Backend", version=APP_VERSION)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_BACKEND_PORT = 17654
DEFAULT_FRONTEND_DEV_PORT = 17655
LOCAL_ORIGIN_REGEX = r"https?://(localhost|127\.0\.0\.1):\d+"

origins = ["app://."]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=LOCAL_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class TaskInfo:
    task_id: str
    status: TaskStatus
    task_type: str
    input_path: str
    output_path: str
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    progress: int = 0


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("Client connected to WebSocket")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info("Client disconnected from WebSocket")

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)

    def broadcast_sync(self, message: dict):
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self.broadcast(message), self.loop)


manager = ConnectionManager()
ocr_service: Optional[OCRService] = None
task_registry: Dict[str, TaskInfo] = {}


def resolve_config_path():
    env_config = os.environ.get("PDF_TOOLBOX_CONFIG_PATH")
    if env_config:
        logger.info(f"Using config from environment variable: {env_config}")
        return Path(env_config).absolute()

    cwd_config = Path("config.json")
    if cwd_config.exists():
        return cwd_config.absolute()

    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent

        if exe_dir.name.lower() == "resources":
            return (exe_dir.parent / "config.json").absolute()

        exe_config = exe_dir / "config.json"
        if exe_config.exists():
            return exe_config.absolute()

        return exe_config.absolute()
    else:
        return (Path(__file__).parent.parent / "config.json").absolute()


CONFIG_PATH = resolve_config_path()
BASE_DIR = CONFIG_PATH.parent
PROJECT_ROOT = BASE_DIR.parent
WORKSPACE_DIR = BASE_DIR / "workspace"
UPLOAD_DIR = WORKSPACE_DIR / "uploads"
OUTPUT_DIR = WORKSPACE_DIR / "outputs"
logger.info(f"Using config at: {CONFIG_PATH}")


def ensure_workspace_dirs():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def setup_dependencies():
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        deps_paths = [
            exe_dir / "dependencies" / "pngquant",
            exe_dir / "dependencies" / "unpaper",
        ]
    else:
        deps_paths = [
            BASE_DIR / "dependencies" / "pngquant",
            BASE_DIR / "dependencies" / "unpaper",
        ]

    current_path = os.environ.get("PATH", "")
    for p in deps_paths:
        if p.exists() and str(p) not in current_path:
            logger.info(f"Adding to PATH: {p}")
            os.environ["PATH"] = str(p) + os.pathsep + os.environ["PATH"]


setup_dependencies()


def load_config():
    logger.info(f"Loading config from: {CONFIG_PATH}")
    if CONFIG_PATH.exists():
        try:
            content = CONFIG_PATH.read_text(encoding="utf-8")
            data = json.loads(content)
            logger.info("Config file loaded successfully.")
            return data
        except Exception as e:
            logger.error(f"Failed to read config file: {e}")
    else:
        logger.info("Config file not found, using default settings.")

    return get_default_config()


def safe_filename(filename: str) -> str:
    name = Path(filename or "document.pdf").name
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    if not safe_name:
        safe_name = "document.pdf"
    if not safe_name.lower().endswith(".pdf"):
        safe_name += ".pdf"
    return safe_name


def make_output_path(input_path: Path, suffix: str) -> Path:
    ensure_workspace_dirs()
    output_name = f"{input_path.stem}{suffix}.pdf"
    return OUTPUT_DIR / output_name


def is_within_workspace(path: Path) -> bool:
    try:
        path.resolve().relative_to(WORKSPACE_DIR.resolve())
        return True
    except ValueError:
        return False


def resolve_download_path(path: str) -> Path:
    resolved = Path(path).expanduser().resolve()
    if not resolved.exists() or not resolved.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    if not is_within_workspace(resolved):
        raise HTTPException(
            status_code=403, detail="Downloads are limited to workspace files"
        )
    return resolved


def resolve_workspace_file(path: str) -> Path:
    resolved = Path(path).expanduser().resolve()
    if not is_within_workspace(resolved):
        raise HTTPException(
            status_code=403, detail="File access is limited to workspace files"
        )
    if not resolved.exists() or not resolved.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return resolved


def resolve_workspace_output(path: str) -> Path:
    resolved = Path(path).expanduser().resolve()
    if not is_within_workspace(resolved):
        raise HTTPException(
            status_code=403, detail="Output path is limited to workspace files"
        )
    if resolved.exists() and not resolved.is_file():
        raise HTTPException(status_code=400, detail="Output path is not a file")
    return resolved


def download_url_for(path: str) -> str:
    return f"/api/files/download?path={quote(str(Path(path).resolve()))}"


def task_to_response(task_info: TaskInfo) -> Dict[str, Any]:
    response = {
        "task_id": task_info.task_id,
        "status": task_info.status.value,
        "task_type": task_info.task_type,
        "input_path": task_info.input_path,
        "output_path": task_info.output_path,
        "created_at": task_info.created_at.isoformat(),
        "completed_at": (
            task_info.completed_at.isoformat() if task_info.completed_at else None
        ),
        "error_message": task_info.error_message,
        "progress": task_info.progress,
    }
    if task_info.status == TaskStatus.SUCCESS and task_info.output_path:
        response["download_url"] = download_url_for(task_info.output_path)
    return response


def get_default_config() -> Dict[str, Any]:
    return {
        "app_settings": {"language": "en"},
        "selected_engine": "tesseract",
        "engines": {
            "tesseract": {"provider": "native", "bin_path": "", "languages": "eng"},
            "paddle": {
                "provider": "api",
                "api": {
                    "selected_model": "PP-OCRv5",
                    "key": "",
                    "models": {
                        "PP-OCRv5": {
                            "url": "https://aistudio.baidu.com/paddleocr/task/xxxx/ocr",
                            "useDocOrientationClassify": False,
                            "useDocUnwarping": False,
                            "useTextlineOrientation": False,
                        },
                        "PP-StructureV3": {
                            "url": "https://aistudio.baidu.com/paddleocr/task/xxxx/layout-parsing",
                            "useDocOrientationClassify": False,
                            "useDocUnwarping": False,
                            "useTableRecognition": True,
                            "useFormulaRecognition": True,
                            "useSealRecognition": False,
                            "useChartRecognition": False,
                            "useRegionDetection": True,
                        },
                        "PaddleOCR-VL": {
                            "url": "https://aistudio.baidu.com/paddleocr/task/xxxx/layout-parsing",
                            "useDocOrientationClassify": False,
                            "useDocUnwarping": False,
                            "useLayoutDetection": True,
                        },
                        "PaddleOCR-VL-1.5": {
                            "url": "https://aistudio.baidu.com/paddleocr/task/xxxx/layout-parsing",
                            "useDocOrientationClassify": False,
                            "useDocUnwarping": False,
                            "useLayoutDetection": True,
                            "repetitionPenalty": 1.0,
                            "temperature": 0.1,
                            "topP": 0.7,
                        },
                    },
                },
            },
            "deepseek": {
                "provider": "ollama",
                "ollama": {"url": "http://localhost:11434", "model": "deepseek-vl2"},
            },
            "mineru": {
                "provider": "api",
                "api": {
                    "url": "https://mineru.net/api/v4/file-urls/batch",
                    "model": "pipeline",
                    "key": "",
                    "is_ocr": False,
                    "enable_formula": True,
                    "enable_table": True,
                    "language": "ch",
                },
            },
        },
        "bookmark_models": {
            "vlm": {
                "enabled": False,
                "provider": "openai",
                "base_url": "https://api.openai.com/v1",
                "api_key": "",
                "model_name": "gpt-4o",
                "prompt": "Extract the table of contents from these images. Return each line as 'Title @ PageNumber' and use indentation to represent hierarchy. Do not include any other text.",
            },
            "llm": {
                "enabled": False,
                "provider": "openai",
                "base_url": "https://api.openai.com/v1",
                "api_key": "",
                "model_name": "gpt-4o-mini",
                "prompt": "The following text is a raw table of contents from a PDF. Clean it up and return each line as 'Title @ PageNumber'. Use indentation to represent hierarchy. Raw text:\n\n{text}",
            },
        },
    }


@app.on_event("startup")
async def startup_event():
    global ocr_service
    manager.set_loop(asyncio.get_running_loop())
    ensure_workspace_dirs()
    config = load_config()
    ocr_service = OCRService(config)
    logger.info("OCRService initialized")


class ConfigModel(BaseModel):
    app_settings: Dict[str, Any]
    selected_engine: str
    engines: Dict[str, Any]
    bookmark_models: Optional[Dict[str, Any]] = None


@app.get("/api/config")
def get_config():
    return load_config()


@app.post("/api/config")
def update_config(config: ConfigModel):
    try:
        logger.info(f"Saving config to: {CONFIG_PATH}")
        CONFIG_PATH.write_text(
            json.dumps(config.dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )

        global ocr_service
        ocr_service = OCRService(config.dict())

        logger.info("Configuration updated and saved.")
        return {"status": "updated", "config": config.dict()}
    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/files/upload")
async def upload_pdf(file: UploadFile = File(...)):
    original_name = file.filename or ""
    filename = safe_filename(file.filename or "document.pdf")
    is_pdf_name = original_name.lower().endswith(".pdf")
    is_pdf_type = file.content_type in (None, "", "application/pdf")
    if not is_pdf_name and not is_pdf_type:
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    ensure_workspace_dirs()
    stored_name = f"{uuid.uuid4().hex}_{filename}"
    stored_path = UPLOAD_DIR / stored_name

    try:
        with stored_path.open("wb") as out:
            while chunk := await file.read(1024 * 1024):
                out.write(chunk)
    finally:
        await file.close()

    return {
        "status": "success",
        "filename": filename,
        "path": str(stored_path.resolve()),
        "size": stored_path.stat().st_size,
    }


@app.get("/api/files/download")
def download_file(path: str = Query(...)):
    resolved = resolve_download_path(path)
    return FileResponse(
        resolved,
        media_type="application/pdf",
        filename=resolved.name,
    )


class OCRRequest(BaseModel):
    input_path: str
    output_path: Optional[str] = None
    engine: str = "tesseract"
    language: Optional[str] = None
    ocr_mode: str = "normal"
    deskew: bool = False
    optimize: int = 1


def run_ocr_task(
    task_id: str,
    input_path: str,
    output_path: str,
    engine: str,
    language: Optional[str] = None,
    ocr_mode: str = "normal",
    deskew: bool = False,
    optimize: int = 1,
):
    task_info = task_registry.get(task_id)
    if task_info:
        task_info.status = TaskStatus.RUNNING

    logger.info(
        f"[Task {task_id}] Starting OCR: {input_path} -> {output_path} using {engine}"
    )

    try:
        inp = Path(input_path)
        out = Path(output_path)

        if not inp.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        out.parent.mkdir(parents=True, exist_ok=True)

        if ocr_service is None:
            raise RuntimeError("OCR service not initialized")

        ocr_service.run_ocr(
            inp,
            out,
            engine,
            task_language=language,
            ocr_mode=ocr_mode,
            deskew=deskew,
            optimize=optimize,
        )

        if task_info:
            task_info.status = TaskStatus.SUCCESS
            task_info.completed_at = datetime.now()
            task_info.progress = 100

        logger.info(f"[Task {task_id}] OCR completed successfully")

        manager.broadcast_sync(
            {
                "type": "task_complete",
                "task_id": task_id,
                "status": "success",
                "output_path": output_path,
                "download_url": download_url_for(output_path),
            }
        )

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        stack_trace = traceback.format_exc()

        logger.error(f"[Task {task_id}] OCR failed: {error_msg}")
        logger.debug(f"[Task {task_id}] Stack trace:\n{stack_trace}")

        if task_info:
            task_info.status = TaskStatus.FAILED
            task_info.completed_at = datetime.now()
            task_info.error_message = error_msg

        manager.broadcast_sync(
            {
                "type": "task_complete",
                "task_id": task_id,
                "status": "failed",
                "error": error_msg,
            }
        )


@app.post("/api/ocr")
async def start_ocr(request: OCRRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())[:8]
    input_path = resolve_workspace_file(request.input_path)
    output_path = (
        resolve_workspace_output(request.output_path)
        if request.output_path
        else make_output_path(input_path, "_ocr")
    )

    task_info = TaskInfo(
        task_id=task_id,
        status=TaskStatus.PENDING,
        task_type="ocr",
        input_path=str(input_path),
        output_path=str(output_path),
    )
    task_registry[task_id] = task_info

    background_tasks.add_task(
        run_ocr_task,
        task_id,
        str(input_path),
        str(output_path),
        request.engine,
        request.language,
        request.ocr_mode,
        request.deskew,
        request.optimize,
    )

    return {
        "status": "accepted",
        "task_id": task_id,
        "output_path": str(output_path),
        "message": "OCR task started",
    }


@app.get("/api/tasks/{task_id}")
def get_task_status(task_id: str):
    task_info = task_registry.get(task_id)
    if not task_info:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return task_to_response(task_info)


from src.services.bookmark_service import BookmarkService

bookmark_service = BookmarkService()


class BookmarkRequest(BaseModel):
    input_path: str
    output_path: Optional[str] = None
    toc_text: str
    page_offset: int = 0


def run_bookmark_task(
    task_id: str, input_path: str, output_path: str, toc_text: str, page_offset: int
):
    task_info = task_registry.get(task_id)
    if task_info:
        task_info.status = TaskStatus.RUNNING

    logger.info(
        f"[Task {task_id}] Starting Bookmark task: {input_path} -> {output_path}"
    )

    try:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        bookmark_service.add_bookmarks(input_path, output_path, toc_text, page_offset)

        if task_info:
            task_info.status = TaskStatus.SUCCESS
            task_info.completed_at = datetime.now()
            task_info.progress = 100

        logger.info(f"[Task {task_id}] Bookmark task completed successfully")

        manager.broadcast_sync(
            {
                "type": "task_complete",
                "task_id": task_id,
                "status": "success",
                "output_path": output_path,
                "download_url": download_url_for(output_path),
            }
        )

    except Exception as e:
        error_msg = str(e)
        logger.error(f"[Task {task_id}] Bookmark task failed: {error_msg}")

        if task_info:
            task_info.status = TaskStatus.FAILED
            task_info.completed_at = datetime.now()
            task_info.error_message = error_msg

        manager.broadcast_sync(
            {
                "type": "task_complete",
                "task_id": task_id,
                "status": "failed",
                "error": error_msg,
            }
        )


@app.post("/api/bookmarks/add")
async def add_bookmarks(request: BookmarkRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())[:8]
    input_path = resolve_workspace_file(request.input_path)
    output_path = (
        resolve_workspace_output(request.output_path)
        if request.output_path
        else make_output_path(input_path, "_bookmarked")
    )

    task_info = TaskInfo(
        task_id=task_id,
        status=TaskStatus.PENDING,
        task_type="bookmark",
        input_path=str(input_path),
        output_path=str(output_path),
    )
    task_registry[task_id] = task_info

    background_tasks.add_task(
        run_bookmark_task,
        task_id,
        str(input_path),
        str(output_path),
        request.toc_text,
        request.page_offset,
    )

    return {
        "status": "accepted",
        "task_id": task_id,
        "output_path": str(output_path),
        "message": "Bookmark task started",
    }


class BookmarkExtractRequest(BaseModel):
    input_path: str


@app.post("/api/bookmarks/extract")
def extract_bookmarks(request: BookmarkExtractRequest):
    try:
        input_path = resolve_workspace_file(request.input_path)
        toc_text = bookmark_service.extract_bookmarks(str(input_path))
        return {"status": "success", "toc_text": toc_text}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Extract bookmarks failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


from src.services.llm_service import LLMService

llm_service = LLMService()


class PageOCRRequest(BaseModel):
    input_path: str
    start_page: int
    end_page: int
    config: Dict[str, Any]


@app.post("/api/bookmarks/ocr_page")
def ocr_pdf_page(request: PageOCRRequest):
    try:
        path = resolve_workspace_file(request.input_path)

        result = llm_service.call_vlm(
            path, request.start_page, request.end_page, request.config
        )
        return {"status": "success", "text": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"VLM Page OCR failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class CleanTextRequest(BaseModel):
    text: str
    config: Dict[str, Any]


@app.post("/api/bookmarks/clean_text")
def clean_bookmark_text(request: CleanTextRequest):
    try:
        result = llm_service.call_llm(request.text, request.config)
        return {"status": "success", "text": result}
    except Exception as e:
        logger.error(f"LLM Clean Text failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "version": APP_VERSION,
        "message": "PDF Toolbox Backend Running",
    }


@app.websocket("/ws/progress")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug(f"Received WebSocket message: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


def resolve_frontend_dist() -> Path:
    if getattr(sys, "frozen", False):
        bundled_root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        bundled_dist = bundled_root / "frontend" / "dist"
        if bundled_dist.exists():
            return bundled_dist
        return Path(sys.executable).parent / "frontend" / "dist"
    return PROJECT_ROOT / "frontend" / "dist"


FRONTEND_DIST = resolve_frontend_dist()
if FRONTEND_DIST.exists():
    logger.info(f"Serving frontend from: {FRONTEND_DIST}")
    app.mount(
        "/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend"
    )
else:
    logger.info(f"Frontend dist not found: {FRONTEND_DIST}")

    @app.get("/")
    def read_root():
        return {
            "status": "ok",
            "message": "PDF Toolbox Backend Running",
            "frontend": "not built",
        }


def parse_port(value: str, env_name: str = "PDF_TOOLBOX_PORT") -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise ValueError(f"{env_name} must be an integer port") from exc
    if not 1 <= port <= 65535:
        raise ValueError(f"{env_name} must be between 1 and 65535")
    return port


def requested_server_port(default: int = DEFAULT_BACKEND_PORT) -> int:
    env_port = os.environ.get("PDF_TOOLBOX_PORT")
    if not env_port:
        return default
    return parse_port(env_port)


def port_is_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def find_available_port(host: str) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def choose_server_port(
    host: str = DEFAULT_HOST, preferred_port: Optional[int] = None
) -> int:
    port = preferred_port if preferred_port is not None else requested_server_port()
    if port_is_available(host, port):
        return port

    fallback_port = find_available_port(host)
    logger.warning(
        f"Port {port} is already in use on {host}; using {fallback_port} instead."
    )
    return fallback_port


def browser_host_for(host: str) -> str:
    return DEFAULT_HOST if host in {"0.0.0.0", "::"} else host


def make_start_url(host: str = DEFAULT_HOST, port: int = DEFAULT_BACKEND_PORT) -> str:
    return f"http://{browser_host_for(host)}:{port}"


START_URL = make_start_url()


def maybe_open_browser(url: str = START_URL) -> bool:
    if os.environ.get("PDF_TOOLBOX_NO_BROWSER") == "1":
        logger.info("Automatic browser opening disabled by PDF_TOOLBOX_NO_BROWSER=1")
        return False
    try:
        return bool(webbrowser.open(url))
    except Exception as e:
        logger.warning(f"Failed to open browser automatically: {e}")
        return False


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("PDF_TOOLBOX_HOST", DEFAULT_HOST)
    port = choose_server_port(host)
    start_url = make_start_url(host, port)

    threading.Timer(1.0, lambda: maybe_open_browser(start_url)).start()
    uvicorn.run(app, host=host, port=port)
