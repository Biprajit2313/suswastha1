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
        from app.core.logging import get_logger
        logger = get_logger(__name__)

        cloudinary.config(
            cloud_name=settings.cloudinary_cloud_name,
            api_key=settings.cloudinary_api_key,
            api_secret=settings.cloudinary_api_secret,
            secure=True,
        )

        path = Path(file_path)
        try:
            # Revert to resource_type="auto" for maximum compatibility across all Cloudinary account types.
            # "auto" will detect PDF and usually treat it as a 'raw' or 'image' resource depending on settings.
            logger.info(f"Uploading file to Cloudinary: {path.name}")
            response: dict[str, Any] = cloudinary.uploader.upload(
                str(path),
                resource_type="auto",
                access_mode="public",
                folder=settings.cloudinary_folder,
                use_filename=True,
                unique_filename=True,
                overwrite=True,
            )
            secure_url = response.get("secure_url")
            
            # Fallback: if secure_url is missing, try url
            if not secure_url:
                secure_url = response.get("url")

            if not isinstance(secure_url, str) or not secure_url:
                logger.error(f"Cloudinary upload failed to return URL. Response: {response}")
                raise RuntimeError("Cloudinary upload did not return a valid URL")
            
            logger.info(f"Cloudinary upload successful: {secure_url}")
            return secure_url
        except Exception as e:
            logger.error(f"Cloudinary upload exception: {str(e)}")
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
