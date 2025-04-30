from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os

router = APIRouter()

# # Path to the UI directory
UI_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui")

# Mount the static folder
router.mount("/ui/static", StaticFiles(directory=os.path.join(UI_DIR, "static")), name="static")

# Serve index.html for the root UI route
@router.get("/ui")
async def serve_ui():
    return FileResponse(os.path.join(UI_DIR, "index.html"))

# Serve other HTML files
@router.get("/ui/{page}")
async def serve_page(page: str):
    return FileResponse(os.path.join(UI_DIR, f"{page}.html"))# Mount the static folder
