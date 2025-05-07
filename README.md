# Image Management System

A web-based system for managing images, projects, and annotations.

## Features

### Core Features
- Project management
- Image upload and storage
- Image viewing and navigation
- Image metadata

### New Features
1. **Image Classification**
   - Define custom classes per project (e.g., 'defect', 'ok', 'unsure')
   - Classify images with one or more classes
   - View and manage classifications

2. **Image Comments**
   - Add comments to images
   - View, edit, and delete comments
   - Comments are associated with users

3. **Project Metadata**
   - Add key-value metadata to projects
   - Support for simple values and complex JSON objects
   - Bulk update project metadata

4. **User Management**
   - User accounts with email and groups
   - User authentication and authorization
   - User-based permissions for comments and classifications

## Architecture

### Backend
- FastAPI for the REST API
- SQLAlchemy for database ORM
- PostgreSQL for data storage
- MinIO for object storage (images)

### Frontend
- Vanilla JavaScript
- HTML/CSS
- Responsive design

## Database Schema

### Core Tables
- `projects`: Stores project information
- `data_instances`: Stores image information and metadata

### New Tables
- `users`: Stores user information
- `image_classes`: Stores class definitions for projects
- `image_classifications`: Stores image classifications
- `image_comments`: Stores comments on images
- `project_metadata`: Stores project metadata

## API Endpoints

### Project Endpoints
- `GET /projects`: List all projects
- `POST /projects`: Create a new project
- `GET /projects/{project_id}`: Get project details

### Image Endpoints
- `POST /projects/{project_id}/images`: Upload an image to a project
- `GET /projects/{project_id}/images`: List all images in a project
- `GET /images/{image_id}`: Get image metadata
- `GET /images/{image_id}/download`: Get image download URL
- `GET /images/{image_id}/content`: Get image content

### User Endpoints
- `POST /users`: Create a new user
- `GET /users/me`: Get current user information
- `GET /users/{user_id}`: Get user information
- `PATCH /users/{user_id}`: Update user information

### Image Class Endpoints
- `POST /projects/{project_id}/classes`: Create a new image class
- `GET /projects/{project_id}/classes`: List all image classes for a project
- `GET /classes/{class_id}`: Get image class details
- `PATCH /classes/{class_id}`: Update image class
- `DELETE /classes/{class_id}`: Delete image class

### Image Classification Endpoints
- `POST /images/{image_id}/classifications`: Classify an image
- `GET /images/{image_id}/classifications`: List all classifications for an image
- `DELETE /classifications/{classification_id}`: Delete classification

### Comment Endpoints
- `POST /images/{image_id}/comments`: Add a comment to an image
- `GET /images/{image_id}/comments`: List all comments for an image
- `GET /comments/{comment_id}`: Get comment details
- `PATCH /comments/{comment_id}`: Update comment
- `DELETE /comments/{comment_id}`: Delete comment

### Project Metadata Endpoints
- `POST /projects/{project_id}/metadata`: Add metadata to a project
- `GET /projects/{project_id}/metadata`: List all metadata for a project
- `GET /projects/{project_id}/metadata/{key}`: Get metadata value
- `PUT /projects/{project_id}/metadata/{key}`: Update metadata value
- `DELETE /projects/{project_id}/metadata/{key}`: Delete metadata
- `GET /projects/{project_id}/metadata-dict`: Get all metadata as a dictionary
- `PUT /projects/{project_id}/metadata-dict`: Update all metadata from a dictionary

## UI Pages

### Project List Page
- List all projects
- Create new projects

### Project Page
- View project details
- Upload images
- Manage project metadata
- Define image classes
- View all images in the project

### Image View Page
- View image details
- Navigate between images
- View and add classifications
- View and add comments
- View image metadata

## Getting Started

### Prerequisites
- Docker and Docker Compose
- Python 3.11+
- Node.js 20+

### Installation with Docker
1. Clone the repository
2. Copy `.env.example` to `.env` and update the values
3. Run `docker-compose up -d`
   - This will build a Docker container using Ubuntu as the base image
   - Python 3.11 and uv package installer will be set up in a virtual environment
   - The frontend will be built and served from the same uvicorn app
4. Access the application at `http://localhost:8000`

### Development Setup
1. Make sure you have Python 3.11+ installed (or the script will attempt to install it)
2. Run the start script: `./start.sh`
   - This will:
     - Check for Python 3.11 and install it if needed (requires sudo)
     - Create a Python virtual environment
     - Install uv package installer
     - Install dependencies using uv
     - Build the frontend if needed
     - Start the application with hot reloading
3. Access the application at `http://localhost:8000`

### Manual Development Setup
If you prefer to set up manually:

1. Create a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install uv package installer:
   ```bash
   pip install uv
   ```

3. Install dependencies using uv:
   ```bash
   uv pip install -r requirements.txt
   ```

4. Build the frontend:
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   mkdir -p app/ui/static
   cp -r frontend/build/* app/ui/
   ```

5. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

6. Access the application at `http://localhost:8000`

## License
This project is licensed under the MIT License - see the LICENSE file for details.
