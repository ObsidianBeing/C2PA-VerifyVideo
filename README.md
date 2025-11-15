# C2PA-VerifyVideo

A production-ready FastAPI service for signing AI-generated videos with **C2PA (Content Credentials)** to make them publicly verifiable. Videos are cryptographically signed with metadata about their origin, creator, and AI tools used, allowing anyone to verify authenticity on [Adobe's Content Authenticity website](https://verify.contentauthenticity.org).

## 🎯 Features

- 🎥 **Video Signing**: Upload and sign videos with C2PA content credentials
- 📝 **Rich Metadata**: Embed creator info, AI tool details, titles, and descriptions
- 🔐 **Cryptographic Security**: Sign with X.509 certificates (ES256 algorithm)
- ✅ **Public Verification**: Verify signed videos on Adobe's official verifier
- 📦 **Download Support**: Get both signed videos and manifest JSON files
- 🚀 **Production Ready**: Error handling, validation, rate limiting, security features
- 📚 **Full API Documentation**: Interactive Swagger UI and ReDoc

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python 3.8+)
- **C2PA Tool**: c2patool (official C2PA reference implementation)
- **Certificate Format**: X.509 with ES256 (Elliptic Curve)
- **Video Formats**: MP4, MOV, M4V

## 📋 Prerequisites

### System Requirements
- Python 3.8 or higher
- OpenSSL (for certificate generation)
- c2patool installed and in PATH

### Install c2patool

**Windows (PowerShell):**
```powershell
# Using cargo (Rust package manager)
cargo install c2patool

# Or download pre-built binary from:
# https://github.com/contentauth/c2patool/releases
```

**macOS:**
```bash
# Using Homebrew
brew install contentauth/tools/c2patool

# Or using cargo
cargo install c2patool
```

**Linux:**
```bash
# Using cargo
cargo install c2patool
```

**Verify installation:**
```bash
c2patool --version
```

## 🚀 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/C2PA-VerifyVideo.git
cd C2PA-VerifyVideo
```

### 2. Create Virtual Environment
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Generate C2PA Certificates

**Windows (PowerShell):**
```powershell
.\generate_c2pa_certs.ps1
```

**macOS/Linux:**
```bash
chmod +x generate_c2pa_certs.sh
./generate_c2pa_certs.sh
```

This creates:
- `certificates_new/sign-cert.pem` - Certificate chain (signing cert + CA)
- `certificates_new/sign-key.pem` - Private key (PKCS#8 format)
- `certificates_new/signer.json` - c2patool configuration

### 5. Copy Certificates
```powershell
# Windows
Copy-Item certificates_new\sign-cert.pem certificates\ -Force
Copy-Item certificates_new\sign-key.pem certificates\ -Force
Copy-Item certificates_new\signer.json certificates\ -Force

# macOS/Linux
cp certificates_new/sign-cert.pem certificates/
cp certificates_new/sign-key.pem certificates/
cp certificates_new/signer.json certificates/
```

### 6. Configure Environment

The `.env` file should already be configured correctly:
```env
# Application Settings
APP_NAME="C2PA Video Signing Service"
APP_VERSION="1.0.0"
DEBUG=True
HOST=0.0.0.0
PORT=8000

# File Storage
UPLOAD_DIR=./files
MAX_FILE_SIZE_MB=500

# C2PA Settings
CERT_PATH=./certificates/sign-cert.pem
PRIVATE_KEY_PATH=./certificates/sign-key.pem
MANIFEST_DIR=./manifests
```

### 7. Run the Server
```bash
# Development mode (auto-reload enabled)
python main.py

# Or using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The server will start at: `http://localhost:8000`

## 📖 API Documentation

Once the server is running, access the interactive documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## 🎬 Example Usage

### Upload and Sign a Video

**Using curl:**
```bash
curl -X POST "http://localhost:8000/api/v1/sign-video" \
  -F "video=@my_video.mp4" \
  -F "organization=Acme AI Corporation" \
  -F "ai_tool=Veo 3" \
  -F "title=AI Generated Landscape" \
  -F "description=Beautiful mountain scenery created by AI"
```

