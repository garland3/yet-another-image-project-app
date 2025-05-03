import uuid
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app import models, schemas
from typing import List, Optional, Dict, Any

# --- User CRUD Operations ---
async def get_user(db: AsyncSession, user_id: str) -> Optional[models.User]:
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    return result.scalars().first()

async def get_user_by_username(db: AsyncSession, username: str) -> Optional[models.User]:
    result = await db.execute(select(models.User).where(models.User.username == username))
    return result.scalars().first()

async def create_user(db: AsyncSession, user_id: str, username: str) -> models.User:
    db_user = models.User(id=user_id, username=username)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

# --- Project CRUD Operations ---
async def get_project(db: AsyncSession, project_id: uuid.UUID) -> Optional[models.Project]:
    result = await db.execute(
        select(models.Project)
        .options(
            selectinload(models.Project.data_instances),
            selectinload(models.Project.project_metadata),
            selectinload(models.Project.image_classes)
        )
        .where(models.Project.id == project_id)
    )
    return result.scalars().first()

async def get_projects_by_group_ids(db: AsyncSession, group_ids: List[str], skip: int = 0, limit: int = 100) -> List[models.Project]:
    if not group_ids:
        return []
    result = await db.execute(
        select(models.Project)
        .where(models.Project.meta_group_id.in_(group_ids))
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def create_project(db: AsyncSession, project: schemas.ProjectCreate) -> models.Project:
    db_project = models.Project(**project.model_dump())
    db.add(db_project)
    await db.commit()
    await db.refresh(db_project)
    return db_project

async def update_project(db: AsyncSession, project_id: uuid.UUID, project_update: schemas.ProjectUpdate) -> Optional[models.Project]:
    update_data = project_update.model_dump(exclude_unset=True)
    if not update_data:
        # No fields to update
        return await get_project(db, project_id)
    
    await db.execute(
        update(models.Project)
        .where(models.Project.id == project_id)
        .values(**update_data)
    )
    await db.commit()
    return await get_project(db, project_id)

# --- Project Metadata CRUD Operations ---
async def get_project_metadata(db: AsyncSession, metadata_id: uuid.UUID) -> Optional[models.ProjectMetadata]:
    result = await db.execute(select(models.ProjectMetadata).where(models.ProjectMetadata.id == metadata_id))
    return result.scalars().first()

async def get_project_metadata_by_key(db: AsyncSession, project_id: uuid.UUID, key: str) -> Optional[models.ProjectMetadata]:
    result = await db.execute(
        select(models.ProjectMetadata)
        .where(models.ProjectMetadata.project_id == project_id, models.ProjectMetadata.key == key)
    )
    return result.scalars().first()

async def get_project_metadata_all(db: AsyncSession, project_id: uuid.UUID) -> List[models.ProjectMetadata]:
    result = await db.execute(
        select(models.ProjectMetadata)
        .where(models.ProjectMetadata.project_id == project_id)
    )
    return result.scalars().all()

async def create_project_metadata(db: AsyncSession, metadata: schemas.ProjectMetadataCreate) -> models.ProjectMetadata:
    db_metadata = models.ProjectMetadata(**metadata.model_dump())
    db.add(db_metadata)
    await db.commit()
    await db.refresh(db_metadata)
    return db_metadata

async def update_project_metadata(db: AsyncSession, metadata_id: uuid.UUID, metadata_update: schemas.ProjectMetadataUpdate) -> Optional[models.ProjectMetadata]:
    update_data = metadata_update.model_dump(exclude_unset=True)
    if not update_data:
        # No fields to update
        return await get_project_metadata(db, metadata_id)
    
    await db.execute(
        update(models.ProjectMetadata)
        .where(models.ProjectMetadata.id == metadata_id)
        .values(**update_data)
    )
    await db.commit()
    return await get_project_metadata(db, metadata_id)

async def delete_project_metadata(db: AsyncSession, metadata_id: uuid.UUID) -> bool:
    result = await db.execute(
        delete(models.ProjectMetadata)
        .where(models.ProjectMetadata.id == metadata_id)
    )
    await db.commit()
    return result.rowcount > 0

# --- Image Class CRUD Operations ---
async def get_image_class(db: AsyncSession, class_id: uuid.UUID) -> Optional[models.ImageClass]:
    result = await db.execute(select(models.ImageClass).where(models.ImageClass.id == class_id))
    return result.scalars().first()

async def get_image_classes_for_project(db: AsyncSession, project_id: uuid.UUID) -> List[models.ImageClass]:
    result = await db.execute(
        select(models.ImageClass)
        .where(models.ImageClass.project_id == project_id)
    )
    return result.scalars().all()

async def create_image_class(db: AsyncSession, image_class: schemas.ImageClassCreate) -> models.ImageClass:
    db_class = models.ImageClass(**image_class.model_dump())
    db.add(db_class)
    await db.commit()
    await db.refresh(db_class)
    return db_class

async def update_image_class(db: AsyncSession, class_id: uuid.UUID, class_update: schemas.ImageClassUpdate) -> Optional[models.ImageClass]:
    update_data = class_update.model_dump(exclude_unset=True)
    if not update_data:
        # No fields to update
        return await get_image_class(db, class_id)
    
    await db.execute(
        update(models.ImageClass)
        .where(models.ImageClass.id == class_id)
        .values(**update_data)
    )
    await db.commit()
    return await get_image_class(db, class_id)

async def delete_image_class(db: AsyncSession, class_id: uuid.UUID) -> bool:
    result = await db.execute(
        delete(models.ImageClass)
        .where(models.ImageClass.id == class_id)
    )
    await db.commit()
    return result.rowcount > 0

# --- Category CRUD Operations ---
async def get_category(db: AsyncSession, category_id: uuid.UUID) -> Optional[models.Category]:
    result = await db.execute(select(models.Category).where(models.Category.id == category_id))
    return result.scalars().first()

async def get_category_by_name(db: AsyncSession, name: str) -> Optional[models.Category]:
    result = await db.execute(select(models.Category).where(models.Category.name == name))
    return result.scalars().first()

async def get_all_categories(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[models.Category]:
    result = await db.execute(
        select(models.Category)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def create_category(db: AsyncSession, category: schemas.CategoryCreate) -> models.Category:
    db_category = models.Category(**category.model_dump())
    db.add(db_category)
    await db.commit()
    await db.refresh(db_category)
    return db_category

async def update_category(db: AsyncSession, category_id: uuid.UUID, category_update: schemas.CategoryUpdate) -> Optional[models.Category]:
    update_data = category_update.model_dump(exclude_unset=True)
    if not update_data:
        # No fields to update
        return await get_category(db, category_id)
    
    await db.execute(
        update(models.Category)
        .where(models.Category.id == category_id)
        .values(**update_data)
    )
    await db.commit()
    return await get_category(db, category_id)

async def delete_category(db: AsyncSession, category_id: uuid.UUID) -> bool:
    result = await db.execute(
        delete(models.Category)
        .where(models.Category.id == category_id)
    )
    await db.commit()
    return result.rowcount > 0

# --- DataInstance CRUD Operations ---
async def get_data_instance(db: AsyncSession, image_id: uuid.UUID) -> Optional[models.DataInstance]:
    result = await db.execute(
        select(models.DataInstance)
        .options(
            selectinload(models.DataInstance.project),
            selectinload(models.DataInstance.image_metadata),
            selectinload(models.DataInstance.comments),
            selectinload(models.DataInstance.bounding_boxes),
            selectinload(models.DataInstance.categories)
        )
        .where(models.DataInstance.id == image_id)
    )
    return result.scalars().first()

async def get_data_instances_for_project(db: AsyncSession, project_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[models.DataInstance]:
    # First check if the project exists
    project = await get_project(db, project_id)
    if not project:
        return []
        
    result = await db.execute(
        select(models.DataInstance)
        .where(models.DataInstance.project_id == project_id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def create_data_instance(db: AsyncSession, data_instance: schemas.DataInstanceCreate) -> models.DataInstance:
    db_data_instance = models.DataInstance(**data_instance.model_dump())
    db.add(db_data_instance)
    await db.commit()
    await db.refresh(db_data_instance)
    return db_data_instance

# --- Image Metadata CRUD Operations ---
async def get_image_metadata(db: AsyncSession, metadata_id: uuid.UUID) -> Optional[models.ImageMetadata]:
    result = await db.execute(select(models.ImageMetadata).where(models.ImageMetadata.id == metadata_id))
    return result.scalars().first()

async def get_image_metadata_by_key(db: AsyncSession, data_instance_id: uuid.UUID, key: str) -> Optional[models.ImageMetadata]:
    result = await db.execute(
        select(models.ImageMetadata)
        .where(models.ImageMetadata.data_instance_id == data_instance_id, models.ImageMetadata.key == key)
    )
    return result.scalars().first()

async def get_image_metadata_all(db: AsyncSession, data_instance_id: uuid.UUID) -> List[models.ImageMetadata]:
    result = await db.execute(
        select(models.ImageMetadata)
        .where(models.ImageMetadata.data_instance_id == data_instance_id)
    )
    return result.scalars().all()

async def create_image_metadata(db: AsyncSession, metadata: schemas.ImageMetadataCreate) -> models.ImageMetadata:
    db_metadata = models.ImageMetadata(**metadata.model_dump())
    db.add(db_metadata)
    await db.commit()
    await db.refresh(db_metadata)
    return db_metadata

async def update_image_metadata(db: AsyncSession, metadata_id: uuid.UUID, metadata_update: schemas.ImageMetadataUpdate) -> Optional[models.ImageMetadata]:
    update_data = metadata_update.model_dump(exclude_unset=True)
    if not update_data:
        # No fields to update
        return await get_image_metadata(db, metadata_id)
    
    await db.execute(
        update(models.ImageMetadata)
        .where(models.ImageMetadata.id == metadata_id)
        .values(**update_data)
    )
    await db.commit()
    return await get_image_metadata(db, metadata_id)

async def delete_image_metadata(db: AsyncSession, metadata_id: uuid.UUID) -> bool:
    result = await db.execute(
        delete(models.ImageMetadata)
        .where(models.ImageMetadata.id == metadata_id)
    )
    await db.commit()
    return result.rowcount > 0

# --- Comment CRUD Operations ---
async def get_comment(db: AsyncSession, comment_id: uuid.UUID) -> Optional[models.Comment]:
    result = await db.execute(select(models.Comment).where(models.Comment.id == comment_id))
    return result.scalars().first()

async def get_comments_for_data_instance(db: AsyncSession, data_instance_id: uuid.UUID) -> List[models.Comment]:
    result = await db.execute(
        select(models.Comment)
        .where(models.Comment.data_instance_id == data_instance_id)
        .order_by(models.Comment.created_at)
    )
    return result.scalars().all()

async def create_comment(db: AsyncSession, comment: schemas.CommentCreate) -> models.Comment:
    db_comment = models.Comment(**comment.model_dump())
    db.add(db_comment)
    await db.commit()
    await db.refresh(db_comment)
    return db_comment

async def update_comment(db: AsyncSession, comment_id: uuid.UUID, comment_update: schemas.CommentUpdate) -> Optional[models.Comment]:
    update_data = comment_update.model_dump(exclude_unset=True)
    if not update_data:
        # No fields to update
        return await get_comment(db, comment_id)
    
    await db.execute(
        update(models.Comment)
        .where(models.Comment.id == comment_id)
        .values(**update_data)
    )
    await db.commit()
    return await get_comment(db, comment_id)

async def delete_comment(db: AsyncSession, comment_id: uuid.UUID) -> bool:
    result = await db.execute(
        delete(models.Comment)
        .where(models.Comment.id == comment_id)
    )
    await db.commit()
    return result.rowcount > 0

# --- Bounding Box CRUD Operations ---
async def get_bounding_box(db: AsyncSession, box_id: uuid.UUID) -> Optional[models.BoundingBox]:
    result = await db.execute(
        select(models.BoundingBox)
        .options(selectinload(models.BoundingBox.image_class))
        .where(models.BoundingBox.id == box_id)
    )
    return result.scalars().first()

async def get_bounding_boxes_for_data_instance(db: AsyncSession, data_instance_id: uuid.UUID) -> List[models.BoundingBox]:
    result = await db.execute(
        select(models.BoundingBox)
        .options(selectinload(models.BoundingBox.image_class))
        .where(models.BoundingBox.data_instance_id == data_instance_id)
    )
    return result.scalars().all()

async def create_bounding_box(db: AsyncSession, box: schemas.BoundingBoxCreate) -> models.BoundingBox:
    db_box = models.BoundingBox(**box.model_dump())
    db.add(db_box)
    await db.commit()
    await db.refresh(db_box)
    return db_box

async def update_bounding_box(db: AsyncSession, box_id: uuid.UUID, box_update: schemas.BoundingBoxUpdate) -> Optional[models.BoundingBox]:
    update_data = box_update.model_dump(exclude_unset=True)
    if not update_data:
        # No fields to update
        return await get_bounding_box(db, box_id)
    
    await db.execute(
        update(models.BoundingBox)
        .where(models.BoundingBox.id == box_id)
        .values(**update_data)
    )
    await db.commit()
    return await get_bounding_box(db, box_id)

async def delete_bounding_box(db: AsyncSession, box_id: uuid.UUID) -> bool:
    result = await db.execute(
        delete(models.BoundingBox)
        .where(models.BoundingBox.id == box_id)
    )
    await db.commit()
    return result.rowcount > 0

# --- DataInstance Category Link CRUD Operations ---
async def get_categories_for_data_instance(db: AsyncSession, data_instance_id: uuid.UUID) -> List[models.Category]:
    result = await db.execute(
        select(models.Category)
        .join(models.DataInstanceCategoryLink)
        .where(models.DataInstanceCategoryLink.data_instance_id == data_instance_id)
    )
    return result.scalars().all()

async def get_data_instances_for_category(db: AsyncSession, category_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[models.DataInstance]:
    result = await db.execute(
        select(models.DataInstance)
        .join(models.DataInstanceCategoryLink)
        .where(models.DataInstanceCategoryLink.category_id == category_id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def link_data_instance_to_category(db: AsyncSession, link: schemas.DataInstanceCategoryLinkCreate) -> models.DataInstanceCategoryLink:
    db_link = models.DataInstanceCategoryLink(**link.model_dump())
    db.add(db_link)
    await db.commit()
    return db_link

async def unlink_data_instance_from_category(db: AsyncSession, data_instance_id: uuid.UUID, category_id: uuid.UUID) -> bool:
    result = await db.execute(
        delete(models.DataInstanceCategoryLink)
        .where(
            models.DataInstanceCategoryLink.data_instance_id == data_instance_id,
            models.DataInstanceCategoryLink.category_id == category_id
        )
    )
    await db.commit()
    return result.rowcount > 0
