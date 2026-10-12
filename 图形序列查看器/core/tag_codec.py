"""Lossless tag-cell encoding with a reader for legacy human-readable CSVs."""
from __future__ import annotations

import json
import re
from typing import TypedDict

from core.tag_engine import normalize_sub_value, normalize_tag_name


class ParsedTag(TypedDict):
    check: bool
    text: str
    sub: str | None


def encode_note(text: str) -> str:
    """Quote new notes so delimiters and tag names cannot become syntax."""
    return json.dumps(text, ensure_ascii=False)


def parse_tag_cell(text: str, names: list[str]) -> dict[str, ParsedTag]:
    """Parse complete tag tokens, never search inside another tag's note.

    New notes are JSON strings. Legacy notes end only at a separator followed
    by a known tag, preserving ordinary punctuation and embedded line breaks.
    """
    vocabulary = set(names)
    if "漏光" in vocabulary:
        vocabulary.add("模型衔接地面处异常反光")
    if not vocabulary or not text.strip():
        return {}
    alternatives = "|".join(re.escape(name) for name in sorted(vocabulary, key=len, reverse=True))
    token = re.compile(rf"(?P<name>{alternatives})(?:\((?P<sub>[^)]*)\))?(?=\s*(?::|、|$))")
    boundary = re.compile(rf"、\s*(?=(?:{alternatives})(?:\([^)]*\))?\s*(?::|、|$))")
    decoder = json.JSONDecoder()
    items: dict[str, ParsedTag] = {}
    position = 0
    while position < len(text):
        while position < len(text) and (text[position].isspace() or text[position] == "、"):
            position += 1
        match = token.match(text, position)
        if match is None:
            # Unknown segments remain opaque; do not discover tags inside them.
            next_boundary = boundary.search(text, position)
            if next_boundary is None:
                break
            position = next_boundary.end()
            continue
        name = normalize_tag_name(match.group("name"))
        sub = normalize_sub_value(name, match.group("sub") or "") or None
        position = match.end()
        while position < len(text) and text[position].isspace():
            position += 1
        note = ""
        if position < len(text) and text[position] == ":":
            position += 1
            while position < len(text) and text[position].isspace():
                position += 1
            quoted = False
            if position < len(text) and text[position] == '"':
                try:
                    value, end = decoder.raw_decode(text, position)
                    remainder = text[end:].lstrip()
                    if isinstance(value, str) and (not remainder or remainder.startswith("、")):
                        note, position, quoted = value, end, True
                except ValueError:
                    pass  # Legacy notes may begin with a literal quote.
            if not quoted:
                next_boundary = boundary.search(text, position)
                end = next_boundary.start() if next_boundary else len(text)
                note, position = text[position:end].strip(), end
        items[name] = {"check": True, "text": note, "sub": sub}
    return items
