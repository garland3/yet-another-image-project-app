import os
import boto3
from botocore.exceptions import ClientError
from app.config import settings
from datetime import timedelta
import io

try:
    # Initialize boto3 client for S3
    S3_REGION = os.getenv("S3_REGION", "us-east-1")
    print(f"S3_ENDPOINT: {settings.S3_ENDPOINT}")
    print(f"S3_ACCESS_KEY: {settings.S3_ACCESS_KEY}")
    print(f"S3_SECRET_KEY: {settings.S3_SECRET_KEY}")
    print(f"S3_BUCKET: {settings.S3_BUCKET}")
    print(f"S3 REGION: {S3_REGION}")

    
    boto3_client = boto3.client(
        's3',
        endpoint_url=settings.S3_ENDPOINT,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=S3_REGION,
        # Use path-style URLs (required for MinIO)
        config=boto3.session.Config(signature_version='s3v4', s3={'addressing_style': 'path'})
    )
    # print("Boto3 S3 client initialized successfully")
except Exception as e:
    print(f"Error initializing Boto3 S3 client: {e}")
    boto3_client = None
    
    
# Test bucket access
try:
    boto3_client.head_bucket(Bucket=settings.S3_BUCKET)
    print("Successfully connected to S3!")
except Exception as e:
    print(f"Error connecting to S3: {e}")


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

# async def upload_file_to_minio(
#     bucket_name: str,
#     object_name: str,
#     file_data: io.BytesIO,
#     length: int,
#     content_type: str = "application/octet-stream"
# ) -> bool:
#     if not boto3_client:
#         print("Boto3 S3 client not initialized. Cannot upload.")
#         return False
#     try:
#         # Reset file pointer to beginning
#         file_data.seek(0)
        
#         # Upload file to S3
#         boto3_client.upload_fileobj(
#             file_data,
#             bucket_name,
#             object_name,
#             ExtraArgs={
#                 'ContentType': content_type
#             }
#         )
#         print(f"Successfully uploaded {object_name} to bucket {bucket_name}")
#         return True
#     except ClientError as e:
#         print(f"S3 Error during upload of {object_name}: {e}")
#         return False
#     except Exception as e:
#         print(f"An unexpected error occurred during upload of {object_name}: {e}")
#         return False

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
        
        # Try using put_object first (similar to your working implementation)
        try:
            boto3_client.put_object(
                Bucket=bucket_name,
                Key=object_name,
                Body=file_data.read(),
                ContentType=content_type
            )
            print(f"Successfully uploaded {object_name} to bucket {bucket_name} using put_object")
            return True
        except Exception as s3_error:
            print(f"put_object error: {str(s3_error)}")
            print("Falling back to upload_fileobj...")
            
            # Reset file pointer again for the fallback method
            file_data.seek(0)
            
            # Fall back to upload_fileobj
            boto3_client.upload_fileobj(
                file_data,
                bucket_name,
                object_name,
                ExtraArgs={
                    'ContentType': content_type
                }
            )
            print(f"Successfully uploaded {object_name} to bucket {bucket_name} using upload_fileobj")
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
