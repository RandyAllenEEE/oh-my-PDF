from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import logging
import json
import shutil
from src.services.ocr_service import OCRService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pdf_toolbox")

app = FastAPI(title="PDF Toolbox Backend", version="0.1.0")

# CORS Configuration
origins = [
    "http://localhost:5173",  # Vite default
    "http://localhost:3000",
    "app://."                 # Electron
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("Client connected to WebSocket")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info("Client disconnected from WebSocket")

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")

manager = ConnectionManager()
ocr_service = None

import sys

def resolve_config_path():
    # 0. Prioritize environment variable from Electron
    env_config = os.environ.get('PDF_TOOLBOX_CONFIG_PATH')
    if env_config:
        logger.info(f"Using config from environment variable: {env_config}")
        return Path(env_config).absolute()

    # 1. Try CWD first (often set by Electron or shell)
    cwd_config = Path("config.json")
    if cwd_config.exists():
        return cwd_config.absolute()

    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
        
        # 2. If we are in 'resources' folder, prioritize parent (app root)
        if exe_dir.name.lower() == 'resources':
            return (exe_dir.parent / "config.json").absolute()

        # 3. Try next to executable
        exe_config = exe_dir / "config.json"
        if exe_config.exists():
            return exe_config.absolute()
        
        return exe_config.absolute()
    else:
        # Development
        return (Path(__file__).parent.parent / "config.json").absolute()

CONFIG_PATH = resolve_config_path()
BASE_DIR = CONFIG_PATH.parent
logger.info(f"Using config at: {CONFIG_PATH}")

# Inject dependencies into PATH
import os
def setup_dependencies():
    if getattr(sys, 'frozen', False):
        # In standalone mode, look for dependencies as siblings to the exe
        exe_dir = Path(sys.executable).parent
        deps_paths = [
            exe_dir / "dependencies" / "pngquant",
            exe_dir / "dependencies" / "unpaper"
        ]
    else:
        # Development
        deps_paths = [
            BASE_DIR / "dependencies" / "pngquant",
            BASE_DIR / "dependencies" / "unpaper"
        ]
    
    current_path = os.environ.get('PATH', '')
    for p in deps_paths:
        if p.exists() and str(p) not in current_path:
            logger.info(f"Adding to PATH: {p}")
            os.environ['PATH'] = str(p) + os.pathsep + os.environ['PATH']

setup_dependencies()

# setup_dependencies() is called above
def load_config():
    logger.info(f"Loading config from: {CONFIG_PATH}")
    print(f"DEBUG: Loading config from: {CONFIG_PATH}")
    if CONFIG_PATH.exists():
        try:
            content = CONFIG_PATH.read_text(encoding="utf-8")
            data = json.loads(content)
            logger.info("Config file loaded successfully.")
            return data
        except Exception as e:
            logger.error(f"Failed to read config file: {e}")
            print(f"DEBUG: Failed to read config file: {e}")
    else:
        logger.info("Config file not found, using default settings.")
        print(f"DEBUG: Config file NOT found at: {CONFIG_PATH}")
    
    return {
        "app_settings": {
            "language": "en"
        },
        "selected_engine": "tesseract",
        "engines": {
            "tesseract": {
                "provider": "native",
                "bin_path": "",
                "languages": "eng"
            },
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
                            "useTextlineOrientation": False
                        },
                        "PP-StructureV3": {
                            "url": "https://aistudio.baidu.com/paddleocr/task/xxxx/layout-parsing",
                            "useDocOrientationClassify": False,
                            "useDocUnwarping": False,
                            "useTableRecognition": True,
                            "useFormulaRecognition": True,
                            "useSealRecognition": False,
                            "useChartRecognition": False,
                            "useRegionDetection": True
                        },
                        "PaddleOCR-VL": {
                            "url": "https://aistudio.baidu.com/paddleocr/task/xxxx/layout-parsing",
                            "useDocOrientationClassify": False,
                            "useDocUnwarping": False,
                            "useLayoutDetection": True
                        },
                        "PaddleOCR-VL-1.5": {
                            "url": "https://aistudio.baidu.com/paddleocr/task/xxxx/layout-parsing",
                            "useDocOrientationClassify": False,
                            "useDocUnwarping": False,
                            "useLayoutDetection": True,
                            "repetitionPenalty": 1.0,
                            "temperature": 0.1,
                            "topP": 0.7
                        }
                    }
                },
                "ollama": {
                    "url": "http://localhost:11434",
                    "model": "paddle_model_placeholder"
                }
            },
            "deepseek": {
                "provider": "ollama",
                "ollama": {
                    "url": "http://localhost:11434",
                    "model": "deepseek-vl2"
                }
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
                    "language": "ch"
                }
            }
        },
        "bookmark_models": {
            "vlm": {
                "enabled": False,
                "provider": "openai",
                "base_url": "https://api.openai.com/v1",
                "api_key": "",
                "model_name": "gpt-4o",
                "prompt": "Extract the table of contents from these images. Return the results in a structured format: each line should be 'Title @ PageNumber', using indentation (spaces or tabs) to represent hierarchy. Do not include any other text."
            },
            "llm": {
                "enabled": False,
                "provider": "openai",
                "base_url": "https://api.openai.com/v1",
                "api_key": "",
                "model_name": "gpt-4o-mini",
                "prompt": "The following text is a raw extraction of a Table of Contents from a PDF. Please clean it up and format it correctly. Each line should be 'Title @ PageNumber'. Use indentation to represent hierarchy. If a page number is missing or incorrect, try to infer it from context or leave it as @0. Raw text:\n\n{text}"
            }
        }
    }

