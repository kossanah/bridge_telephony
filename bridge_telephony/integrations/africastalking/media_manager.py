"""
Media Manager for Call Queue Audio Files
Handles uploading and managing hold music and IVR prompts
Includes integration with Africa's Talking Media Upload API
"""

import frappe
import os
import mimetypes
import requests
from frappe import _
from frappe.utils import get_files_path, get_site_url
from werkzeug.utils import secure_filename


class MediaManager:
    """
    Manages audio media files for call queues and IVR
    Supports MP3, WAV, and other audio formats
    Integrates with Africa's Talking Media Upload API
    """

    ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg', 'm4a', 'aac'}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    AT_MEDIA_UPLOAD_URL = "https://voice.africastalking.com/mediaUpload"

    def __init__(self):
        self.files_path = get_files_path()
        self.media_folder = os.path.join(self.files_path, "telephony_media")
        self._ensure_media_folder()
        self._load_settings()

    def _load_settings(self):
        """Load Africa's Talking settings"""
        try:
            settings = frappe.get_single("Bridge Telephony Settings")
            self.at_username = settings.username
            self.at_api_key = settings.get_password("api_key") if settings.api_key else None
            self.at_enabled = settings.enabled
        except Exception as e:
            frappe.logger().debug(f"Could not load AT settings: {str(e)}")
            self.at_username = None
            self.at_api_key = None
            self.at_enabled = False

    def _ensure_media_folder(self):
        """Create media folder if it doesn't exist"""
        if not os.path.exists(self.media_folder):
            os.makedirs(self.media_folder)

    def _allowed_file(self, filename):
        """Check if file has allowed extension"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.ALLOWED_EXTENSIONS

    def upload_media(self, file, title=None, media_type="Hold Music"):
        """
        Upload an audio file and create Call Queue Media record

        Args:
            file: File object from request
            title: Title for the media (optional)
            media_type: Type - 'Hold Music', 'IVR Prompt', 'Ring Tone'

        Returns:
            dict: Success status and media doc name
        """
        try:
            # Validate file
            if not file:
                return {
                    "success": False,
                    "error": "No file provided"
                }

            if not self._allowed_file(file.filename):
                return {
                    "success": False,
                    "error": f"Invalid file type. Allowed: {', '.join(self.ALLOWED_EXTENSIONS)}"
                }

            # Check file size
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)

            if file_size > self.MAX_FILE_SIZE:
                return {
                    "success": False,
                    "error": f"File too large. Maximum size: {self.MAX_FILE_SIZE / (1024*1024)}MB"
                }

            # Generate secure filename
            filename = secure_filename(file.filename)
            timestamp = frappe.utils.now_datetime().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{filename}"

            # Save file
            file_path = os.path.join(self.media_folder, filename)
            file.save(file_path)

            # Generate public URL
            public_url = self._get_public_url(filename)

            # Get file info
            file_info = self._get_file_info(file_path)

            # Create Call Queue Media record
            if not title:
                title = filename.rsplit('.', 1)[0]

            media_doc = frappe.get_doc({
                "doctype": "Call Queue Media",
                "title": title,
                "media_type": media_type,
                "file_url": f"/private/files/telephony_media/{filename}",
                "public_url": public_url,
                "duration": file_info.get("duration", 0),
                "status": "Pending"  # Start as Pending, update after AT upload
            })
            media_doc.insert(ignore_permissions=True)

            # Upload to Africa's Talking Media API
            at_upload_result = self.upload_to_africastalking(file_path, public_url)

            if at_upload_result.get("success"):
                media_doc.status = "Active"
                media_doc.at_media_url = at_upload_result.get("at_url", public_url)
                media_doc.save(ignore_permissions=True)
            else:
                # Still save locally even if AT upload fails
                media_doc.status = "Local Only"
                media_doc.at_upload_error = at_upload_result.get("error", "Unknown error")
                media_doc.save(ignore_permissions=True)
                frappe.log_error(
                    title="AT Media Upload Warning",
                    message=f"Media saved locally but AT upload failed: {at_upload_result.get('error')}"
                )

            frappe.db.commit()

            return {
                "success": True,
                "message": "Media uploaded successfully",
                "media_name": media_doc.name,
                "public_url": public_url,
                "at_upload": at_upload_result
            }

        except Exception as e:
            frappe.log_error(
                title="Media Upload Error",
                message=f"Error uploading media: {str(e)}"
            )
            return {
                "success": False,
                "error": str(e)
            }

    def delete_media(self, media_name):
        """
        Delete a media file and its record

        Args:
            media_name: Name of Call Queue Media document

        Returns:
            dict: Success status
        """
        try:
            media_doc = frappe.get_doc("Call Queue Media", media_name)

            # Delete physical file if exists
            if media_doc.file_url:
                file_path = self._get_file_path_from_url(media_doc.file_url)
                if os.path.exists(file_path):
                    os.remove(file_path)

            # Delete document
            frappe.delete_doc("Call Queue Media", media_name, force=True)
            frappe.db.commit()

            return {
                "success": True,
                "message": "Media deleted successfully"
            }

        except Exception as e:
            frappe.log_error(
                title="Media Delete Error",
                message=f"Error deleting media: {str(e)}"
            )
            return {
                "success": False,
                "error": str(e)
            }

    def get_media_list(self, media_type=None):
        """
        Get list of available media files

        Args:
            media_type: Filter by media type (optional)

        Returns:
            list: List of media documents
        """
        try:
            filters = {"status": "Active"}
            if media_type:
                filters["media_type"] = media_type

            media_list = frappe.get_all(
                "Call Queue Media",
                filters=filters,
                fields=["name", "title", "media_type", "public_url", "duration", "creation"],
                order_by="creation desc"
            )

            return {
                "success": True,
                "data": media_list
            }

        except Exception as e:
            frappe.log_error(
                title="Get Media List Error",
                message=f"Error: {str(e)}"
            )
            return {
                "success": False,
                "error": str(e)
            }

    def _get_public_url(self, filename):
        """Generate public URL for file"""
        site_url = get_site_url(frappe.local.site)
        return f"{site_url}/files/telephony_media/{filename}"

    def _get_file_path_from_url(self, file_url):
        """Convert file URL to filesystem path"""
        # Remove leading slash and 'private/' if present
        relative_path = file_url.lstrip('/').replace('private/', '')
        return os.path.join(frappe.get_site_path(), relative_path)

    def upload_to_africastalking(self, file_path, public_url):
        """
        Upload media file to Africa's Talking Media Upload API

        API Endpoint: POST https://voice.africastalking.com/mediaUpload

        Args:
            file_path: Local path to the audio file
            public_url: Public URL where the file is accessible

        Returns:
            dict: Upload result with success status
        """
        try:
            # Reload settings to ensure we have latest credentials
            self._load_settings()

            if not self.at_enabled:
                return {
                    "success": False,
                    "error": "Africa's Talking integration is not enabled"
                }

            if not self.at_username or not self.at_api_key:
                return {
                    "success": False,
                    "error": "Africa's Talking credentials not configured"
                }

            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "error": f"File not found: {file_path}"
                }

            # Prepare the request
            headers = {
                "apiKey": self.at_api_key,
                "Accept": "application/json"
            }

            # Africa's Talking Media Upload API accepts multipart/form-data
            # with 'username', 'url' (or 'phoneNumber') fields
            # Method 1: Upload via URL (if file is publicly accessible)
            # Method 2: Upload file directly

            # Try URL-based upload first (more reliable for AT)
            data = {
                "username": self.at_username,
                "url": public_url
            }

            frappe.logger().info(f"Uploading media to Africa's Talking: {public_url}")

            response = requests.post(
                self.AT_MEDIA_UPLOAD_URL,
                headers=headers,
                data=data,
                timeout=60
            )

            if response.status_code == 201 or response.status_code == 200:
                # Success
                frappe.logger().info(f"AT Media upload successful: {response.text}")
                return {
                    "success": True,
                    "message": "Media uploaded to Africa's Talking successfully",
                    "at_url": public_url,
                    "response": response.text
                }
            elif response.status_code == 400:
                # Bad request - might need to try file upload instead
                frappe.logger().warning(f"AT URL upload failed, trying file upload: {response.text}")
                return self._upload_file_directly(file_path, headers)
            else:
                return {
                    "success": False,
                    "error": f"AT API returned status {response.status_code}: {response.text}"
                }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Connection to Africa's Talking timed out"
            }
        except requests.exceptions.ConnectionError as e:
            return {
                "success": False,
                "error": f"Could not connect to Africa's Talking: {str(e)}"
            }
        except Exception as e:
            frappe.log_error(
                title="AT Media Upload Error",
                message=f"Error uploading to AT: {str(e)}"
            )
            return {
                "success": False,
                "error": str(e)
            }

    def _upload_file_directly(self, file_path, headers):
        """
        Upload file directly to Africa's Talking (fallback method)

        Args:
            file_path: Path to the audio file
            headers: API headers with authentication

        Returns:
            dict: Upload result
        """
        try:
            filename = os.path.basename(file_path)
            mime_type, _ = mimetypes.guess_type(file_path)

            with open(file_path, 'rb') as f:
                files = {
                    'file': (filename, f, mime_type or 'audio/mpeg')
                }
                data = {
                    'username': self.at_username
                }

                response = requests.post(
                    self.AT_MEDIA_UPLOAD_URL,
                    headers=headers,
                    data=data,
                    files=files,
                    timeout=120  # Longer timeout for file upload
                )

            if response.status_code in [200, 201]:
                return {
                    "success": True,
                    "message": "Media file uploaded directly to Africa's Talking",
                    "response": response.text
                }
            else:
                return {
                    "success": False,
                    "error": f"Direct file upload failed with status {response.status_code}: {response.text}"
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Direct file upload error: {str(e)}"
            }

    def retry_at_upload(self, media_name):
        """
        Retry uploading a media file to Africa's Talking

        Args:
            media_name: Name of Call Queue Media document

        Returns:
            dict: Upload result
        """
        try:
            media_doc = frappe.get_doc("Call Queue Media", media_name)

            if not media_doc.file_url:
                return {
                    "success": False,
                    "error": "No file URL found for this media"
                }

            file_path = self._get_file_path_from_url(media_doc.file_url)

            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "error": "Local file not found"
                }

            public_url = media_doc.public_url or self._get_public_url(os.path.basename(file_path))

            result = self.upload_to_africastalking(file_path, public_url)

            if result.get("success"):
                media_doc.status = "Active"
                media_doc.at_media_url = result.get("at_url", public_url)
                media_doc.at_upload_error = None
                media_doc.save(ignore_permissions=True)
                frappe.db.commit()

            return result

        except Exception as e:
            frappe.log_error(
                title="Retry AT Upload Error",
                message=str(e)
            )
            return {
                "success": False,
                "error": str(e)
            }

    def _get_file_info(self, file_path):
        """
        Get file information like duration, format, etc.

        Args:
            file_path: Path to audio file

        Returns:
            dict: File information
        """
        info = {
            "duration": 0,
            "format": None,
            "size": 0
        }

        try:
            # Get file size
            info["size"] = os.path.getsize(file_path)

            # Get mime type
            mime_type, _ = mimetypes.guess_type(file_path)
            info["format"] = mime_type

            # Try to get duration using mutagen if available
            try:
                from mutagen import File as MutagenFile
                audio = MutagenFile(file_path)
                if audio and hasattr(audio.info, 'length'):
                    info["duration"] = int(audio.info.length)
            except ImportError:
                # mutagen not available, duration will be 0
                pass
            except Exception as e:
                frappe.logger().debug(f"Could not get audio duration: {str(e)}")

        except Exception as e:
            frappe.logger().debug(f"Error getting file info: {str(e)}")

        return info

    def validate_media_url(self, url):
        """
        Validate if a media URL is accessible

        Args:
            url: Media URL to validate

        Returns:
            dict: Validation result
        """
        try:
            import requests
            response = requests.head(url, timeout=5)

            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "URL is accessible"
                }
            else:
                return {
                    "success": False,
                    "error": f"URL returned status code: {response.status_code}"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# Whitelisted API methods

@frappe.whitelist()
def upload_media_file():
    """
    API endpoint to upload media file

    Expected form data:
        - file: Audio file
        - title: Media title (optional)
        - media_type: Type of media (optional)

    Returns:
        dict: Upload result
    """
    try:
        if 'file' not in frappe.request.files:
            frappe.throw(_("No file uploaded"))

        file = frappe.request.files['file']
        title = frappe.form_dict.get('title')
        media_type = frappe.form_dict.get('media_type', 'Hold Music')

        manager = MediaManager()
        result = manager.upload_media(file, title, media_type)

        return result

    except Exception as e:
        frappe.log_error(
            title="Upload Media API Error",
            message=str(e)
        )
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def delete_media_file(media_name):
    """
    API endpoint to delete media file

    Args:
        media_name: Name of Call Queue Media document

    Returns:
        dict: Delete result
    """
    try:
        manager = MediaManager()
        result = manager.delete_media(media_name)
        return result

    except Exception as e:
        frappe.log_error(
            title="Delete Media API Error",
            message=str(e)
        )
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def get_media_files(media_type=None):
    """
    API endpoint to get list of media files

    Args:
        media_type: Filter by media type (optional)

    Returns:
        dict: List of media files
    """
    try:
        manager = MediaManager()
        result = manager.get_media_list(media_type)
        return result

    except Exception as e:
        frappe.log_error(
            title="Get Media Files API Error",
            message=str(e)
        )
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def validate_media_url(url):
    """
    API endpoint to validate media URL

    Args:
        url: Media URL to validate

    Returns:
        dict: Validation result
    """
    try:
        manager = MediaManager()
        result = manager.validate_media_url(url)
        return result

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
