Okay, let's set up a minimal FastAPI application with PostgreSQL for metadata and MinIO for image storage, using Docker Compose. We'll include the requested mocking for authentication and group membership checks.

**Project Structure:**

```
.
├── app/
│   ├── __init__.py
│   ├── main.py         # FastAPI app setup and root endpoint
│   ├── config.py       # Pydantic settings management
│   ├── database.py     # Database connection and session
│   ├── models.py       # SQLAlchemy ORM models
│   ├── schemas.py      # Pydantic schemas for API validation
│   ├── crud.py         # Database interaction functions
│   ├── dependencies.py # Auth and authorization dependencies
│   ├── minio_client.py # MinIO connection and functions
│   └── routers/
│       ├── __init__.py
│       ├── projects.py   # Project related routes
│       └── images.py     # Image related routes
├── .env              # Environment variables
├── Dockerfile        # Docker build instructions for the app
├── docker-compose.yml # Docker Compose configuration
└── requirements.txt  # Python dependencies
```

**1. `requirements.txt`**

```txt
fastapi[all]
uvicorn[standard]
sqlalchemy[asyncio]>=2.0 # Use SQLAlchemy 2.0+ for better async
asyncpg # Async driver for postgresql
psycopg2-binary # Required by alembic sometimes, good to have
alembic # For database migrations (good practice, though not strictly used in this minimal example)
python-dotenv
pydantic-settings # For loading .env into Pydantic models
minio # MinIO Python client
python-multipart # For file uploads in FastAPI
uuid
```

**2. `.env` (Create this file)**

```env
# --- Application Settings ---
APP_NAME="Data Management API"
SKIP_HEADER_CHECK=True # Set to False or remove to enable real auth (when implemented)
MOCK_USER_EMAIL="test@example.com"
MOCK_USER_GROUPS='["admin-group", "data-scientists", "project-alpha-group"]' # JSON list of groups the mock user belongs to

# --- PostgreSQL Settings ---
POSTGRES_USER=admin
POSTGRES_PASSWORD=supersecretpassword
POSTGRES_DB=datamgmt
POSTGRES_SERVER=db # Service name in docker-compose
POSTGRES_PORT=5432
DATABASE_URL=postgresql+asyncpg://admin:supersecretpassword@db:5432/datamgmt

# --- MinIO Settings ---
MINIO_ENDPOINT=minio:9000 # Service name and port in docker-compose
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadminpassword
MINIO_BUCKET_NAME=data-storage
MINIO_USE_SSL=False # Set to True if MinIO is configured with TLS/SSL
```

**3. `app/config.py`**

```python
import json
from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    APP_NAME: str = "Data Management API"
    SKIP_HEADER_CHECK: bool = False
    MOCK_USER_EMAIL: str = "test@example.com"
    MOCK_USER_GROUPS_JSON: str = '[]' # Renamed to load as JSON string first

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str # SQLAlchemy connection string

    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET_NAME: str = "data-storage"
    MINIO_USE_SSL: bool = False

    # Computed property for mock groups
    @property
    def MOCK_USER_GROUPS(self) -> List[str]:
        try:
            return json.loads(self.MOCK_USER_GROUPS_JSON)
        except json.JSONDecodeError:
            print(f"Warning: Could not parse MOCK_USER_GROUPS_JSON: {self.MOCK_USER_GROUPS_JSON}")
            return []

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        # If using Pydantic v2:
        # case_sensitive = True

settings = Settings()
```

**4. `app/database.py`**

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# Create the async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True, # Log SQL queries (optional, good for debugging)
    future=True # Use modern SQLAlchemy features
)

# Create a configured "Session" class
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False, # Important for async background tasks
    autocommit=False,
    autoflush=False,
)

# Base class for ORM models
Base = declarative_base()

# Dependency to get DB session in routes
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

