import uuid
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

class User(BaseModel):
    email: EmailStr
    groups: List[str] = []
    username: Optional[str] = None

class UserInDB(User):
    id: str
    username: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }

# --- Project Related Schemas ---
class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    meta_group_id: str = Field(..., min_length=1, max_length=255)

class ProjectCreate(ProjectBase):
    created_by_user_id: Optional[str] = None

class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    updated_by_user_id: Optional[str] = None

class Project(ProjectBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by_user_id: Optional[str] = None
    updated_by_user_id: Optional[str] = None

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }

# --- Project Metadata Schemas ---
class ProjectMetadataBase(BaseModel):
    key: str = Field(..., min_length=1, max_length=255)
    value: Optional[str] = None

class ProjectMetadataCreate(ProjectMetadataBase):
    project_id: uuid.UUID
    created_by_user_id: Optional[str] = None

class ProjectMetadataUpdate(BaseModel):
    value: Optional[str] = None
    updated_by_user_id: Optional[str] = None

class ProjectMetadata(ProjectMetadataBase):
    id: uuid.UUID
    project_id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by_user_id: Optional[str] = None
    updated_by_user_id: Optional[str] = None

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }

# --- Image Class Schemas ---
class ImageClassBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None

class ImageClassCreate(ImageClassBase):
    project_id: uuid.UUID
    created_by_user_id: Optional[str] = None

class ImageClassUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    updated_by_user_id: Optional[str] = None

class ImageClass(ImageClassBase):
    id: uuid.UUID
    project_id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by_user_id: Optional[str] = None
    updated_by_user_id: Optional[str] = None

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }

# --- Category Schemas ---
class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None

class CategoryCreate(CategoryBase):
    created_by_user_id: Optional[str] = None

class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None

class Category(CategoryBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by_user_id: Optional[str] = None

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }

# --- DataInstance Related Schemas ---
class DataInstanceBase(BaseModel):
    filename: str
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None

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

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }

# --- Image Metadata Schemas ---
class ImageMetadataBase(BaseModel):
    key: str = Field(..., min_length=1, max_length=255)
    value: Optional[str] = None

class ImageMetadataCreate(ImageMetadataBase):
    data_instance_id: uuid.UUID
    created_by_user_id: Optional[str] = None

class ImageMetadataUpdate(BaseModel):
    value: Optional[str] = None
    updated_by_user_id: Optional[str] = None

class ImageMetadata(ImageMetadataBase):
    id: uuid.UUID
    data_instance_id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by_user_id: Optional[str] = None
    updated_by_user_id: Optional[str] = None

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }

# --- Comment Schemas ---
class CommentBase(BaseModel):
    text: str

class CommentCreate(CommentBase):
    data_instance_id: uuid.UUID
    user_id: str

class CommentUpdate(BaseModel):
    text: Optional[str] = None

class Comment(CommentBase):
    id: uuid.UUID
    data_instance_id: uuid.UUID
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }

# --- Bounding Box Schemas ---
class BoundingBoxBase(BaseModel):
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    comment: Optional[str] = None

class BoundingBoxCreate(BoundingBoxBase):
    data_instance_id: uuid.UUID
    image_class_id: uuid.UUID
    created_by_user_id: Optional[str] = None

class BoundingBoxUpdate(BaseModel):
    x_min: Optional[float] = None
    y_min: Optional[float] = None
    x_max: Optional[float] = None
    y_max: Optional[float] = None
    comment: Optional[str] = None
    image_class_id: Optional[uuid.UUID] = None
    updated_by_user_id: Optional[str] = None

class BoundingBox(BoundingBoxBase):
    id: uuid.UUID
    data_instance_id: uuid.UUID
    image_class_id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by_user_id: Optional[str] = None
    updated_by_user_id: Optional[str] = None

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }

# --- DataInstance Category Link Schemas ---
class DataInstanceCategoryLinkBase(BaseModel):
    data_instance_id: uuid.UUID
    category_id: uuid.UUID

class DataInstanceCategoryLinkCreate(DataInstanceCategoryLinkBase):
    assigned_by_user_id: Optional[str] = None

class DataInstanceCategoryLink(DataInstanceCategoryLinkBase):
    assigned_at: datetime
    assigned_by_user_id: Optional[str] = None

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }

# --- Response Schemas ---
class PresignedUrlResponse(BaseModel):
    url: str
    object_key: str
    method: str = "GET"
