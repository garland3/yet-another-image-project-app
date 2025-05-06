from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from pydantic import ValidationError
import traceback
import json
from app.config import settings
from app.database import create_db_and_tables
from app.minio_client import minio_client, ensure_bucket_exists
from app.migrations import run_migrations
from app.routers import projects, images, users, image_classes, comments, project_metadata
from app.routers import ui

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application startup...")
    print("Creating database tables if they don't exist...")
    await create_db_and_tables()
    print("Database tables checked/created.")
    
    # Run migrations to set up new tables and migrate existing data
    await run_migrations()
    print(f"Checking/Creating MinIO bucket: {settings.MINIO_BUCKET_NAME}")
    if minio_client:
         bucket_exists = ensure_bucket_exists(minio_client, settings.MINIO_BUCKET_NAME)
         if not bucket_exists:
             print(f"FATAL: Could not ensure MinIO bucket '{settings.MINIO_BUCKET_NAME}' exists. Uploads/Downloads will fail.")
         else:
            print(f"MinIO bucket '{settings.MINIO_BUCKET_NAME}' is ready.")
    else:
        print("WARNING: MinIO client not initialized. Object storage operations will fail.")
    print("Application startup complete.")
    yield
    print("Application shutdown...")
    print("Application shutdown complete.")

app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan
)

from fastapi.middleware.cors import CORSMiddleware
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.middleware("http")
async def log_request(request, call_next):
    print(f"Request: {request.method} {request.url}")
    try:
        response = await call_next(request)
        return response
    except ValidationError as e:
        # Log the detailed error
        print(f"Pydantic ValidationError: {str(e)}")
        print(f"Error details: {e.errors()}")
        print(f"Traceback: {traceback.format_exc()}")
        
        # Return a more informative error response
        return CustomJSONResponse(
            status_code=422,
            content={
                "detail": "Validation Error",
                "errors": e.errors(),
                "message": str(e)
            }
        )
    except Exception as e:
        # Log other exceptions
        print(f"Unhandled exception: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise


# Mount static files for UI
app.mount("/ui/static", StaticFiles(directory="app/ui/static"), name="ui-static")

app.include_router(projects.router)
app.include_router(images.router)
app.include_router(users.router)
app.include_router(image_classes.router)
app.include_router(comments.router)
app.include_router(project_metadata.router)
app.include_router(ui.router)

from fastapi.responses import RedirectResponse

@app.get("/", tags=["Root"])
async def read_root():
    return RedirectResponse(url="/ui")