# Function to create tables (call this at startup)
# NOTE: In production, use Alembic migrations instead
async def create_db_and_tables():
     async with engine.begin() as conn:
         # await conn.run_sync(Base.metadata.drop_all) # Use cautiously during dev
         await conn.run_sync(Base.metadata.create_all)

```

**5. `app/models.py`**

```python
import uuid
from sqlalchemy import Column, String, Text, ForeignKey, DateTime, JSON, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    meta_group_id = Column(String(255), nullable=False, index=True) # Identifier for the meta-group
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship (optional but useful)
    images = relationship("DataInstance", back_populates="project", cascade="all, delete-orphan")

class DataInstance(Base):
    __tablename__ = "data_instances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    object_storage_key = Column(String(1024), nullable=False, unique=True) # Key in MinIO
    content_type = Column(String(100), nullable=True)
    size_bytes = Column(BigInteger, nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True) # Arbitrary JSON metadata, renamed to avoid keyword clash
    uploaded_by_user_id = Column(String(255), nullable=False) # e.g., user email or ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship
    project = relationship("Project", back_populates="images")

```

**6. `app/schemas.py`**

```python
import uuid
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# --- User (for dependency) ---
class User(BaseModel):
    email: EmailStr
    groups: List[str] = [] # List of meta-groups the user belongs to

# --- Project Schemas ---
class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    meta_group_id: str = Field(..., min_length=1, max_length=255)

class ProjectCreate(ProjectBase):
    pass

class Project(ProjectBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True # Pydantic v2
        # orm_mode = True # Pydantic v1

# --- Data Instance (Image) Schemas ---
class DataInstanceBase(BaseModel):
    filename: str
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None
    metadata_: Optional[Dict[str, Any]] = Field(None, alias="metadata") # Use alias for input/output

class DataInstanceCreate(DataInstanceBase):
    project_id: uuid.UUID
    object_storage_key: str
    uploaded_by_user_id: str

class DataInstance(DataInstanceBase):
    id: uuid.UUID
    project_id: uuid.UUID
    object_storage_key: str
    uploaded_by_user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True # Pydantic v2
        # orm_mode = True # Pydantic v1

class PresignedUrlResponse(BaseModel):
    url: str
    object_key: str
    method: str = "GET"
```

**7. `app/minio_client.py`**

```python
from minio import Minio
from minio.error import S3Error
from app.config import settings
from datetime import timedelta
import io

# Initialize MinIO client
try:
    minio_client = Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_USE_SSL,
    )
except Exception as e:
    print(f"Error initializing MinIO client: {e}")
    minio_client = None # Handle gracefully if connection fails at startup

# Function to ensure bucket exists
def ensure_bucket_exists(client: Minio, bucket_name: str):
    if not client:
        print("Minio client not initialized.")
        return False
    try:
        found = client.bucket_exists(bucket_name)
        if not found:
            client.make_bucket(bucket_name)
            print(f"Bucket '{bucket_name}' created.")
            return True
        else:
            # print(f"Bucket '{bucket_name}' already exists.")
            return True
    except S3Error as e:
        print(f"Error checking or creating bucket '{bucket_name}': {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred with MinIO bucket operations: {e}")
        return False


# Upload function
async def upload_file_to_minio(
    bucket_name: str,
    object_name: str,
    file_data: io.BytesIO,
    length: int,
    content_type: str = "application/octet-stream"
) -> bool:
    if not minio_client:
        print("Minio client not initialized. Cannot upload.")
        return False
    try:
        minio_client.put_object(
            bucket_name,
            object_name,
            data=file_data,
            length=length,
            content_type=content_type
        )
        print(f"Successfully uploaded {object_name} to bucket {bucket_name}")
        return True
    except S3Error as e:
        print(f"MinIO Error during upload of {object_name}: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during upload of {object_name}: {e}")
        return False

