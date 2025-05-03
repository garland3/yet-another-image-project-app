from minio import Minio
from minio.error import S3Error
from app.config import settings
from datetime import timedelta
import io

try:
    minio_client = Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_USE_SSL,
    )
except Exception as e:
    print(f"Error initializing MinIO client: {e}")
    minio_client = None

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
            return True
    except S3Error as e:
        print(f"Error checking or creating bucket '{bucket_name}': {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred with MinIO bucket operations: {e}")
        return False

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
