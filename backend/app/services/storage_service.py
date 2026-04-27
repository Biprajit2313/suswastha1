from pathlib import Path
from typing import Any

from app.core.config import get_settings


class StorageService:
    def upload_pdf(self, file_path: str) -> str:
        """
        Upload a local PDF to Cloudinary and return a secure URL.

        Contract:
        - Uses resource_type='raw'
        - Uses folder='suswastha_reports'
        - Deletes the local file after upload attempt
        """
        settings = get_settings()
        if not (
            settings.cloudinary_cloud_name
            and settings.cloudinary_api_key
            and settings.cloudinary_api_secret
        ):
            raise RuntimeError("Cloudinary credentials are not configured")

        import cloudinary
        import cloudinary.utils
        import cloudinary.uploader

        cloudinary.config(
            cloud_name=settings.cloudinary_cloud_name,
            api_key=settings.cloudinary_api_key,
            api_secret=settings.cloudinary_api_secret,
            secure=True,
        )

        path = Path(file_path)
        try:
            # Use resource_type="image" for PDFs to enable better delivery features in Cloudinary.
            # We also set the format explicitly to 'pdf'.
            logger.info("uploading_to_cloudinary", extra={"file": str(path)})
            response: dict[str, Any] = cloudinary.uploader.upload(
                str(path),
                resource_type="image",
                format="pdf",
                access_mode="public",
                folder=settings.cloudinary_folder,
                use_filename=True,
                unique_filename=True,
                overwrite=True,
            )
            secure_url = response.get("secure_url")
            if not isinstance(secure_url, str) or not secure_url:
                logger.error("cloudinary_upload_no_url", extra={"response": response})
                raise RuntimeError("Cloudinary upload did not return a secure URL")
            
            logger.info("cloudinary_upload_success", extra={"url": secure_url})
            return secure_url
        except Exception as e:
            logger.exception("cloudinary_upload_failed", extra={"error": str(e)})
            raise RuntimeError(f"Cloudinary upload failed: {str(e)}") from e
        finally:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                # best-effort cleanup; upstream can log if needed
                pass

    def upload_file(self, file_path: str | Path) -> str:
        # Backward-compatible wrapper used by older code paths.
        return self.upload_pdf(str(file_path))
