import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app import crud, schemas, models
from app.database import get_db
from app.dependencies import get_current_user
from app.config import settings
from app.routers.image_classes import check_image_access

router = APIRouter(
    tags=["Comments"],
)

@router.post("/images/{image_id}/comments", response_model=schemas.ImageComment, status_code=status.HTTP_201_CREATED)
async def create_comment(
    image_id: uuid.UUID,
    comment: schemas.ImageCommentBase,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    print(f"Comment request received for image_id: {image_id}")
    print(f"Comment text: {comment.text}")
    print(f"Current user: {current_user}")
    
    # Check if the user has access to the image
    await check_image_access(image_id, db, current_user)
    
    # Set up the comment create object
    comment_create = schemas.ImageCommentCreate(
        image_id=image_id,
        text=comment.text,
        # author_id is now optional in the schema
    )
    
    print(f"Created comment object: {comment_create}")
    
    # Set the author_id based on the current user
    if current_user.id:
        comment_create.author_id = current_user.id
    else:
        db_user = await crud.get_user_by_email(db=db, email=current_user.email)
        if not db_user:
            # Create a new user
            user_create = schemas.UserCreate(
                email=current_user.email,
                groups=current_user.groups,
            )
            db_user = await crud.create_user(db=db, user=user_create)
        
        comment_create.author_id = db_user.id
    
    # Create the comment
    return await crud.create_comment(db=db, comment=comment_create)

@router.get("/images/{image_id}/comments", response_model=List[schemas.ImageComment])
async def list_comments(
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # Check if the user has access to the image
    await check_image_access(image_id, db, current_user)
    
    # Get all comments for the image
    return await crud.get_comments_for_image(db=db, image_id=image_id)

@router.get("/comments/{comment_id}", response_model=schemas.ImageComment)
async def get_comment(
    comment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # Get the comment
    db_comment = await crud.get_comment(db=db, comment_id=comment_id)
    if db_comment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    
    # Check if the user has access to the image
    await check_image_access(db_comment.image_id, db, current_user)
    
    return db_comment

@router.patch("/comments/{comment_id}", response_model=schemas.ImageComment)
async def update_comment(
    comment_id: uuid.UUID,
    comment_data: schemas.ImageCommentBase,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # Get the comment
    db_comment = await crud.get_comment(db=db, comment_id=comment_id)
    if db_comment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    
    # Check if the user has access to the image
    await check_image_access(db_comment.image_id, db, current_user)
    
    # Only allow the author of the comment or admin users to update it
    if (current_user.id and str(db_comment.author_id) != str(current_user.id)) and "admin" not in current_user.groups:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this comment",
        )
    
    # Update the comment
    updated_comment = await crud.update_comment(
        db=db, 
        comment_id=comment_id, 
        comment_data=comment_data.model_dump(exclude_unset=True)
    )
    
    return updated_comment

@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # Get the comment
    db_comment = await crud.get_comment(db=db, comment_id=comment_id)
    if db_comment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    
    # Check if the user has access to the image
    await check_image_access(db_comment.image_id, db, current_user)
    
    # Only allow the author of the comment or admin users to delete it
    if (current_user.id and str(db_comment.author_id) != str(current_user.id)) and "admin" not in current_user.groups:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this comment",
        )
    
    # Delete the comment
    success = await crud.delete_comment(db=db, comment_id=comment_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete comment",
        )
    
    return None
