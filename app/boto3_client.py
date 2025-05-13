import boto3
from botocore.exceptions import ClientError
from app.config import settings
from datetime import timedelta
import io

try:
    # Initialize boto3 client for S3
    boto3_client = boto3.client(
        's3',
        endpoint_url=f"http://{settings.S3_ENDPOINT}",
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        # Use path-style URLs (required for MinIO)
        config=boto3.session.Config(signature_version='s3v4', s3={'addressing_style': 'path'})
    )
    print("Boto3 S3 client initialized successfully")
except Exception as e:
    print(f"Error initializing Boto3 S3 client: {e}")
    boto3_client = None

def ensure_bucket_exists(client, bucket_name: str):
    if not client:
        print("Boto3 S3 client not initialized.")
        return False
    try:
        # Check if bucket exists
        client.head_bucket(Bucket=bucket_name)
        return True
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')
        if error_code == '404':
            # Bucket doesn't exist, create it
            try:
                client.create_bucket(Bucket=bucket_name)
                print(f"Bucket '{bucket_name}' created.")
                return True
            except ClientError as create_error:
                print(f"Error creating bucket '{bucket_name}': {create_error}")
                return False
        else:
            print(f"Error checking bucket '{bucket_name}': {e}")
            return False
    except Exception as e:
        print(f"An unexpected error occurred with S3 bucket operations: {e}")
        return False

async def upload_file_to_minio(
    bucket_name: str,
    object_name: str,
    file_data: io.BytesIO,
    length: int,
    content_type: str = "application/octet-stream"
) -> bool:
    if not boto3_client:
        print("Boto3 S3 client not initialized. Cannot upload.")
        return False
    try:
        # Reset file pointer to beginning
        file_data.seek(0)
        
        # Upload file to S3
        boto3_client.upload_fileobj(
            file_data,
            bucket_name,
            object_name,
            ExtraArgs={
                'ContentType': content_type
            }
        )
        print(f"Successfully uploaded {object_name} to bucket {bucket_name}")
        return True
    except ClientError as e:
        print(f"S3 Error during upload of {object_name}: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during upload of {object_name}: {e}")
        return False

def get_presigned_download_url(bucket_name: str, object_name: str, expires_delta: timedelta = timedelta(hours=1)) -> str | None:
    if not boto3_client:
        print("Boto3 S3 client not initialized. Cannot generate URL.")
        return None
    try:
        # Generate presigned URL
        url = boto3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': object_name
            },
            ExpiresIn=int(expires_delta.total_seconds())
        )
        return url
    except ClientError as e:
        print(f"S3 Error generating presigned URL for {object_name}: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred generating presigned URL for {object_name}: {e}")
        return None
