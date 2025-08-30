"""
Serialization utilities for converting database models to API schemas.
Centralizes metadata serialization logic to avoid repetition.
"""

from typing import Any, Dict
from core import schemas, models


def to_data_instance_schema(db_image: models.DataInstance) -> schemas.DataInstance:
    """
    Convert a database DataInstance model to a Pydantic schema.
    Handles metadata serialization consistently.
    
    Args:
        db_image: The database model instance
        
    Returns:
        Pydantic schema instance with properly serialized metadata
    """
    # Convert metadata_ to dict format expected by the schema
    metadata_dict = {}
    if db_image.metadata_:
        # If it's already a dict, use it directly
        if isinstance(db_image.metadata_, dict):
            metadata_dict = db_image.metadata_
        # If it's a string, try to parse it as JSON
        elif isinstance(db_image.metadata_, str):
            try:
                import json
                metadata_dict = json.loads(db_image.metadata_)
            except (json.JSONDecodeError, TypeError):
                metadata_dict = {}
        # If it's some other type with attributes, convert to dict
        elif hasattr(db_image.metadata_, '__dict__'):
            metadata_dict = {k: v for k, v in db_image.metadata_.__dict__.items() 
                           if not k.startswith('_')}
    
    return schemas.DataInstance(
        id=db_image.id,
        filename=db_image.filename,
        file_path=db_image.file_path,
        project_id=db_image.project_id,
        metadata_=metadata_dict,
        thumbnail_path=db_image.thumbnail_path,
        created_at=db_image.created_at,
        updated_at=db_image.updated_at
    )


def normalize_metadata_dict(metadata_: Any) -> Dict[str, Any]:
    """
    Normalize metadata from various formats to a dictionary.
    
    Args:
        metadata_: The metadata in various possible formats
        
    Returns:
        A dictionary representation of the metadata
    """
    if metadata_ is None:
        return {}
    
    if isinstance(metadata_, dict):
        return metadata_
    
    if isinstance(metadata_, str):
        try:
            import json
            return json.loads(metadata_)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    if hasattr(metadata_, '__dict__'):
        return {k: v for k, v in metadata_.__dict__.items() 
               if not k.startswith('_')}
    
    # Fallback: try to convert to dict
    try:
        return dict(metadata_)
    except (TypeError, ValueError):
        return {}
