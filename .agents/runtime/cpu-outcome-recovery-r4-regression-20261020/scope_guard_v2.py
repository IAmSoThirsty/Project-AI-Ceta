"""SQLite URI observer: resolve only local file URIs inside the owned verification root."""
from pathlib import Path
from urllib.parse import urlsplit
from nturl2path import url2pathname
import os

def sqlite_contained(value, root):
    try:
        text = os.fsdecode(value)
        if text.startswith('file:'):
            parsed = urlsplit(text)
            if parsed.scheme != 'file' or parsed.netloc or parsed.fragment:
                return False
            text = url2pathname(parsed.path)
            if not Path(text).is_absolute():
                return False
        elif urlsplit(text).scheme and not (len(text) > 2 and text[1:3] in (':/', ':\\')):
            return False
        if '\x00' in text:
            return False
        return Path(text).resolve().is_relative_to(root.resolve())
    except (TypeError, ValueError, OSError):
        return False