**Response:**
```json
{
  "status": "ok",
  "message": "C2PA signing succeeded in embedded mode.",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "links": {
    "download_url": "http://localhost:8000/api/v1/files/video-signed-20251115_010530-550e8400.mp4",
    "manifest_url": "http://localhost:8000/api/v1/files/video-signed-20251115_010530-550e8400.manifest.json",
    "mode": "embedded",
    "verify_at": "https://verify.contentauthenticity.org"
  },
  "metadata": {
    "original_filename": "my_video.mp4",
    "file_size_mb": 206.3,
    "signed_at": "2025-11-15T01:05:30.123456Z",
    "organization": "Acme AI Corporation",
    "ai_tool": "Veo 3",
    "title": "AI Generated Landscape",
    "description": "Beautiful mountain scenery created by AI"
  }
}
```

### Download Signed Video

**Using curl:**
```bash
# Download signed video
curl -O "http://localhost:8000/api/v1/files/video-signed-20251115_010530-550e8400.mp4"

# Download manifest JSON
curl -O "http://localhost:8000/api/v1/files/video-signed-20251115_010530-550e8400.manifest.json"
```

**Using browser:**
Simply paste the URL from `download_url` in your browser:
```
http://localhost:8000/api/v1/files/video-signed-20251115_010530-550e8400.mp4
```

### Verify the Signed Video

1. Download the signed video using the URL from the response
2. Go to https://verify.contentauthenticity.org
3. Upload your signed video
4. View the embedded Content Credentials

**Expected Result:**
- ✅ Content Credential found and readable
- ⚠️ Issuer shows as "Unrecognized" (because test certificates aren't in Adobe's trust list)
- ✅ Metadata visible: organization, AI tool, title, creation date, actions

### Using Python Requests

```python
import requests

# 1. Sign video
with open('my_video.mp4', 'rb') as video_file:
    response = requests.post(
        'http://localhost:8000/api/v1/sign-video',
        files={'video': video_file},
        data={
            'organization': 'My Company',
            'ai_tool': 'Runway Gen-3',
            'title': 'Product Demo Video',
            'description': 'AI-generated product demonstration'
        }
    )

result = response.json()
print(f"Job ID: {result['job_id']}")
print(f"Download URL: {result['links']['download_url']}")

# 2. Download signed video
video_response = requests.get(result['links']['download_url'])
with open('signed_video.mp4', 'wb') as f:
    f.write(video_response.content)

print("✅ Video signed and downloaded successfully!")
```

### Using JavaScript/Fetch

```javascript
// 1. Sign video
const formData = new FormData();
formData.append('video', fileInput.files[0]);
formData.append('organization', 'My Company');
formData.append('ai_tool', 'Midjourney Video');
formData.append('title', 'Product Launch');
formData.append('description', 'AI-generated promotional video');

const response = await fetch('http://localhost:8000/api/v1/sign-video', {
  method: 'POST',
  body: formData
});

const result = await response.json();
console.log('Signed video URL:', result.links.download_url);

// 2. Download signed video
const videoBlob = await fetch(result.links.download_url).then(r => r.blob());
const url = window.URL.createObjectURL(videoBlob);
const a = document.createElement('a');
a.href = url;
a.download = 'signed-video.mp4';
a.click();
```

## 📦 Project Structure

```
C2PA-VerifyVideo/
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py          # API endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py          # Configuration & settings
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py         # Pydantic models
│   └── services/
│       ├── __init__.py
│       └── c2pa_service.py    # C2PA signing logic
├── certificates/              # Certificate storage
│   ├── sign-cert.pem         # Certificate chain
│   ├── sign-key.pem          # Private key
│   └── signer.json           # c2patool config
├── files/                    # Uploaded & signed videos
├── manifests/                # Generated C2PA manifests
├── .env                      # Environment configuration
├── .gitignore
├── generate_c2pa_certs.ps1   # Windows cert generator
├── generate_c2pa_certs.sh    # Unix cert generator
├── LICENSE
├── main.py                   # Application entry point
├── README.md
└── requirements.txt          # Python dependencies
```

## 🔒 Security Features

