from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from typing import Optional
import os
import uuid
from pathlib import Path
from datetime import datetime

from app.models.schemas import VideoSignRequest, SigningResponse, ErrorResponse
from app.core.config import settings
from app.services.c2pa_service import c2pa_service

router = APIRouter()

def get_file_size_mb(file_path: str) -> float:
    """Get file size in megabytes"""
    return os.path.getsize(file_path) / (1024 * 1024)

@router.post(
    "/sign-video",
    response_model=SigningResponse,
    summary="Sign video with C2PA credentials",
    description="Upload a video file and sign it with C2PA content credentials",
    responses={
        200: {
            "description": "Video signed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "message": "C2PA signing succeeded in embedded mode.",
                        "job_id": "550e8400-e29b-41d4-a716-446655440000",
                        "links": {
                            "download_url": "http://localhost:8000/files/video-signed-20231113.mp4",
                            "manifest_url": "http://localhost:8000/files/video-signed-20231113.manifest.json",
                            "mode": "embedded"
                        },
                        "metadata": {
                            "original_filename": "my_video.mp4",
                            "file_size_mb": 25.5,
                            "signed_at": "2023-11-13T10:30:00Z"
                        }
                    }
                }
            }
        },
        400: {"description": "Invalid request - bad file type or size"},
        500: {"description": "Server error during signing"}
    }
)
async def sign_video(
    video: UploadFile = File(
        ..., 
        description="Video file to sign (MP4, MOV, M4V formats supported)"
    ),
    organization: str = Form(
        ..., 
        description="Organization name (e.g., 'Test Organization')",
        example="Test Org"
    ),
    ai_tool: str = Form(
        ..., 
        description="AI tool/model used to generate the video",
        example="Veo 3"
    ),
    title: Optional[str] = Form(
        None, 
        description="Video title (optional)",
        example="AI Generated Landscape"
    ),
    description: Optional[str] = Form(
        None, 
        description="Video description (optional)",
        example="Beautiful AI-generated mountain landscape"
    )
):
    """
    ## Sign a video file with C2PA content credentials
    
    This endpoint accepts a video file along with metadata and returns a signed video
    that can be verified on Adobe's Content Authenticity website.
    
    ### Parameters:
    - **video**: The video file (MP4, MOV, or M4V)
    - **organization**: Name of your organization
    - **ai_tool**: Name of the AI model/tool used
    - **title**: Optional title for the video
    - **description**: Optional description
    
    ### Returns:
    - **download_url**: URL to download the signed video
    - **manifest_url**: URL to download the manifest JSON
    - **metadata**: Information about the signing operation
    
    ### Example Usage:
```bash
    curl -X POST "http://localhost:8000/api/v1/sign-video" \\
      -F "video=@my_video.mp4" \\
      -F "organization=Test Org" \\
      -F "ai_tool=Veo 3" \\
      -F "title=My AI Video" \\
      -F "description=A beautiful AI-generated video"
```
    
    ### Verification:
    After downloading the signed video, verify it at:
    https://verify.contentauthenticity.org
    """
    
    # Validate file type
    allowed_extensions = ['.mp4', '.mov', '.m4v']
    file_ext = Path(video.filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file_ext}'. Allowed types: {', '.join(allowed_extensions)}"
        )
    
    # Generate unique job ID and filenames
    job_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    base_filename = f"video-signed-{timestamp}-{job_id[:8]}"
    
    # File paths
    input_path = os.path.join(settings.UPLOAD_DIR, f"temp_{job_id}{file_ext}")
    output_path = os.path.join(settings.UPLOAD_DIR, f"{base_filename}{file_ext}")
    output_manifest_path = os.path.join(settings.UPLOAD_DIR, f"{base_filename}.manifest.json")
    manifest_path = None
    
    try:
        # Save uploaded file
        print(f"📤 Uploading video: {video.filename}")
        with open(input_path, "wb") as buffer:
            content = await video.read()
            buffer.write(content)
        
        file_size_mb = get_file_size_mb(input_path)
        print(f"📊 File size: {file_size_mb:.2f} MB")
        
        # Check file size limit
        if file_size_mb > settings.MAX_FILE_SIZE_MB:
            os.remove(input_path)
            raise HTTPException(
                status_code=400,
                detail=f"File too large ({file_size_mb:.1f}MB). Maximum size: {settings.MAX_FILE_SIZE_MB}MB"
            )
        
        # Generate manifest
        print(f"📝 Generating C2PA manifest...")
        manifest_path = c2pa_service.generate_manifest(
            organization=organization,
            ai_tool=ai_tool,
            title=title,
            description=description
        )
        print(f"✅ Manifest created: {manifest_path}")
        
        # Sign the video
        print(f"🔐 Signing video with C2PA credentials...")
        result = c2pa_service.sign_video(
            input_video_path=input_path,
            output_video_path=output_path,
            manifest_path=manifest_path
        )
        
        if not result['success']:
            raise Exception(result.get('error', 'Signing failed'))
        
        print(f"✅ Video signed successfully")
        
        # Extract manifest to separate JSON file
        print(f"📄 Extracting manifest to JSON...")
        manifest_extracted = c2pa_service.extract_manifest(
            output_path, 
            output_manifest_path
        )
        
        if manifest_extracted:
            print(f"✅ Manifest extracted: {output_manifest_path}")
        else:
            print(f"⚠️  Warning: Could not extract manifest to separate file")
        
        # Clean up temporary files
        print(f"🧹 Cleaning up temporary files...")
        if os.path.exists(input_path):
            os.remove(input_path)
        if manifest_path and os.path.exists(manifest_path):
            os.remove(manifest_path)
        
        print(f"✅ Process complete!")
        
        # Build response
        base_url = f"http://{settings.HOST}:{settings.PORT}"
        
        return SigningResponse(
            status="ok",
            message="C2PA signing succeeded in embedded mode.",
            job_id=job_id,
            links={
                "download_url": f"{base_url}/files/{os.path.basename(output_path)}",
                "manifest_url": f"{base_url}/files/{os.path.basename(output_manifest_path)}" if manifest_extracted else None,
                "mode": "embedded",
                "verify_at": "https://verify.contentauthenticity.org"
            },
            metadata={
                "original_filename": video.filename,
                "file_size_mb": round(file_size_mb, 2),
                "signed_at": datetime.utcnow().isoformat() + "Z",
                "organization": organization,
                "ai_tool": ai_tool,
                "title": title,
                "description": description
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        # Clean up on error
        print(f"❌ Error: {str(e)}")
        for path in [input_path, output_path, manifest_path, output_manifest_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except:
                    pass
        raise HTTPException(status_code=500, detail=f"Error signing video: {str(e)}")


@router.get(
    "/files/{filename}",
    summary="Download signed video or manifest",
    description="Download a signed video file or its manifest JSON",
    response_class=FileResponse,
    responses={
        200: {"description": "File download successful"},
        404: {"description": "File not found"},
        403: {"description": "Access denied"}
    }
)
async def download_file(filename: str):
    """
    ## Download a signed video or manifest file
    
    ### Parameters:
    - **filename**: The name of the file to download
    
    ### Example:
```
    GET /api/v1/files/video-signed-20231113-abc123.mp4
```
    """
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Security: Prevent directory traversal attacks
    real_path = os.path.abspath(file_path)
    allowed_dir = os.path.abspath(settings.UPLOAD_DIR)
    
    if not real_path.startswith(allowed_dir):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/octet-stream'
    )