"""
photo_service — upload validation + compression/resizing pipeline.

Always re-encodes to JPEG at a fixed square size (120x120 or 200x200),
regardless of the source format, so storage and template rendering never
have to think about original dimensions/formats again.
"""
import io
import uuid
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from app.extensions import db
from app.models import Photo

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
TARGET_SIZES = {"120": (120, 120), "200": (200, 200)}
JPEG_QUALITY = 82


class PhotoError(Exception):
    """Base class for photo validation/processing errors."""


class PhotoTooLarge(PhotoError):
    pass


class PhotoInvalidFormat(PhotoError):
    pass


def process_and_save_photo(file_storage, user_id: int, max_upload_bytes: int,
                            photos_dir: str, variant: str = "200") -> Photo:
    """
    Validates the uploaded file, compresses/resizes it, writes it to disk,
    and returns a persisted Photo row.

    Raises PhotoTooLarge / PhotoInvalidFormat on invalid input — callers
    should catch these and turn them into a user-facing 4xx response.
    """
    if variant not in TARGET_SIZES:
        raise ValueError(f"Unsupported variant: {variant}")

    raw = file_storage.read()
    if len(raw) > max_upload_bytes:
        raise PhotoTooLarge(f"File exceeds {max_upload_bytes} bytes")

    try:
        img = Image.open(io.BytesIO(raw))
        img.verify()  # sanity-check it's really an image
        img = Image.open(io.BytesIO(raw))  # re-open: verify() consumes the parser
    except UnidentifiedImageError as exc:
        raise PhotoInvalidFormat("Not a recognizable image file") from exc

    if img.format not in ALLOWED_FORMATS:
        raise PhotoInvalidFormat(f"Unsupported image format: {img.format}")

    img = ImageOps.exif_transpose(img)
    img = img.convert("RGB")

    size = TARGET_SIZES[variant]
    img = ImageOps.fit(img, size, method=Image.LANCZOS, centering=(0.5, 0.3))

    out = io.BytesIO()
    img.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    processed_bytes = out.getvalue()

    user_dir = Path(photos_dir) / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4().hex}.jpg"
    dest_path = user_dir / filename
    dest_path.write_bytes(processed_bytes)

    photo = Photo(
        user_id=user_id,
        storage_path=str(Path(str(user_id)) / filename),  # relative, stored path
        variant=variant,
        width=size[0],
        height=size[1],
        filesize_bytes=len(processed_bytes),
        original_filename=getattr(file_storage, "filename", None),
    )
    db.session.add(photo)
    db.session.commit()
    return photo


def delete_photo_file(photo: Photo, photos_dir: str) -> None:
    path = Path(photos_dir) / photo.storage_path
    if path.exists():
        path.unlink()
