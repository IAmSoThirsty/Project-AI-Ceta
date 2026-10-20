"""Bounded, integer-only canonical wire profile for the supplied 20 records.

This implements the exact schema vocabulary used by the packaged contracts.
Unsupported schema keywords are rejected at construction, never ignored.
It validates shapes only. Authentication, policy, freshness, signatures,
current read sets, and legal state transitions belong to their trusted owners.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import re
import unicodedata
from typing import Any

MAX_WIRE_BYTES = 1024 * 1024
MAX_DEPTH = 32
MIN_INTEGER = -(2**63)
MAX_INTEGER = 2**63 - 1
PROFILE = "ceta-json-integer-nfc-v1"
UNICODE_VERSION = "15.0.0"
_DATE_TIME = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]"
    r"(?:\.[0-9]{1,9})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])"
)
_KEYWORDS = frozenset({
    "$schema", "$id", "$defs", "$ref", "title", "description", "type",
    "properties", "required", "additionalProperties", "anyOf", "oneOf",
    "const", "enum", "items", "minItems", "maxItems", "minLength",
    "maxLength", "minimum", "maximum", "pattern", "format",
})


class ContractError(ValueError):
    """Deterministic rejection without copying sensitive input into errors."""

    def __init__(self, code: str, path: str = "$") -> None:
        self.code, self.path = code, path
        super().__init__(f"{code} at {path}")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError("DUPLICATE_KEY")
        result[key] = value
    return result


def _not_integer(_: str) -> Any:
    raise ContractError("NON_INTEGER_NUMBER")


def _preflight(text: str) -> None:
    depth, quoted, escaped = 0, False, False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > MAX_DEPTH:
                raise ContractError("DEPTH_LIMIT")
        elif char in "]}":
            depth -= 1
    # The JSON parser, after this allocation bound, checks syntactic balance.


def _tree(value: Any, depth: int = 0) -> None:
    if depth == 0 and unicodedata.unidata_version != UNICODE_VERSION:
        raise ContractError("UNSUPPORTED_UNICODE_VERSION")
    if depth > MAX_DEPTH:
        raise ContractError("DEPTH_LIMIT")
    kind = type(value)
    if value is None or kind is bool:
        return
    if kind is int:
        if not MIN_INTEGER <= value <= MAX_INTEGER:
            raise ContractError("INTEGER_RANGE")
    elif kind is str:
        try:
            value.encode("utf-8", errors="strict")
        except UnicodeError as exc:
            raise ContractError("INVALID_UNICODE") from exc
        if unicodedata.normalize("NFC", value) != value:
            raise ContractError("NON_CANONICAL_UNICODE")
    elif kind is list:
        for item in value:
            _tree(item, depth + 1)
    elif kind is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise ContractError("NON_STRING_KEY")
            _tree(key, depth + 1)
            _tree(item, depth + 1)
    else:
        raise ContractError("UNSUPPORTED_VALUE")


def strict_loads(wire: bytes) -> Any:
    if type(wire) is not bytes:
        raise ContractError("WIRE_MUST_BE_BYTES")
    if len(wire) > MAX_WIRE_BYTES:
        raise ContractError("WIRE_SIZE_LIMIT")
    try:
        text = wire.decode("utf-8", errors="strict")
        _preflight(text)
        result = json.loads(text, object_pairs_hook=_pairs,
                            parse_float=_not_integer, parse_constant=_not_integer)
    except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError("MALFORMED_JSON") from exc
    _tree(result)
    return result


def canonical_bytes(value: Any) -> bytes:
    _tree(value)
    wire = json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(wire) > MAX_WIRE_BYTES:
        raise ContractError("WIRE_SIZE_LIMIT")
    return wire


@dataclass(frozen=True)
class ParsedRecord:
    """Original and canonical bytes are separate immutable evidence cuts."""

    record_type: str
    record_id: str
    original_wire: bytes
    canonical_wire: bytes
    original_sha256: str
    commitment: str

    def as_dict(self) -> dict[str, Any]:
        return json.loads(self.canonical_wire)


def _schema_bound_types(shape: Any, depth: int = 0) -> None:
    """Classify malformed bounds before integer-only schema serialization.

    Traverse schema positions only: literal values in const/enum are records,
    not nested schemas. References and all remaining validation stay in the
    compiler after the schema has been copied through canonical serialization.
    """
    if depth > MAX_DEPTH:
        raise ContractError("DEPTH_LIMIT")
    if type(shape) is not dict:
        return
    for field in ("minimum", "maximum", "minItems", "maxItems", "minLength", "maxLength"):
        if field in shape and type(shape[field]) is not int:
            raise ContractError("INVALID_SCHEMA_BOUND")
    for group in ("properties", "$defs"):
        children = shape.get(group)
        if type(children) is dict:
            for child in children.values():
                _schema_bound_types(child, depth + 2)
    if "items" in shape:
        _schema_bound_types(shape["items"], depth + 1)
    for group in ("anyOf", "oneOf"):
        children = shape.get(group)
        if type(children) is list:
            for child in children:
                _schema_bound_types(child, depth + 2)


class RecordCodec:
    """An injected schema avoids filesystem or domain dependencies in core."""

    def __init__(self, schema: dict[str, Any]) -> None:
        _schema_bound_types(schema)
        self._schema = strict_loads(canonical_bytes(schema))
        self._compile(self._schema)
        self._definitions = self._schema.get("$defs", {})
        if len(self._definitions) != 20:
            raise ContractError("RECORD_SET_MISMATCH")
        refs = self._schema.get("oneOf", [])
        if {r.get("$ref") for r in refs} != {"#/$defs/" + n for n in self._definitions} or len(refs) != 20:
            raise ContractError("RECORD_DISPATCH_MISMATCH")
        for name, shape in self._definitions.items():
            properties = shape.get("properties", {})
            if (shape.get("type") != "object" or shape.get("additionalProperties") is not False
                    or set(shape.get("required", [])) != set(properties)
                    or properties.get("record_type", {}).get("const") != name
                    or properties.get("schema_version", {}).get("const") != "1"):
                raise ContractError("NON_STRICT_RECORD_SCHEMA")

    def _compile(self, shape: dict[str, Any], references: tuple[str, ...] = ()) -> None:
        if type(shape) is not dict or set(shape) - _KEYWORDS:
            raise ContractError("UNSUPPORTED_SCHEMA_KEYWORD")
        for group in ("properties", "$defs"):
            if group in shape and type(shape[group]) is not dict:
                raise ContractError("INVALID_SCHEMA_STRUCTURE")
        for group in ("anyOf", "oneOf", "enum"):
            if group in shape and (type(shape[group]) is not list or not shape[group]):
                raise ContractError("INVALID_SCHEMA_STRUCTURE")
        if "required" in shape:
            required = shape["required"]
            if (type(required) is not list or any(type(item) is not str for item in required)
                    or len(set(required)) != len(required)):
                raise ContractError("INVALID_SCHEMA_STRUCTURE")
        if "additionalProperties" in shape and type(shape["additionalProperties"]) is not bool:
            raise ContractError("INVALID_SCHEMA_STRUCTURE")
        for lower, upper, kind in (("minimum", "maximum", "integer"),
                                   ("minItems", "maxItems", "array"),
                                   ("minLength", "maxLength", "string")):
            for field in (lower, upper):
                if field in shape and (type(shape[field]) is not int or shape.get("type") != kind):
                    raise ContractError("INVALID_SCHEMA_BOUND")
                if field in shape and kind != "integer" and shape[field] < 0:
                    raise ContractError("INVALID_SCHEMA_BOUND")
            if lower in shape and upper in shape and shape[lower] > shape[upper]:
                raise ContractError("INVALID_SCHEMA_BOUND")
        if "$ref" in shape:
            ref = shape["$ref"]
            if type(ref) is not str or not ref.startswith("#/$defs/") or ref[8:] not in self._schema.get("$defs", {}):
                raise ContractError("UNSUPPORTED_SCHEMA_REFERENCE")
            if ref in references:
                raise ContractError("CYCLIC_SCHEMA_REFERENCE")
            self._compile(self._schema["$defs"][ref[8:]], references + (ref,))
        if "type" in shape and (type(shape["type"]) is not str or
                shape["type"] not in {"null", "object", "array", "string", "integer", "boolean"}):
            raise ContractError("UNSUPPORTED_SCHEMA_TYPE")
        if "format" in shape and shape["format"] != "date-time":
            raise ContractError("UNSUPPORTED_SCHEMA_FORMAT")
        if "pattern" in shape:
            try:
                re.compile(shape["pattern"])
            except (TypeError, re.error) as exc:
                raise ContractError("INVALID_SCHEMA_PATTERN") from exc
        for group in ("properties", "$defs"):
            for child in shape.get(group, {}).values():
                self._compile(child, references)
        if "items" in shape:
            self._compile(shape["items"], references)
        for group in ("anyOf", "oneOf"):
            for child in shape.get(group, []):
                self._compile(child, references)

    def _check(self, value: Any, shape: dict[str, Any], path: str) -> None:
        if "$ref" in shape:
            self._check(value, self._definitions[shape["$ref"][8:]], path)
        for group in ("anyOf", "oneOf"):
            if group not in shape:
                continue
            successes = 0
            for choice in shape[group]:
                try:
                    self._check(value, choice, path)
                    successes += 1
                except ContractError:
                    pass
            if successes < 1 or (group == "oneOf" and successes != 1):
                raise ContractError("SCHEMA_ALTERNATIVE", path)
        for key in ("const", "enum"):
            if key not in shape:
                continue
            choices = [shape[key]] if key == "const" else shape.get(key, [])
            if not any(type(value) is type(c) and value == c for c in choices):
                raise ContractError("SCHEMA_VALUE", path)
        kinds = {"null": type(None), "object": dict, "array": list,
                 "string": str, "integer": int, "boolean": bool}
        if "type" in shape and type(value) is not kinds[shape["type"]]:
            raise ContractError("SCHEMA_TYPE", path)
        if type(value) is dict:
            properties = shape.get("properties", {})
            if not set(shape.get("required", [])).issubset(value):
                raise ContractError("MISSING_FIELD", path)
            if shape.get("additionalProperties") is False and set(value) - set(properties):
                raise ContractError("UNKNOWN_FIELD", path)
            for name, child in properties.items():
                if name in value:
                    self._check(value[name], child, path + "/" + name)
        elif type(value) is list:
            if len(value) < shape.get("minItems", 0) or len(value) > shape.get("maxItems", MAX_WIRE_BYTES):
                raise ContractError("ARRAY_BOUND", path)
            for index, item in enumerate(value):
                if "items" in shape:
                    self._check(item, shape["items"], f"{path}/{index}")
        elif type(value) is str:
            if len(value) < shape.get("minLength", 0) or len(value) > shape.get("maxLength", MAX_WIRE_BYTES):
                raise ContractError("STRING_BOUND", path)
            if "pattern" in shape and not re.fullmatch(shape["pattern"], value):
                raise ContractError("STRING_PATTERN", path)
            if "format" in shape:
                try:
                    if not _DATE_TIME.fullmatch(value):
                        raise ValueError
                    datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError as exc:
                    raise ContractError("INVALID_DATE_TIME", path) from exc
        elif type(value) is int:
            if value < shape.get("minimum", MIN_INTEGER) or value > shape.get("maximum", MAX_INTEGER):
                raise ContractError("INTEGER_BOUND", path)

    def decode(self, wire: bytes) -> ParsedRecord:
        value = strict_loads(wire)
        if (type(value) is not dict or type(value.get("record_type")) is not str
                or value["record_type"] not in self._definitions):
            raise ContractError("UNKNOWN_RECORD_TYPE")
        shape = self._definitions[value["record_type"]]
        self._check(value, shape, "$")
        canonical = canonical_bytes(value)
        domain = ("CETA:record:" + PROFILE + ":" + value["record_type"] + "\0").encode("ascii")
        return ParsedRecord(value["record_type"], value["record_id"], wire, canonical,
                            "sha256:" + hashlib.sha256(wire).hexdigest(),
                            "sha256:" + hashlib.sha256(domain + canonical).hexdigest())