- ✅ **Path Traversal Prevention**: Blocks directory traversal attacks
- ✅ **File Type Validation**: Only accepts MP4, MOV, M4V formats
- ✅ **File Size Limits**: Configurable max file size (default 500MB)
- ✅ **Input Sanitization**: Removes dangerous characters from metadata
- ✅ **CORS Middleware**: Configurable cross-origin requests
- ✅ **Cryptographic Signing**: ES256 algorithm with certificate chain

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_NAME` | Application name | "C2PA Video Signing Service" |
| `APP_VERSION` | Application version | "1.0.0" |
| `DEBUG` | Enable debug mode | True |
| `HOST` | Server host | 0.0.0.0 |
| `PORT` | Server port | 8000 |
| `UPLOAD_DIR` | Directory for files | ./files |
| `MAX_FILE_SIZE_MB` | Max upload size | 500 |
| `CERT_PATH` | Certificate path | ./certificates/sign-cert.pem |
| `PRIVATE_KEY_PATH` | Private key path | ./certificates/sign-key.pem |
| `MANIFEST_DIR` | Manifest storage | ./manifests |

## 🧪 Testing

### Health Check
```bash
curl http://localhost:8000/api/v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "C2PA Video Signing Service",
  "version": "1.0.0"
}
```

### Test Video Signing
Use the sample video files in the `tests/` directory (create one if needed):

```bash
curl -X POST "http://localhost:8000/api/v1/sign-video" \
  -F "video=@test_video.mp4" \
  -F "organization=Test Org" \
  -F "ai_tool=Test Tool" \
  -F "title=Test Video"
```

## 🐛 Troubleshooting

### c2patool not found
```bash
# Verify installation
c2patool --version

# If not found, install:
cargo install c2patool
```

### Certificate errors
```bash
# Regenerate certificates
.\generate_c2pa_certs.ps1  # Windows
./generate_c2pa_certs.sh   # Unix

# Verify certificates exist
ls certificates/sign-cert.pem
ls certificates/sign-key.pem
```

### File upload errors
- Check file size (default max: 500MB)
- Verify file format (MP4, MOV, M4V only)
- Ensure `files/` directory has write permissions

### "COSE error parsing certificate"
- Make sure you're using the certificates generated by the script
- Certificate chain must include both signing cert and CA cert
- Private key must be in PKCS#8 format

## 📊 API Endpoints

### POST `/api/v1/sign-video`
Sign a video with C2PA credentials

**Parameters:**
- `video` (file, required): Video file to sign
- `organization` (string, required): Organization name
- `ai_tool` (string, required): AI tool/model used
- `title` (string, optional): Video title
- `description` (string, optional): Video description

**Response:** SigningResponse with download URLs

### GET `/api/v1/files/{filename}`
Download signed video or manifest

**Parameters:**
- `filename` (path, required): File name to download

**Response:** File download

### GET `/api/v1/health`
Health check endpoint

**Response:** Service status

### GET `/`
Root endpoint with service information

**Response:** Service details and available endpoints

## 🚀 Production Deployment

### Using Trusted Certificates

For production use, replace test certificates with certificates from a trusted CA:

1. **Purchase a code signing certificate** from:
   - DigiCert
   - GlobalSign
   - Sectigo

2. **Replace certificate files:**
   ```bash
   cp your-production-cert.pem certificates/sign-cert.pem
   cp your-production-key.pem certificates/sign-key.pem
   ```

3. **Update signer.json:**
   ```json
   {
       "cert": "sign-cert.pem",
       "key": "sign-key.pem"
   }
   ```

### Deployment Considerations

- Set `DEBUG=False` in production
- Use a reverse proxy (nginx, Apache)
- Enable HTTPS/TLS
- Set up proper logging
- Implement rate limiting
- Add authentication/authorization
- Set up file cleanup/archival
- Monitor disk space for uploads
- Use environment-specific `.env` files

### Docker Deployment (Optional)

```dockerfile
# Dockerfile example
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    openssl \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Rust and c2patool
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
RUN cargo install c2patool

# Copy application
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create directories
RUN mkdir -p files manifests certificates

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Support

For issues, questions, or contributions:
- GitHub Issues: [Create an issue](https://github.com/ObsidianBeing/C2PA-VerifyVideo/issues)
- Email: abeltibbeshana@gmail.com/obsidian.being.tech@gmail.com

## 🔗 Links

- **C2PA Specification**: https://c2pa.org/specifications/
- **c2patool**: https://github.com/contentauth/c2patool
- **Adobe Content Authenticity**: https://contentauthenticity.org/
- **Verify Tool**: https://verify.contentauthenticity.org
- **FastAPI Documentation**: https://fastapi.tiangolo.com/


---

**Built with ❤️ for content authenticity and transparency**
