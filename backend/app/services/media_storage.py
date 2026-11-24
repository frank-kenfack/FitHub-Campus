"""Validation par Pillow et stockage sur volume des images envoyees."""

import os
import uuid

from PIL import Image, UnidentifiedImageError
from werkzeug.datastructures import FileStorage

ALLOWED_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


def save_validated_image(
    file_storage: FileStorage | None,
    base_upload_folder: str,
    subfolder: str,
    max_size: tuple[int, int] = (800, 800),
) -> str:
    if file_storage is None or not file_storage.filename:
        raise ValueError("Aucun fichier image fourni.")

    try:
        file_storage.stream.seek(0)
        with Image.open(file_storage.stream) as probe:
            probe.verify()

        file_storage.stream.seek(0)
        with Image.open(file_storage.stream) as img:
            fmt = (img.format or "").upper()
            if fmt not in ALLOWED_FORMATS:
                raise ValueError("Format non supporte (JPG, PNG ou WEBP attendu).")

            ext = ALLOWED_FORMATS[fmt]
            target_dir = os.path.join(base_upload_folder, subfolder)
            os.makedirs(target_dir, exist_ok=True)

            # Un nom aleatoire et un re-encodage Pillow neutralisent les noms malveillants et metadonnees.
            filename = f"{uuid.uuid4().hex}.{ext}"
            dest_path = os.path.join(target_dir, filename)

            converted = img.convert("RGBA" if fmt == "PNG" else "RGB")
            converted.thumbnail(max_size)
            save_kwargs = {"optimize": True}
            if fmt in {"JPEG", "WEBP"}:
                save_kwargs["quality"] = 85
            converted.save(dest_path, format=fmt, **save_kwargs)

        return f"/uploads/{subfolder}/{filename}"
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Le fichier envoye n'est pas une image valide.") from exc


def remove_uploaded_file(relative_url: str, base_upload_folder: str) -> None:
    prefix = "/uploads/"
    if not relative_url or not relative_url.startswith(prefix):
        return
    rel_path = relative_url[len(prefix) :].replace("/", os.sep)
    abs_base = os.path.abspath(base_upload_folder)
    candidate = os.path.abspath(os.path.join(abs_base, rel_path))
    # Verification de confinement pour empecher toute traversee de repertoire hors d'uploads.
    if candidate.startswith(abs_base + os.sep) and os.path.isfile(candidate):
        try:
            os.remove(candidate)
        except OSError:
            pass