@app.on_event("startup")
async def startup_event():
    global ocr_service
    config = load_config()
    ocr_service = OCRService(config)

# Config Models
from typing import Dict, Any
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
        # Save to file
        logger.info(f"Saving config to: {CONFIG_PATH}")
        print(f"DEBUG: Saving config to: {CONFIG_PATH}")
        CONFIG_PATH.write_text(json.dumps(config.dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        
        # Reload service with new config
        global ocr_service
        ocr_service = OCRService(config.dict())
        
        logger.info("Configuration updated and saved.")
        return {"status": "updated", "config": config.dict()}
    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class OCRRequest(BaseModel):
    input_path: str
    output_path: str
    engine: str = "tesseract"
    language: Optional[str] = None # Task-specific language (e.g. for MinerU pipeline)
    deskew: bool = False
    optimize: int = 1

def run_ocr_task(input_path: str, output_path: str, engine: str, language: Optional[str] = None, deskew: bool = False, optimize: int = 1):
    logger.info(f"Starting OCR task: {input_path} -> {output_path} using {engine} (lang: {language}, deskew: {deskew}, optimize: {optimize})")
    try:
        # Verify paths
        inp = Path(input_path)
        out = Path(output_path)
        if not inp.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
            
        # Run OCR
        ocr_service.run_ocr(inp, out, engine, task_language=language, deskew=deskew, optimize=optimize)
        logger.info("OCR task completed successfully")
        
        # Notify via WebSocket (fire and forget for now, needs async wrapper if using await)
        # Since this runs in a thread pool (BackgroundTasks), we can't easily await async methods 
        # on the main event loop directly without some care. 
        # For simplicity, we just log. Real implementation needs proper async integration.
        
    except Exception as e:
        logger.error(f"OCR task failed: {e}")

@app.post("/api/ocr")
async def start_ocr(request: OCRRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(
        run_ocr_task, 
        request.input_path, 
        request.output_path, 
        request.engine, 
        request.language,
        request.deskew,
        request.optimize
    )
    return {"status": "accepted", "message": "OCR task started"}

# --- Bookmark Service Integration ---
from src.services.bookmark_service import BookmarkService
bookmark_service = BookmarkService()

class BookmarkRequest(BaseModel):
    input_path: str
    output_path: str
    toc_text: str
    page_offset: int = 0

def run_bookmark_task(input_path: str, output_path: str, toc_text: str, page_offset: int):
    logger.info(f"Starting Bookmark task: {input_path} -> {output_path}")
    try:
        bookmark_service.add_bookmarks(input_path, output_path, toc_text, page_offset)
        logger.info("Bookmark task completed successfully")
    except Exception as e:
        logger.error(f"Bookmark task failed: {e}")

@app.post("/api/bookmarks/add")
async def add_bookmarks(request: BookmarkRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(
        run_bookmark_task,
        request.input_path,
        request.output_path,
        request.toc_text,
        request.page_offset
    )
    return {"status": "accepted", "message": "Bookmark task started"}

class BookmarkExtractRequest(BaseModel):
    input_path: str

@app.post("/api/bookmarks/extract")
def extract_bookmarks(request: BookmarkExtractRequest):
    try:
        toc_text = bookmark_service.extract_bookmarks(request.input_path)
        return {"status": "success", "toc_text": toc_text}
    except Exception as e:
        logger.error(f"Extract bookmarks failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- LLM Integration ---
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
        path = Path(request.input_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
            
        result = llm_service.call_vlm(path, request.start_page, request.end_page, request.config)
        return {"status": "success", "text": result}
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

@app.get("/")
def read_root():
    return {"status": "ok", "message": "PDF Toolbox Backend Running"}

@app.websocket("/ws/progress")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    # Use 8000 port to match frontend fetch calls
    uvicorn.run(app, host="127.0.0.1", port=8000)
