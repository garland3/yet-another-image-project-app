from fastapi.responses import RedirectResponse
# import app router. 
from fastapi.routing import APIRouter

from fastapi.middleware.cors import CORSMiddleware
import logging
import time
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import os
from pathlib import Path
from contextlib import asynccontextmanager
from pydantic import ValidationError
import traceback
import json
from config import settings
from database import create_db_and_tables
from boto3_client import boto3_client, ensure_bucket_exists
from migrations import run_migrations
from routers import projects, images, users, image_classes, comments, project_metadata, api_keys


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application startup...")
    print("Creating database tables if they don't exist...")
    await create_db_and_tables()
    print("Database tables checked/created.")
    
    # Run migrations to set up new tables and migrate existing data
    await run_migrations()
    print(f"Checking/Creating S3 bucket: {settings.S3_BUCKET}")
    if boto3_client:
         bucket_exists = ensure_bucket_exists(boto3_client, settings.S3_BUCKET)
         if not bucket_exists:
             print(f"FATAL: Could not ensure S3 bucket '{settings.S3_BUCKET}' exists. Uploads/Downloads will fail.")
         else:
            print(f"S3 bucket '{settings.S3_BUCKET}' is ready.")
    else:
        print("WARNING: Boto3 S3 client not initialized. Object storage operations will fail.")
    # Ensure a writable tmp dir exists for any runtime needs
    os.makedirs(os.path.join(os.getcwd(), "tmp"), exist_ok=True)
    # if frontend/build exist, then copy the contents of frontend/build to /ui2
    # if os.path.exists("/app/frontend/build"):
        # Copy the contents of frontend/build to /ui2
        # os.system("cp -r /app/frontend/build /ui2/")
        # print("Frontend build copied to /ui2")
    # else:
        # print("Frontend build not found, serving empty ui directory")
    print("Application startup complete.")
    yield
    print("Application shutdown...")
    print("Application shutdown complete.")



app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan
)



# Add CORS middleware
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cors_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.DEBUG:
    # Add debug middleware to catch exceptions and print debug information
    @app.middleware("http")
    async def debug_exception_middleware(request: Request, call_next):
        start_time = time.time()
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            print(f"Request: {request.method} {request.url.path} completed in {process_time:.4f}s")
            return response
        except Exception as e:
            process_time = time.time() - start_time
            print(f"ERROR in {request.method} {request.url.path} after {process_time:.4f}s: {type(e).__name__}: {str(e)}")
            # Avoid dumping headers/body in non-dev logs
            if settings.DEBUG:
                print(f"Traceback: {traceback.format_exc()}")
            raise  # Re-raise the exception for FastAPI to handle

# Add middleware that prints the request type and path to the console
# Custom JSON encoder to handle MetaData objects
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, "__class__") and obj.__class__.__name__ == "MetaData":
            return {}
        return super().default(obj)

# Custom JSONResponse that uses our encoder
class CustomJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            cls=CustomJSONEncoder,
        ).encode("utf-8")

# Global exception handler for Pydantic ValidationError
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    # print he trace back to and as much informaion tot he console. 
    print(f"ValidationError: {str(exc)}")
    print(f"Error details: {exc.errors()}")
    print(f"Traceback: {traceback.format_exc()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )





# Create an API router 
api_router = APIRouter()

# Include all API routers under the /api prefix
api_router.include_router(projects.router)
api_router.include_router(images.router)
api_router.include_router(users.router)
api_router.include_router(image_classes.router)
api_router.include_router(comments.router)
api_router.include_router(project_metadata.router)
api_router.include_router(api_keys.router)

# Include the API router in the main app
app.include_router(api_router)

# for other routes, check the frontend build folder for html, js, css
# Set up static files serving

# Get frontend build path from settings
front_end_build_path = settings.FRONTEND_BUILD_PATH
# Convert to absolute path if it's relative
if not os.path.isabs(front_end_build_path):
    # Make it relative to the project root (parent of app directory)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    front_end_build_path = os.path.join(project_root, front_end_build_path)

print(f"Frontend build path: {front_end_build_path}")

# Serve the static files from the build directory if it exists
static_dir = os.path.join(front_end_build_path, "static")
if os.path.isdir(static_dir):
    app.mount(
        "/static",
        StaticFiles(directory=static_dir),
        name="static_files"
    )
else:
    print(f"Static directory not found at {static_dir}; skipping static mount")

# import fileresponse. 
from fastapi.responses import FileResponse
# Mount individual files using separate handlers
@app.get("/favicon.ico")
async def get_favicon():
    return FileResponse(os.path.join(front_end_build_path, "favicon.ico"))

# 3 route for logo192.png
@app.get("/logo192.png")
async def get_logo192():
    return FileResponse(os.path.join(front_end_build_path, "logo192.png"))

@app.get("/manifest.json")
async def get_manifest():
    return FileResponse(os.path.join(front_end_build_path, "manifest.json"))

@app.get("/")
async def get_index():
    return FileResponse(os.path.join(front_end_build_path, "index.html"))

# Catch-all route for React Router - this must be last
@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    """
    Catch-all route to serve the React app for any path that doesn't match
    an API route or static file. This enables React Router to handle client-side routing.
    """
    # Don't handle API routes through this catch-all
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    
    # Serve the React app's index.html for all other routes
    return FileResponse(os.path.join(front_end_build_path, "index.html"))
