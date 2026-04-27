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
            response: dict[str, Any] = cloudinary.uploader.upload(
                str(path),
                resource_type="raw",
                folder=settings.cloudinary_folder,
                public_id=path.stem,
                overwrite=True,
            )
            secure_url = response.get("secure_url")
            if not isinstance(secure_url, str) or not secure_url:
                raise RuntimeError("Cloudinary upload did not return a secure URL")
            return secure_url
        finally:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                # best-effort cleanup; upstream can log if needed
                pass

    def upload_file(self, file_path: str | Path) -> str:
        # Backward-compatible wrapper used by older code paths.
        return self.upload_pdf(str(file_path))
