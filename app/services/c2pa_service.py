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
        # Initialize paths from settings first
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
            result = subprocess.run(
                ["c2patool", "--version"],
                capture_output=True,
                check=True,
                text=True
            )
            print(f"✅ c2patool version: {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            raise RuntimeError(f"c2patool is not installed or not in PATH: {e}")
    
    def generate_manifest(
        self,
        organization: str,
        ai_tool: str,
        title: Optional[str] = None,
        description: Optional[str] = None
    ) -> str:
        """
        Generate a C2PA manifest file with embedded signer configuration
        
        Args:
            organization: Organization name
            ai_tool: AI tool/model used
            title: Optional video title
            description: Optional video description
            
        Returns:
            Path to the generated manifest file
        """
        
        # Get relative paths for certificates (c2patool prefers relative paths)
        cert_dir = Path(self.cert_path).parent
        cert_name = Path(self.cert_path).name
        key_name = Path(self.private_key_path).name
        
        # Build the manifest structure with signer info
        manifest = {
            "alg": "es256",
            "private_key": key_name,
            "sign_cert": cert_name,
            "ta_url": "http://timestamp.digicert.com",
            "claim_generator": f"{settings.APP_NAME}/{settings.APP_VERSION}",
            "title": title if title else "AI Generated Content Credentials",
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
        if description:
            iptc_data["caption"] = description
        
        # Generate unique manifest filename in certificates directory
        manifest_id = str(uuid.uuid4())
        manifest_path = os.path.join(
            str(cert_dir), 
            f"manifest_{manifest_id}.json"
        )
        
        # Write manifest to file with proper encoding
        with open(manifest_path, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        print(f"📋 Manifest saved to: {manifest_path}")
        
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
            # Convert to absolute paths
            abs_input = os.path.abspath(input_video_path)
            abs_output = os.path.abspath(output_video_path)
            abs_manifest = os.path.abspath(manifest_path)
            
            # Get the directory containing the manifest (should be certificates dir)
            manifest_dir = str(Path(abs_manifest).parent)
            
            # Build c2patool command - use --manifest flag with file path
            cmd = [
                "c2patool",
                abs_input,
                "--manifest", abs_manifest,
                "--output", abs_output,
                "--force"
            ]
            
            print(f"🔧 Input: {abs_input}")
            print(f"🔧 Output: {abs_output}")
            print(f"🔧 Manifest: {abs_manifest}")
            print(f"🔧 Working directory: {manifest_dir}")
            print(f"🔧 Command: {' '.join(cmd)}")
            
            # Execute c2patool from the certificates directory
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=300,  # 5 minute timeout
                cwd=manifest_dir  # Run from certificates directory
            )
            
            # Verify output file was created
            if not os.path.exists(output_video_path):
                raise Exception("Signed video file was not created")
            
            # Check file size
            if os.path.getsize(output_video_path) == 0:
                raise Exception("Signed video file is empty")
            
            print(f"✅ c2patool stdout: {result.stdout}")
            
            return {
                "success": True,
                "output_path": output_video_path,
                "message": "Video signed successfully",
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
        except subprocess.CalledProcessError as e:
            error_msg = f"c2patool failed: {e.stderr if e.stderr else str(e)}"
            print(f"❌ c2patool error: {error_msg}")
            print(f"❌ stdout: {e.stdout if hasattr(e, 'stdout') else 'N/A'}")
            print(f"❌ stderr: {e.stderr if hasattr(e, 'stderr') else 'N/A'}")
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
            print(f"❌ Unexpected error: {str(e)}")
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
            # Convert to absolute paths
            abs_video_path = os.path.abspath(video_path)
            abs_output_path = os.path.abspath(output_json_path)
            
            # Use c2patool to extract manifest in JSON format
            cmd = [
                "c2patool",
                abs_video_path,
                "--info",
                "--output", abs_output_path,
                "--force"
            ]
            
            print(f"🔧 Extracting manifest from: {abs_video_path}")
            print(f"🔧 Output to: {abs_output_path}")
            print(f"🔧 Command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True,
                timeout=60
            )
            
            # If --info --output doesn't work, try alternate method
            if result.returncode != 0 or not os.path.exists(output_json_path):
                print(f"⚠️  First method failed, trying alternate extraction...")
                
                # Method 2: Get manifest as stdout and save it
                cmd2 = ["c2patool", abs_video_path, "--info"]
                result2 = subprocess.run(
                    cmd2,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=60
                )
                
                # Save stdout to file
                with open(abs_output_path, 'w', encoding='utf-8') as f:
                    f.write(result2.stdout)
                
                print(f"✅ Manifest extracted using alternate method")
            
            return os.path.exists(output_json_path)
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to extract manifest: {e.stderr if e.stderr else str(e)}")
            return False
        except Exception as e:
            print(f"❌ Failed to extract manifest: {e}")
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