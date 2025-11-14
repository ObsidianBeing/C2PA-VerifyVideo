import json
import subprocess
import os
import uuid
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
from app.core.config import settings

class C2PAService:
    """Service for handling C2PA signing operations"""
    
    def __init__(self):
        self.cert_path = settings.CERT_PATH
        self.private_key_path = settings.PRIVATE_KEY_PATH
        self.manifest_dir = settings.MANIFEST_DIR
        
        # Verify certificates exist
        if not os.path.exists(self.cert_path):
            raise FileNotFoundError(f"Certificate not found at: {self.cert_path}")
        if not os.path.exists(self.private_key_path):
            raise FileNotFoundError(f"Private key not found at: {self.private_key_path}")
        
        # Verify c2patool is installed
        try:
            subprocess.run(
                ["c2patool", "--version"],
                capture_output=True,
                check=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError("c2patool is not installed or not in PATH")
    
    def generate_manifest(
        self,
        organization: str,
        ai_tool: str,
        title: Optional[str] = None,
        description: Optional[str] = None
    ) -> str:
        """
        Generate a C2PA manifest file
        
        Args:
            organization: Organization name
            ai_tool: AI tool/model used
            title: Optional video title
            description: Optional video description
            
        Returns:
            Path to the generated manifest file
        """
        
        # Build the manifest structure
        manifest = {
            "claim_generator": f"{settings.APP_NAME}/{settings.APP_VERSION}",
            "title": "AI Generated Content Credentials",
            "assertions": [
                {
                    "label": "c2pa.actions",
                    "data": {
                        "actions": [
                            {
                                "action": "c2pa.created",
                                "softwareAgent": ai_tool,
                                "when": datetime.utcnow().isoformat() + "Z"
                            }
                        ]
                    }
                },
                {
                    "label": "stds.iptc.photo-metadata",
                    "data": {
                        "creator": [organization],
                        "creditLine": organization,
                        "digitalSourceType": "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"
                    }
                }
            ]
        }
        
        # Add optional IPTC metadata
        iptc_data = manifest["assertions"][1]["data"]
        if title:
            iptc_data["headline"] = title
        if description:
            iptc_data["caption"] = description
        
        # Generate unique manifest filename
        manifest_id = str(uuid.uuid4())
        manifest_path = os.path.join(
            self.manifest_dir, 
            f"manifest_{manifest_id}.json"
        )
        
        # Write manifest to file
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        return manifest_path
    
    def sign_video(
        self,
        input_video_path: str,
        output_video_path: str,
        manifest_path: str
    ) -> Dict[str, any]:
        """
        Sign video with C2PA credentials using c2patool
        
        Args:
            input_video_path: Path to input video
            output_video_path: Path where signed video will be saved
            manifest_path: Path to manifest JSON file
            
        Returns:
            Dictionary with success status and details
        """
        
        try:
            # Build c2patool command
            cmd = [
                "c2patool",
                input_video_path,
                "--manifest", manifest_path,
                "--output", output_video_path,
                "--force",  # to overwrite if exists already
                "--signer-path", str(Path(self.cert_path).parent),
            ]
            
            # Execute c2patool
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=300  # 5 minute timeout
            )
            
            # Verify output file was created
            if not os.path.exists(output_video_path):
                raise Exception("Signed video file was not created")
            
            # Check file size
            if os.path.getsize(output_video_path) == 0:
                raise Exception("Signed video file is empty")
            
            return {
                "success": True,
                "output_path": output_video_path,
                "message": "Video signed successfully",
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
        except subprocess.CalledProcessError as e:
            error_msg = f"c2patool failed: {e.stderr if e.stderr else str(e)}"
            return {
                "success": False,
                "error": error_msg,
                "stdout": e.stdout if hasattr(e, 'stdout') else "",
                "stderr": e.stderr if hasattr(e, 'stderr') else ""
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Signing operation timed out (exceeded 5 minutes)"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
    def extract_manifest(
        self, 
        video_path: str, 
        output_json_path: str
    ) -> bool:
        """
        Extract manifest from signed video to a separate JSON file
        
        Args:
            video_path: Path to signed video
            output_json_path: Path where manifest JSON will be saved
            
        Returns:
            True if extraction successful, False otherwise
        """
        
        try:
            cmd = [
                "c2patool",
                video_path,
                "--output", output_json_path,
                "--force"
            ]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=True,
                timeout=60
            )
            
            return os.path.exists(output_json_path)
            
        except Exception as e:
            print(f"Failed to extract manifest: {e}")
            return False
    
    def verify_video(self, video_path: str) -> Dict[str, any]:
        """
        Verify C2PA signature in video
        
        Args:
            video_path: Path to signed video
            
        Returns:
            Dictionary with verification status and info
        """
        
        try:
            cmd = ["c2patool", video_path, "--info"]
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=True,
                timeout=60
            )
            
            return {
                "valid": True,
                "info": result.stdout,
                "message": "Video signature is valid"
            }
        except subprocess.CalledProcessError as e:
            return {
                "valid": False,
                "error": e.stderr if e.stderr else str(e),
                "message": "Video signature verification failed"
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "message": "Verification process failed"
            }

# Create singleton instance
c2pa_service = C2PAService()