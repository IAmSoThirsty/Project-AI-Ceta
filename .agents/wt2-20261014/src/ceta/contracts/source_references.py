"""Exact working reference resolution; no authority or source adoption is issued."""
from dataclasses import dataclass
import hashlib

from .wire import ContractError, strict_loads

PROFILE = "ceta-codex-handoff-reference-map-v1"
MAP_SHA256 = "7311708cdd0a8e32a7ddb648e214be6bc91fe3ccd4c770331c727b3484523e99"
SCHEMA_SHA256 = "036909b7fec542b60ecc7bb5c472bf7779ed612b8f869dbd60c02b759de84fda"
REFERENCE = "../schemas/handoff_record.md"
GUIDE_PREFIX = "sources/codex/canonical_text/02_AGENT_ROLES/EXPECTED_OUTPUT_CONTRACTS/"


@dataclass(frozen=True)
class ResolvedSourceReference:
    guide_path: str
    guide_sha256: str
    original_reference: str
    working_material_path: str
    schema_sha256: str
    schema_bytes: bytes
    status: str = "WORKING_REFERENCE_RESOLVED_ORIGINAL_AUTHOR_INTENT_NOT_ESTABLISHED"


class WorkingReferenceMap:
    """An injected engineering mapping. Its own receipt remains independently bound."""

    def __init__(self, mapping_wire: bytes) -> None:
        if type(mapping_wire) is not bytes or hashlib.sha256(mapping_wire).hexdigest() != MAP_SHA256:
            raise ContractError("REFERENCE_MAP_COMMITMENT_MISMATCH")
        mapping = strict_loads(mapping_wire)
        if type(mapping) is not dict or mapping.get("profile") != PROFILE:
            raise ContractError("UNSUPPORTED_REFERENCE_MAP")
        schema = mapping.get("schema")
        guides = mapping.get("guides")
        if (type(schema) is not dict or schema.get("sha256") != SCHEMA_SHA256
                or schema.get("bytes") != 493 or type(guides) is not list or len(guides) != 21):
            raise ContractError("REFERENCE_MAP_BINDING_MISMATCH")
        material = schema.get("working_material_path")
        if (type(material) is not str or material != "contracts/reference_material/handoff_record.source.md"):
            raise ContractError("UNSUPPORTED_REFERENCE_MATERIAL_PATH")
        rows = {}
        witnesses = set()
        for guide in guides:
            if type(guide) is not dict:
                raise ContractError("INVALID_REFERENCE_MAP_GUIDE")
            path = guide.get("path")
            digest = guide.get("sha256")
            if (type(path) is not str or not path.startswith(GUIDE_PREFIX)
                    or "\\" in path or ".." in path.split("/")
                    or type(digest) is not str or len(digest) != 64
                    or any(c not in "0123456789abcdef" for c in digest)
                    or guide.get("original_reference") != REFERENCE
                    or type(guide.get("witness")) is not int):
                raise ContractError("INVALID_REFERENCE_MAP_GUIDE")
            if path in rows or guide["witness"] in witnesses:
                raise ContractError("DUPLICATE_REFERENCE_MAP_GUIDE")
            rows[path] = digest
            witnesses.add(guide["witness"])
        if witnesses != set(range(37, 58)):
            raise ContractError("REFERENCE_MAP_WITNESS_SET_MISMATCH")
        self._guides = tuple(sorted(rows.items()))
        self._material = material

    def resolve(self, guide_path: str, guide_wire: bytes, schema_wire: bytes) -> ResolvedSourceReference:
        guides = dict(self._guides)
        if type(guide_path) is not str or guide_path not in guides:
            raise ContractError("UNMAPPED_SOURCE_REFERENCE")
        if type(guide_wire) is not bytes or type(schema_wire) is not bytes:
            raise ContractError("REFERENCE_BYTES_REQUIRED")
        digest = hashlib.sha256(guide_wire).hexdigest()
        if digest != guides[guide_path]:
            raise ContractError("GUIDE_SOURCE_COMMITMENT_MISMATCH")
        if len(schema_wire) != 493 or hashlib.sha256(schema_wire).hexdigest() != SCHEMA_SHA256:
            raise ContractError("SCHEMA_SOURCE_COMMITMENT_MISMATCH")
        try:
            text = guide_wire.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise ContractError("INVALID_GUIDE_UTF8") from exc
        if text.count(REFERENCE) != 1:
            raise ContractError("SOURCE_REFERENCE_LITERAL_MISMATCH")
        return ResolvedSourceReference(guide_path, digest, REFERENCE, self._material,
                                       SCHEMA_SHA256, schema_wire)
