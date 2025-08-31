import os
import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.routing import APIRouter
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pydantic import ValidationError

from core.config import settings
from core.database import create_db_and_tables
from core.migrations import run_migrations
from utils.boto3_client import boto3_client, ensure_bucket_exists
from middleware.cors_debug import add_cors_middleware, debug_exception_middleware
from middleware.auth import auth_middleware
from routers import projects, images, users, image_classes, comments, project_metadata, api_keys


"""
FastAPI application with modular structure.
Separates app creation from runtime configuration.
"""
from utils.boto3_client import boto3_client, ensure_bucket_exists
from middleware.cors_debug import add_cors_middleware, debug_exception_middleware
from routers import projects, images, users, image_classes, comments, project_metadata, api_keys


# Configure logging
def setup_logging():
    """Configure structured logging for the application."""
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    
    # JSON formatter for structured logging
    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_entry = {
                'timestamp': self.formatTime(record, self.datefmt),
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage(),
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno
            }
            if record.exc_info:
                log_entry['exception'] = self.formatException(record.exc_info)
            return json.dumps(log_entry)
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove default handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add our handler
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)
    
    return logging.getLogger(__name__)


# Initialize logger
logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Application startup...")
    if settings.FAST_TEST_MODE:
        logger.info("FAST_TEST_MODE enabled: skipping DB create/migrate and S3 bucket checks.")
    else:
        logger.info("Creating database tables if they don't exist...")
        await create_db_and_tables()
        logger.info("Database tables checked/created.")
        
        # Run migrations to set up new tables and migrate existing data
        await run_migrations()
        logger.info(f"Checking/Creating S3 bucket: {settings.S3_BUCKET}")
        if boto3_client:
            bucket_exists = ensure_bucket_exists(boto3_client, settings.S3_BUCKET)
            if not bucket_exists:
                logger.error(f"FATAL: Could not ensure S3 bucket '{settings.S3_BUCKET}' exists. Uploads/Downloads will fail.")
            else:
                logger.info(f"S3 bucket '{settings.S3_BUCKET}' is ready.")
        else:
            logger.warning("WARNING: Boto3 S3 client not initialized. Object storage operations will fail.")
    # Ensure a writable tmp dir exists for any runtime needs
    os.makedirs(os.path.join(os.getcwd(), "tmp"), exist_ok=True)
    logger.info("Application startup complete.")
    yield
    logger.info("Application shutdown...")
    logger.info("Application shutdown complete.")


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


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    App factory pattern for clean separation of concerns.
    """
    app = FastAPI(
        title=settings.APP_NAME,
        lifespan=lifespan
    )

    # Add CORS middleware
    cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    add_cors_middleware(app, cors_origins)
    
    # Add security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)

    # Add authentication middleware
    app.middleware("http")(auth_middleware)

    # Add debug middleware if in debug mode
    if settings.DEBUG:
        app.middleware("http")(debug_exception_middleware)

    # Global exception handler for Pydantic ValidationError
    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError):
        logger.error(f"ValidationError: {str(exc)}", extra={
            'error_details': exc.errors(),
            'request_path': request.url.path,
            'request_method': request.method
        })
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

    # Setup static file serving
    setup_static_files(app)
    
    return app


def setup_static_files(app: FastAPI):
    """Configure static file serving for the frontend."""
    # Get frontend build path from settings
    front_end_build_path = settings.FRONTEND_BUILD_PATH
    # Convert to absolute path if it's relative
    if not os.path.isabs(front_end_build_path):
        # Make it relative to the project root (parent of app directory)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        front_end_build_path = os.path.join(project_root, front_end_build_path)

    logger.info(f"Frontend build path: {front_end_build_path}")

    # Serve the static files from the build directory if it exists
    static_dir = os.path.join(front_end_build_path, "static")
    if os.path.isdir(static_dir):
        app.mount(
            "/static",
            StaticFiles(directory=static_dir),
            name="static_files"
        )
    else:
        logger.warning(f"Static directory not found at {static_dir}; skipping static mount")

    # Mount individual files using separate handlers
    @app.get("/favicon.ico")
    async def get_favicon():
        return FileResponse(os.path.join(front_end_build_path, "favicon.ico"))

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


# Create the app instance
app = create_app()
