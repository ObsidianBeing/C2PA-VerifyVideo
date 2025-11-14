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
        # Use EC certificates for ECDSA signing
        self.cert_path = "./certificates/rsa_certificate.pem"
        self.private_key_path = "./certificates/rsa_private_key.pem"
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
        """
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
        Sign MP4 video with C2PA credentials using c2patool with ECDSA
        """

        try:
            print(f"🔍 DEBUG: Using cert: {self.cert_path}")
            print(f"🔍 DEBUG: Using key: {self.private_key_path}")
            
            # For c2patool 0.9.12: Options come BEFORE the path
            # Syntax: c2patool [OPTIONS] <PATH>
            cmd = [
                "c2patool",
                "-m", str(manifest_path),
                "-o", str(output_video_path),
                "--signer-path", "certificates" ,
                "-f",
                str(input_video_path)  # Path comes LAST
            ]

            print(f"🔧 Running command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=300
            )

            if not os.path.exists(output_video_path) or os.path.getsize(output_video_path) == 0:
                raise Exception("Signed video file was not created or is empty")

            return {
                "success": True,
                "output_path": output_video_path,
                "message": "Video signed successfully",
                "stdout": result.stdout,
                "stderr": result.stderr
            }

        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": f"c2patool failed: {e.stderr if e.stderr else str(e)}",
                "stdout": e.stdout if hasattr(e, 'stdout') else "",
                "stderr": e.stderr if hasattr(e, 'stderr') else "",
                "command": ' '.join(cmd)
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
        """
        try:
            # Use --info flag to get manifest data, then save to JSON
            cmd = [
                "c2patool",
                video_path,
                "--info"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=60
            )

            # Save the output to JSON file
            if result.stdout:
                with open(output_json_path, 'w', encoding='utf-8') as f:
                    f.write(result.stdout)
                return os.path.exists(output_json_path)
            
            return False

        except Exception as e:
            print(f"Failed to extract manifest: {e}")
            return False

    def verify_video(self, video_path: str) -> Dict[str, any]:
        """
        Verify C2PA signature in video
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

# Singleton instance
c2pa_service = C2PAService()