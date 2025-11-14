from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
import os

# Create FastAPI application with full Swagger configuration
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    ## C2PA Video Signing Service
    
    This service adds **C2PA (Content Credentials)** to AI-generated videos, making them verifiable.
    
    ### Features:
    * 🎥 Upload and sign video files with C2PA credentials
    * 📝 Embed metadata (creator, AI tool, title, description)
    * 🔐 Cryptographically signed with X.509 certificates
    * ✅ Verifiable on [Adobe's Content Authenticity](https://verify.contentauthenticity.org)
    * 📦 Download signed videos and manifests
    
    ### How it works:
    1. Upload a video file with metadata
    2. System generates a C2PA manifest
    3. Video is signed using c2patool
    4. Download the signed video
    5. Verify on Adobe's website
    
    ### Quick Start:
    Use the **POST /api/v1/sign-video** endpoint to sign your first video!
    """,
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc alternative UI
    openapi_url="/openapi.json",  # OpenAPI schema
    contact={
        "name": "C2PA Video Service",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# CORS middleware (allow all origins for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory (for serving signed videos)
if os.path.exists(settings.UPLOAD_DIR):
    app.mount("/files", StaticFiles(directory=settings.UPLOAD_DIR), name="files")

# Root endpoint
@app.get("/", tags=["Health"])
async def root():
    """
    Root endpoint - Service information
    """
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "sign_video": "/api/v1/sign-video",
            "health": "/api/v1/health"
        }
    }

@app.get("/api/v1/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint - Verify service is operational
    """
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }

# Import and include routers (we'll create this next)
from app.api import routes
app.include_router(routes.router, prefix="/api/v1", tags=["C2PA Signing"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )