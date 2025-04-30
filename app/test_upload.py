import requests
import os

# URL of the API endpoint
url = "http://localhost:8000/projects/4a6579b7-ac4e-4301-beeb-68bd2ebadfc3/images"

# Path to the file to upload
file_path = "app/ui/static/css/styles.css"

# Check if the file exists
if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
    exit(1)

# Open the file in binary mode
with open(file_path, "rb") as file:
    # Create a dictionary with the file to upload
    files = {
        "file": (os.path.basename(file_path), file, "text/css")
    }
    
    # Add headers
    headers = {
        "accept": "application/json"
    }
    
    # Make the POST request
    print(f"Uploading file {file_path} to {url}...")
    response = requests.post(url, headers=headers, files=files)
    
    # Print the response status code and content
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.text}")