# Get presigned URL function
def get_presigned_download_url(bucket_name: str, object_name: str, expires_delta: timedelta = timedelta(hours=1)) -> str | None:
    if not minio_client:
        print("Minio client not initialized. Cannot generate URL.")
        return None
    try:
        url = minio_client.presigned_get_object(
            bucket_name,
            object_name,
            expires=expires_delta,
        )
        return url
    except S3Error as e:
        print(f"MinIO Error generating presigned URL for {object_name}: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred generating presigned URL for {object_name}: {e}")
        return None

```

**8. `app/dependencies.py`**

```python
from fastapi import Depends, HTTPException, status, Header, Request
from typing import Optional, List
from app.config import settings
from app.schemas import User

# Mock Group Membership Check (as requested)
def check_mock_user_in_group(user: User, group_id: str) -> bool:
    """
    Checks if the MOCK user is in the specified group based on .env settings.
    """
    # print(f"Checking if mock user '{user.email}' is in group '{group_id}'")
    # print(f"Mock user groups: {user.groups}")
    return group_id in user.groups

# Dependency to get the current user (mocked)
async def get_current_user(
    request: Request, # Use request to potentially access headers later
    x_user_id: Optional[str] = Header(None), # Example header, not used if mocked
    x_user_groups: Optional[str] = Header(None) # Example header, not used if mocked
) -> User:
    """
    Dependency to get the current user.
    If SKIP_HEADER_CHECK is True, returns a mock user.
    Otherwise, raises 401 (future real implementation would go here).
    """
    if settings.SKIP_HEADER_CHECK:
        # print("Auth check skipped. Using mock user.")
        return User(email=settings.MOCK_USER_EMAIL, groups=settings.MOCK_USER_GROUPS)
    else:
        # --- Placeholder for Real Authentication ---
        # Here you would:
        # 1. Check for authentication headers (e.g., Authorization: Bearer <token>)
        # 2. Validate the token (e.g., JWT verification, OAuth introspection)
        # 3. Fetch user details (ID, email) from the token or a user service
        # 4. Fetch user's meta-group memberships from your external group API
        # 5. Return a User object or raise HTTPException
        # Example using placeholder headers:
        # if not x_user_id:
        #     raise HTTPException(
        #         status_code=status.HTTP_401_UNAUTHORIZED,
        #         detail="Not authenticated: Missing user ID header",
        #     )
        # # Call your group API here based on x_user_id
        # user_groups = fetch_groups_for_user(x_user_id) # Replace with actual call
        # return User(email=x_user_id, groups=user_groups) # Assuming email is the ID for now
        # --- End Placeholder ---

        # For now, if mocking is disabled, deny access
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required (mocking disabled)",
        )

# Dependency for checking if user is in a specific group (uses mock if enabled)
async def requires_group_membership(
    required_group_id: str,
    current_user: User = Depends(get_current_user)
) -> bool:
    """
    Dependency that checks if the current user is a member of the required group.
    Uses mock check if SKIP_HEADER_CHECK is True.
    Raises 403 Forbidden if the user is not in the group.
    """
    is_member = False
    if settings.SKIP_HEADER_CHECK:
        is_member = check_mock_user_in_group(current_user, required_group_id)
    else:
        # --- Placeholder for Real Group Check ---
        # In a real scenario, get_current_user would already populate
        # the user.groups based on the external API call.
        is_member = required_group_id in current_user.groups
        # --- End Placeholder ---

    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User '{current_user.email}' does not have access to group '{required_group_id}'",
        )
    return True # Indicate success (though not strictly necessary as exception handles failure)
```

**9. `app/crud.py`**

```python
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app import models, schemas
from typing import List, Optional

# === Project CRUD ===

async def get_project(db: AsyncSession, project_id: uuid.UUID) -> Optional[models.Project]:
    result = await db.execute(select(models.Project).where(models.Project.id == project_id))
    return result.scalars().first()

