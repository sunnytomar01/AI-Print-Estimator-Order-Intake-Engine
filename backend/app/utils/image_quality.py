from io import BytesIO
from typing import Tuple

try:
    from PIL import Image
except Exception:
    Image = None


def get_image_dpi(content: bytes) -> Tuple[int, int]:
    """Return (xdpi, ydpi). Fall back to (72,72) if not available."""
    if Image is None:
        return (72, 72)
    try:
        img = Image.open(BytesIO(content))
        dpi = img.info.get("dpi")
        if dpi and isinstance(dpi, tuple):
            return (int(dpi[0]), int(dpi[1]))
        return (72, 72)
    except Exception:
        return (72, 72)
