"""Reads pictures with free models that run on this server; nothing is sent anywhere.

- Tesseract reads the text on a picture (Uzbek Latin and Cyrillic, Russian, English).
- Florence-2 (florence-community/Florence-2-base, MIT licence, about 0.25 B parameters) describes
  what is shown: a chart, a table, a diagram. It runs on CPU; the first call downloads the model.

Both are optional. Without Tesseract there is no OCR, without torch/transformers there are no
captions; the rest of the app keeps working and GET /api/ai/status says what is available.
Install them with `pip install -r requirements-vision.txt` and the tesseract-ocr packages.
"""

import io
import logging
import shutil
from dataclasses import dataclass
from functools import lru_cache

from app.config import get_settings

log = logging.getLogger(__name__)

# Pictures are scaled down to this before reading: enough for text, fast on CPU.
MAX_SIDE = 1600


@dataclass
class ImageText:
    caption: str = ""
    ocr_text: str = ""

    def describe(self) -> str:
        parts = []
        if self.caption:
            parts.append(f"На картинке: {self.caption}")
        if self.ocr_text:
            parts.append(f"Текст на картинке: {self.ocr_text}")
        return "\n".join(parts) or "Картинку прочитать не удалось."


def _open(data: bytes):
    from PIL import Image

    image = Image.open(io.BytesIO(data))
    image = image.convert("RGB")
    image.thumbnail((MAX_SIDE, MAX_SIDE))
    return image


# --- OCR ----------------------------------------------------------------------------------


@lru_cache
def ocr_languages() -> str:
    """The wanted Tesseract languages that are installed, joined with '+'; empty when OCR is off."""
    if shutil.which("tesseract") is None:
        return ""
    try:
        import pytesseract

        installed = set(pytesseract.get_languages(config=""))
    except Exception:
        return ""
    wanted = [lang for lang in get_settings().ocr_languages.split("+") if lang in installed]
    return "+".join(wanted)


def read_text(data: bytes) -> str:
    languages = ocr_languages()
    if not languages:
        return ""
    import pytesseract

    try:
        text = pytesseract.image_to_string(_open(data), lang=languages)
    except Exception as exc:
        log.warning("OCR failed: %s", exc)
        return ""
    # Join broken lines, drop the empty ones and the noise Tesseract finds in charts.
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if sum(ch.isalnum() for ch in line) >= 2)


# --- Captions -------------------------------------------------------------------------------


@lru_cache
def _florence():
    import torch
    from transformers import AutoProcessor, Florence2ForConditionalGeneration

    name = get_settings().vision_model
    model = Florence2ForConditionalGeneration.from_pretrained(name, dtype=torch.float32).eval()
    return model, AutoProcessor.from_pretrained(name)


def captions_available() -> bool:
    if not get_settings().vision_model:
        return False
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except ImportError:
        return False
    return True


def caption(data: bytes) -> str:
    if not captions_available():
        return ""
    try:
        import torch

        model, processor = _florence()
        task = "<MORE_DETAILED_CAPTION>"
        image = _open(data)
        inputs = processor(text=task, images=image, return_tensors="pt")
        with torch.inference_mode():
            ids = model.generate(**inputs, max_new_tokens=160, num_beams=3)
        raw = processor.batch_decode(ids, skip_special_tokens=False)[0]
        answer = processor.post_process_generation(raw, task=task, image_size=image.size)
        return str(answer.get(task, "")).strip()
    except Exception as exc:  # no model download, out of memory, a broken picture
        log.warning("Image caption failed: %s", exc)
        return ""


def read_image(data: bytes) -> ImageText:
    """Blocking: call it in a worker thread."""
    return ImageText(caption=caption(data), ocr_text=read_text(data))