async def get_projects_by_group_ids(db: AsyncSession, group_ids: List[str], skip: int = 0, limit: int = 100) -> List[models.Project]:
    if not group_ids:
        return [] # No groups, no projects visible
    result = await db.execute(
        select(models.Project)
        .where(models.Project.meta_group_id.in_(group_ids))
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def create_project(db: AsyncSession, project: schemas.ProjectCreate) -> models.Project:
    db_project = models.Project(**project.model_dump()) # Pydantic v2
    # db_project = models.Project(**project.dict()) # Pydantic v1
    db.add(db_project)
    await db.commit()
    await db.refresh(db_project)
    return db_project

# === Data Instance (Image) CRUD ===

async def get_data_instance(db: AsyncSession, image_id: uuid.UUID) -> Optional[models.DataInstance]:
    result = await db.execute(
        select(models.DataInstance)
        .options(selectinload(models.DataInstance.project)) # Eager load project for auth check
        .where(models.DataInstance.id == image_id)
        )
    return result.scalars().first()

async def get_data_instances_for_project(db: AsyncSession, project_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[models.DataInstance]:
    result = await db.execute(
        select(models.DataInstance)
        .where(models.DataInstance.project_id == project_id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def create_data_instance(db: AsyncSession, data_instance: schemas.DataInstanceCreate) -> models.DataInstance:
    # Handle potential alias for 'metadata_'
    create_data = data_instance.model_dump() # Pydantic v2
    # create_data = data_instance.dict() # Pydantic v1
    if "metadata" in create_data:
         create_data["metadata_"] = create_data.pop("metadata")

    db_data_instance = models.DataInstance(**create_data)
    db.add(db_data_instance)
    await db.commit()
    await db.refresh(db_data_instance)
    return db_data_instance
```

**10. `app/routers/projects.py`**

```python
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app import crud, schemas, models
from app.database import get_db
from app.dependencies import get_current_user, requires_group_membership, check_mock_user_in_group
from app.config import settings


router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
)

@router.post("/", response_model=schemas.Project, status_code=status.HTTP_201_CREATED)
async def create_new_project(
    project: schemas.ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """
    Creates a new project. User must be a member of the specified meta-group.
    """
    # Authorization: Check if user is in the meta-group they are assigning the project to
    is_member = False
    if settings.SKIP_HEADER_CHECK:
        is_member = check_mock_user_in_group(current_user, project.meta_group_id)
    else:
        # Real check would use current_user.groups populated during authentication
        is_member = project.meta_group_id in current_user.groups

    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User '{current_user.email}' cannot create projects in group '{project.meta_group_id}'",
        )

    db_project = await crud.create_project(db=db, project=project)
    return db_project

@router.get("/", response_model=List[schemas.Project])
async def read_projects(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """
    Retrieves a list of projects accessible by the current user based on their group memberships.
    """
    # No specific group check needed here, filtering is based on user's groups
    projects = await crud.get_projects_by_group_ids(db=db, group_ids=current_user.groups, skip=skip, limit=limit)
    return projects

@router.get("/{project_id}", response_model=schemas.Project)
async def read_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user), # Get user first
):
    """
    Retrieves details for a specific project. User must be in the project's meta-group.
    """
    db_project = await crud.get_project(db=db, project_id=project_id)
    if db_project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Authorization: Check if user is in the project's group AFTER fetching the project
    is_member = False
    if settings.SKIP_HEADER_CHECK:
        is_member = check_mock_user_in_group(current_user, db_project.meta_group_id)
    else:
        is_member = db_project.meta_group_id in current_user.groups

    if not is_member:
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User '{current_user.email}' does not have access to project '{project_id}' (group '{db_project.meta_group_id}')",
        )

    return db_project

```

**11. `app/routers/images.py`**

```python
import uuid
import io
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from app import crud, schemas, models
from app.database import get_db
from app.dependencies import get_current_user, check_mock_user_in_group
from app.minio_client import upload_file_to_minio, get_presigned_download_url
from app.config import settings
import json


router = APIRouter(
    tags=["Images"], # Group routes under Images tag
)

async def check_project_access(project_id: uuid.UUID, db: AsyncSession, current_user: schemas.User) -> models.Project:
    """Helper dependency to get project and verify user access"""
    db_project = await crud.get_project(db=db, project_id=project_id)
    if db_project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Authorization check
    is_member = False
    if settings.SKIP_HEADER_CHECK:
        is_member = check_mock_user_in_group(current_user, db_project.meta_group_id)
    else:
        is_member = db_project.meta_group_id in current_user.groups

    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User '{current_user.email}' does not have access to project '{project_id}' (group '{db_project.meta_group_id}')",
        )
    return db_project


