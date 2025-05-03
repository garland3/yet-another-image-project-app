import uuid
from sqlalchemy import (
    Column, String, Text, ForeignKey, DateTime, JSON, BigInteger,
    Integer, Float, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base # Assuming 'app.database.Base' is your declarative base

# --- User Table (Needed for tracking creators/editors) ---
class User(Base):
    __tablename__ = "users"

    # Assuming you use a string ID elsewhere, but UUID is generally better if starting fresh.
    # Using String here to match 'uploaded_by_user_id' and 'meta_group_id' style.
    id = Column(String(255), primary_key=True, index=True)
    username = Column(String(255), nullable=False, unique=True)
    # Add other relevant user fields like email, hashed_password, full_name, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships to track creations/updates (optional but good practice)
    created_projects = relationship("Project", foreign_keys="[Project.created_by_user_id]", back_populates="creator")
    updated_projects = relationship("Project", foreign_keys="[Project.updated_by_user_id]", back_populates="updater")
    uploaded_data_instances = relationship("DataInstance", back_populates="uploader")
    # Add relationships for other created/updated items if needed

# --- Project Table (Modified) ---
class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    meta_group_id = Column(String(255), nullable=False, index=True) # Consider if this is still needed or relates to User/Group

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by_user_id = Column(String(255), ForeignKey("users.id"), nullable=True) # Who created it
    updated_by_user_id = Column(String(255), ForeignKey("users.id"), nullable=True) # Who last updated it

    # Relationships
    creator = relationship("User", foreign_keys=[created_by_user_id], back_populates="created_projects")
    updater = relationship("User", foreign_keys=[updated_by_user_id], back_populates="updated_projects")
    data_instances = relationship("DataInstance", back_populates="project", cascade="all, delete-orphan") # Renamed from 'images' for clarity
    project_metadata = relationship("ProjectMetadata", back_populates="project", cascade="all, delete-orphan")
    image_classes = relationship("ImageClass", back_populates="project", cascade="all, delete-orphan")

# --- Project Metadata Table ---
class ProjectMetadata(Base):
    __tablename__ = "project_metadata"
    __table_args__ = (UniqueConstraint('project_id', 'key', name='uq_project_metadata_key'),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    key = Column(String(255), nullable=False)
    value = Column(Text, nullable=True) # Use Text for flexibility, or JSON if values are complex

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by_user_id = Column(String(255), ForeignKey("users.id"), nullable=True)
    updated_by_user_id = Column(String(255), ForeignKey("users.id"), nullable=True)

    # Relationships
    project = relationship("Project", back_populates="project_metadata")
    creator = relationship("User", foreign_keys=[created_by_user_id]) # Simplified relationship if detailed back-pop not needed
    updater = relationship("User", foreign_keys=[updated_by_user_id])

# --- DataInstance Table (Modified Image Table) ---
class DataInstance(Base):
    __tablename__ = "data_instances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    object_storage_key = Column(String(1024), nullable=False, unique=True)
    content_type = Column(String(100), nullable=True)
    size_bytes = Column(BigInteger, nullable=True)
    # metadata_ = Column("metadata", JSON, nullable=True) # REMOVED - Replaced by structured metadata table
    uploaded_by_user_id = Column(String(255), ForeignKey("users.id"), nullable=False) # Now an FK

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    # No updated_by_user_id here unless the file blob itself can be updated

    # Relationships
    project = relationship("Project", back_populates="data_instances")
    uploader = relationship("User", back_populates="uploaded_data_instances")
    image_metadata = relationship("ImageMetadata", back_populates="data_instance", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="data_instance", cascade="all, delete-orphan")
    bounding_boxes = relationship("BoundingBox", back_populates="data_instance", cascade="all, delete-orphan")
    # Many-to-Many relationship for Categories
    categories = relationship("Category", secondary="data_instance_category_link", back_populates="data_instances")


# --- Image Metadata Table ---
class ImageMetadata(Base):
    __tablename__ = "image_metadata"
    __table_args__ = (UniqueConstraint('data_instance_id', 'key', name='uq_image_metadata_key'),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    data_instance_id = Column(UUID(as_uuid=True), ForeignKey("data_instances.id"), nullable=False, index=True)
    key = Column(String(255), nullable=False)
    value = Column(Text, nullable=True) # Use Text for flexibility, or JSON if values are complex

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by_user_id = Column(String(255), ForeignKey("users.id"), nullable=True)
    updated_by_user_id = Column(String(255), ForeignKey("users.id"), nullable=True)

    # Relationships
    data_instance = relationship("DataInstance", back_populates="image_metadata")
    creator = relationship("User", foreign_keys=[created_by_user_id])
    updater = relationship("User", foreign_keys=[updated_by_user_id])


# --- Comment Table ---
class Comment(Base):
    __tablename__ = "comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    data_instance_id = Column(UUID(as_uuid=True), ForeignKey("data_instances.id"), nullable=False, index=True)
    user_id = Column(String(255), ForeignKey("users.id"), nullable=False) # Who made the comment
    text = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now()) # Allow comment edits

    # Relationships
    data_instance = relationship("DataInstance", back_populates="comments")
    commenter = relationship("User", foreign_keys=[user_id]) # Can add back_populates="comments" to User if needed


# --- Image Class Table ---
class ImageClass(Base):
    __tablename__ = "image_classes"
    __table_args__ = (UniqueConstraint('project_id', 'name', name='uq_project_image_class_name'),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    # Optional: add color, hotkey etc. for UI
    # color = Column(String(7), nullable=True) # e.g., '#FF0000'

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by_user_id = Column(String(255), ForeignKey("users.id"), nullable=True)
    updated_by_user_id = Column(String(255), ForeignKey("users.id"), nullable=True)

    # Relationships
    project = relationship("Project", back_populates="image_classes")
    creator = relationship("User", foreign_keys=[created_by_user_id])
    updater = relationship("User", foreign_keys=[updated_by_user_id])
    bounding_boxes = relationship("BoundingBox", back_populates="image_class") # All boxes with this class


# --- Bounding Box Table ---
class BoundingBox(Base):
    __tablename__ = "bounding_boxes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    data_instance_id = Column(UUID(as_uuid=True), ForeignKey("data_instances.id"), nullable=False, index=True)
    image_class_id = Column(UUID(as_uuid=True), ForeignKey("image_classes.id"), nullable=False) # Class assigned to this box

    # Coordinates - Use Float for flexibility (e.g., relative coords 0.0-1.0) or Integer for pixels
    x_min = Column(Float, nullable=False)
    y_min = Column(Float, nullable=False)
    x_max = Column(Float, nullable=False)
    y_max = Column(Float, nullable=False)

    comment = Column(Text, nullable=True) # Optional comment specific to this box

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by_user_id = Column(String(255), ForeignKey("users.id"), nullable=True)
    updated_by_user_id = Column(String(255), ForeignKey("users.id"), nullable=True)

    # Relationships
    data_instance = relationship("DataInstance", back_populates="bounding_boxes")
    image_class = relationship("ImageClass", back_populates="bounding_boxes")
    creator = relationship("User", foreign_keys=[created_by_user_id])
    updater = relationship("User", foreign_keys=[updated_by_user_id])

# --- Category Table ---
class Category(Base):
    __tablename__ = "categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True) # Assuming global categories for now
    description = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by_user_id = Column(String(255), ForeignKey("users.id"), nullable=True)
    # updated_by_user_id might not be needed if categories are fairly static

    # Relationships
    creator = relationship("User", foreign_keys=[created_by_user_id])
    # Many-to-Many relationship for DataInstances
    data_instances = relationship("DataInstance", secondary="data_instance_category_link", back_populates="categories")

# --- Association Table for DataInstance <-> Category (Many-to-Many) ---
class DataInstanceCategoryLink(Base):
    __tablename__ = "data_instance_category_link"

    data_instance_id = Column(UUID(as_uuid=True), ForeignKey("data_instances.id"), primary_key=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), primary_key=True)

    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    assigned_by_user_id = Column(String(255), ForeignKey("users.id"), nullable=True)

    # Relationships (optional, for accessing assignment metadata)
    assigner = relationship("User", foreign_keys=[assigned_by_user_id])
    # data_instance = relationship("DataInstance") # Can access via DataInstance.categories
    # category = relationship("Category")       # Can access via Category.data_instances
