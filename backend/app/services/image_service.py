import tempfile
from pathlib import Path

from fastapi import UploadFile


class ImageService:
    async def save_upload(self, upload: UploadFile) -> Path:
        suffix = Path(upload.filename or "upload.png").suffix or ".png"
        fd, name = tempfile.mkstemp(prefix="suswastha_image_", suffix=suffix)
        path = Path(name)
        with path.open("wb") as handle:
            while chunk := await upload.read(1024 * 1024):
                handle.write(chunk)
        return path

    def cleanup(self, path: Path) -> None:
        path.unlink(missing_ok=True)