@router.post("/projects/{project_id}/images", response_model=schemas.DataInstance, status_code=status.HTTP_201_CREATED)
async def upload_image_to_project(
    project_id: uuid.UUID,
    file: UploadFile = File(...),
    metadata_json: Optional[str] = Form(None, alias="metadata"), # Receive metadata as JSON string
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """
    Uploads an image (or any file) to a specific project.
    User must be a member of the project's meta-group.
    Optional metadata can be provided as a JSON string in the 'metadata' form field.
    """
    # Verify access to the project
    db_project = await check_project_access(project_id, db, current_user)

    # Generate unique identifiers
    image_id = uuid.uuid4()
    # Use a structured key: project_id / image_id / original_filename
    object_storage_key = f"{db_project.id}/{image_id}/{file.filename}"

    # Parse metadata if provided
    parsed_metadata: Optional[Dict[str, Any]] = None
    if metadata_json:
        try:
            parsed_metadata = json.loads(metadata_json)
        except json.JSONDecodeError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON format for metadata")

    # Read file content into memory (for MinIO upload)
    # For very large files, consider streaming approaches if possible with the client
    contents = await file.read()
    file_data = io.BytesIO(contents)
    file_size = len(contents)

    # Upload to MinIO
    success = await upload_file_to_minio(
        bucket_name=settings.MINIO_BUCKET_NAME,
        object_name=object_storage_key,
        file_data=file_data,
        length=file_size,
        content_type=file.content_type
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to upload file to object storage")

    # Create database record
    data_instance_create = schemas.DataInstanceCreate(
        project_id=db_project.id,
        filename=file.filename,
        object_storage_key=object_storage_key,
        content_type=file.content_type,
        size_bytes=file_size,
        metadata=parsed_metadata, # Pass parsed dict here
        uploaded_by_user_id=current_user.email,
    )

    # Note: Use model_dump() with alias handling in crud if needed
    db_data_instance = await crud.create_data_instance(db=db, data_instance=data_instance_create)

    # Manually set metadata for the response model if alias was used
    response_data = schemas.DataInstance.model_validate(db_data_instance) # Pydantic v2
    # response_data = schemas.DataInstance.from_orm(db_data_instance) # Pydantic v1
    if "metadata_" in db_data_instance.__dict__:
         response_data.metadata_ = db_data_instance.metadata_

    return response_data


@router.get("/projects/{project_id}/images", response_model=List[schemas.DataInstance])
async def list_images_in_project(
    project_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """
    Lists images (data instances) within a specific project.
    User must be a member of the project's meta-group.
    """
    # Verify access to the project (implicitly checks if project exists)
    await check_project_access(project_id, db, current_user)

    images = await crud.get_data_instances_for_project(db=db, project_id=project_id, skip=skip, limit=limit)

    # Convert to response schema, handling metadata alias if needed
    response_images = []
    for img in images:
        img_schema = schemas.DataInstance.model_validate(img) # Pydantic v2
        # img_schema = schemas.DataInstance.from_orm(img) # Pydantic v1
        if "metadata_" in img.__dict__:
            img_schema.metadata_ = img.metadata_
        response_images.append(img_schema)

    return response_images

@router.get("/images/{image_id}", response_model=schemas.DataInstance)
async def get_image_metadata(
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """
    Gets the metadata for a specific image (data instance).
    User must be a member of the meta-group associated with the image's project.
    """
    db_image = await crud.get_data_instance(db=db, image_id=image_id)
    if db_image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    # Authorization check via the loaded project's group
    is_member = False
    if settings.SKIP_HEADER_CHECK:
        is_member = check_mock_user_in_group(current_user, db_image.project.meta_group_id)
    else:
        is_member = db_image.project.meta_group_id in current_user.groups

    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User '{current_user.email}' does not have access to image '{image_id}'",
        )

    # Convert to response schema, handling metadata alias if needed
    response_data = schemas.DataInstance.model_validate(db_image) # Pydantic v2
    # response_data = schemas.DataInstance.from_orm(db_image) # Pydantic v1
    if "metadata_" in db_image.__dict__:
         response_data.metadata_ = db_image.metadata_

    return response_data


@router.get("/images/{image_id}/download", response_model=schemas.PresignedUrlResponse)
async def get_image_download_url(
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """
    Gets a temporary, pre-signed URL to download the actual image file from MinIO.
    User must be a member of the meta-group associated with the image's project.
    """
    db_image = await crud.get_data_instance(db=db, image_id=image_id)
    if db_image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    # Authorization check via the loaded project's group
    is_member = False
    if settings.SKIP_HEADER_CHECK:
        is_member = check_mock_user_in_group(current_user, db_image.project.meta_group_id)
    else:
        is_member = db_image.project.meta_group_id in current_user.groups

    if not is_member:
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User '{current_user.email}' does not have access to image '{image_id}'",
        )

    # Generate pre-signed URL from MinIO
    download_url = get_presigned_download_url(
        bucket_name=settings.MINIO_BUCKET_NAME,
        object_name=db_image.object_storage_key
    )

    if not download_url:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not generate download URL")

    return schemas.PresignedUrlResponse(url=download_url, object_key=db_image.object_storage_key)

```

**12. `app/main.py`**

```python
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.config import settings
from app.database import create_db_and_tables
from app.minio_client import minio_client, ensure_bucket_exists
from app.routers import projects, images

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    print("Application startup...")
    # Ensure database tables are created (use Alembic in production)
    print("Creating database tables if they don't exist...")
    await create_db_and_tables()
    print("Database tables checked/created.")

    # Ensure MinIO bucket exists
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
    # --- Shutdown ---
    print("Application shutdown...")
    # Cleanup resources here if needed (e.g., close database engine explicitly)
    # await engine.dispose() # If necessary
    print("Application shutdown complete.")


app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan
)

# Include routers
app.include_router(projects.router)
app.include_router(images.router) # Include image routes


@app.get("/", tags=["Root"])
async def read_root():
    """Root endpoint providing basic API info."""
    return {"message": f"Welcome to the {settings.APP_NAME}", "docs": "/docs"}

# Optional: Add __init__.py files in app/ and app/routers/ if needed for imports,
# though they are often optional in newer Python versions.
# Create empty `app/__init__.py` and `app/routers/__init__.py`
```

**13. `Dockerfile`**

```dockerfile
# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Prevent Python from writing pyc files to disc (optional)
ENV PYTHONDONTWRITEBYTECODE 1
# Ensure Python output is sent straight to terminal (useful for logs)
ENV PYTHONUNBUFFERED 1

# Install system dependencies that might be needed by some Python packages
# (e.g., psycopg2 needs libpq-dev, build-essential for C extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY ./app /app/app
COPY .env /app/.env # Copy .env file (alternative: use docker-compose env_file)

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application using Uvicorn
# Use --reload for development only
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
# For production, use:
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**14. `docker-compose.yml`**

```yaml
version: '3.8'

services:
  db:
    image: postgres:15 # Use a specific version
    container_name: postgres_db
    volumes:
      - postgres_data:/var/lib/postgresql/data/
    env_file:
      - .env # Load DB credentials from .env
    ports:
      - "5433:5432" # Expose PG on host port 5433 to avoid conflicts
    networks:
      - data_mgmt_net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    restart: unless-stopped

  minio:
    image: minio/minio:latest
    container_name: minio_storage
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000" # API port
      - "9090:9090" # Console port
    env_file:
      - .env # Load MinIO credentials from .env
    environment:
      # These need to be explicitly set for MinIO service itself
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}
    command: server /data --console-address ":9090"
    networks:
      - data_mgmt_net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    restart: unless-stopped

  app:
    build: . # Build the image from the Dockerfile in the current directory
    container_name: fastapi_app
    env_file:
      - .env # Load all settings from .env
    ports:
      - "8000:8000"
    volumes:
      - ./app:/app/app # Mount local app directory for development hot-reloading
    networks:
      - data_mgmt_net
    depends_on:
      db:
        condition: service_healthy # Wait for DB to be ready
      minio:
        condition: service_healthy # Wait for MinIO to be ready
    restart: unless-stopped

networks:
  data_mgmt_net:
    driver: bridge

volumes:
  postgres_data:
  minio_data:

```

**How to Run:**

1.  **Save:** Create all the files and directories as described above.
2.  **Install Docker:** Make sure you have Docker and Docker Compose installed.
3.  **Build & Run:** Open a terminal in the project's root directory (where `docker-compose.yml` is located) and run:
    ```bash
    docker-compose up --build
    ```
    The `--build` flag ensures the FastAPI app image is built (or rebuilt if code changes).
4.  **Access:**
    * **API Docs:** Open your web browser to `http://localhost:8000/docs`. You should see the Swagger UI for your API.
    * **MinIO Console:** Open `http://localhost:9090`. Log in using the `MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY` from your `.env` file. You should see the `data-storage` bucket created automatically.
    * **Database (Optional):** You can connect to the PostgreSQL database using a tool like DBeaver or `psql` on host port `5433` (as mapped in `docker-compose.yml`) using the credentials from `.env`.

**Explanation:**

1.  **FastAPI App (`app/`):** Contains the core logic, API routes, database models, schemas, dependencies, and configuration.
2.  **Mocking (`.env` & `dependencies.py`):**
    * `SKIP_HEADER_CHECK=True` in `.env` enables mocking.
    * `MOCK_USER_EMAIL` and `MOCK_USER_GROUPS` define the mock user's details.
    * `get_current_user` dependency checks `SKIP_HEADER_CHECK` and returns the mock user if true.
    * `check_mock_user_in_group` simulates checking if the mock user belongs to a specific group based on `MOCK_USER_GROUPS`.
    * Authorization checks in the routers use these mock functions when mocking is enabled.
3.  **Database (`database.py`, `models.py`, `crud.py`):** Uses SQLAlchemy's async capabilities with `asyncpg` to interact with PostgreSQL. Defines models (`Project`, `DataInstance`) and CRUD functions.
4.  **Object Storage (`minio_client.py`):** Initializes the MinIO client and provides functions for uploading files and generating pre-signed download URLs. The bucket is created automatically on startup.
5.  **Docker (`Dockerfile`, `docker-compose.yml`):**
    * `Dockerfile` defines how to build the Python application image.
    * `docker-compose.yml` defines the three services (`app`, `db`, `minio`), sets up networking, volumes for data persistence, environment variables, health checks, and dependencies between services.
6.  **API Endpoints (`routers/`):**
    * `/projects`: Create and list projects (listing is filtered by the mock user's groups). Get project details (requires user to be in the project's group).
    * `/projects/{project_id}/images`: Upload images to a project (requires user to be in the project's group). List images in a project.
    * `/images/{image_id}`: Get image metadata (requires user access to the parent project's group).
    * `/images/{image_id}/download`: Get a pre-signed URL for direct download from MinIO (requires user access).

This setup provides a minimal but functional starting point for your data management system, including the requested mocking features.