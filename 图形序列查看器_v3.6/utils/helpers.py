"""Small shared utility helpers."""
from typing import Any
import re

def natural_key(text: Any) -> Any:
    return [int(part) if part.isdigit() else part.lower() for part in re.split('(\\d+)', str(text))]
