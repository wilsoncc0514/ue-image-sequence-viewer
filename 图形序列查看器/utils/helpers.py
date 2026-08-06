"""Small shared utility helpers."""
import re
from typing import Any


def natural_key(text: Any) -> Any:
    return [int(part) if part.isdigit() else part.lower() for part in re.split('(\\d+)', str(text))]
