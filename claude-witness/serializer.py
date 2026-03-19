"""Safe argument serialization for claude-witness.

Handles generators, ORM entities, circular refs, exceptions, and giant payloads
without crashing. A test run must never fail because of witness serialization.

Rules:
  1. Try json.dumps with a custom fallback.
  2. If that fails or result is too long, fall back to reprlib.repr().
  3. If that fails, return a typed sentinel: <unserializable:TypeName>.
  4. Never raise.
"""

import json
import reprlib
from typing import Any

MAX_STR_LEN = 500
MAX_COLLECTION_ITEMS = 20
MAX_LOCALS_KEYS = 30

_reprizer = reprlib.Repr()
_reprizer.maxstring = MAX_STR_LEN
_reprizer.maxother = MAX_STR_LEN
_reprizer.maxlist = MAX_COLLECTION_ITEMS
_reprizer.maxdict = MAX_COLLECTION_ITEMS
_reprizer.maxtuple = MAX_COLLECTION_ITEMS
_reprizer.maxset = MAX_COLLECTION_ITEMS
_reprizer.maxlong = MAX_STR_LEN
_reprizer.maxlevel = 3


def _json_default(obj: Any) -> Any:
    """Custom JSON encoder for non-standard types."""
    # Generators / iterators — don't consume them
    import types
    if isinstance(obj, (types.GeneratorType, range)):
        return f"<{type(obj).__name__}>"
    # Objects with __dict__ (dataclasses, ORM models, etc.)
    if hasattr(obj, "__dict__"):
        items = list(obj.__dict__.items())[:MAX_COLLECTION_ITEMS]
        return {k: v for k, v in items}
    # Other iterables (sets, custom sequences)
    if hasattr(obj, "__iter__"):
        result = []
        for i, item in enumerate(obj):
            if i >= MAX_COLLECTION_ITEMS:
                result.append(f"...<{type(obj).__name__} truncated>")
                break
            result.append(item)
        return result
    # Bytes
    if isinstance(obj, (bytes, bytearray)):
        return f"<bytes len={len(obj)}>"
    return f"<{type(obj).__name__}>"


def safe_serialize(value: Any) -> Any:
    """Return a JSON-safe representation of value. Never raises."""
    # Fast path for primitives
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        if len(value) <= MAX_STR_LEN:
            return value
        return value[:MAX_STR_LEN] + "...<truncated>"

    # Try full JSON roundtrip
    try:
        text = json.dumps(value, default=_json_default, ensure_ascii=False)
        if len(text) <= MAX_STR_LEN:
            return json.loads(text)
        # Too long — truncate at string level
        return text[:MAX_STR_LEN] + "...<truncated>"
    except Exception:
        pass

    # Fallback: reprlib.repr
    try:
        return f"<repr:{_reprizer.repr(value)}>"
    except Exception:
        pass

    return f"<unserializable:{type(value).__name__}>"


def safe_locals(locals_dict: dict) -> dict:
    """Serialize a frame locals() dict. Skips dunder names and limits size."""
    result = {}
    for k, v in list(locals_dict.items())[:MAX_LOCALS_KEYS]:
        if k.startswith("__"):
            continue
        result[k] = safe_serialize(v)
    return result


def safe_args(frame) -> dict:
    """Serialize positional and keyword arguments from a call frame."""
    args = {}
    try:
        code = frame.f_code
        local_vars = frame.f_locals
        # co_varnames[:co_argcount] = positional args, then keyword-only
        n = code.co_argcount + code.co_kwonlyargcount
        for name in code.co_varnames[:n]:
            if name in local_vars:
                args[name] = safe_serialize(local_vars[name])
    except Exception:
        pass
    return args
