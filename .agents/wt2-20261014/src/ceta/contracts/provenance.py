"""Exact source and maturity namespaces; presence does not issue authority."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
from .wire import ContractError


@dataclass(frozen=True)
class SourceReference:
    namespace: str
    original_id: str
    commitment: str


class ProvenanceCatalog:
    """Injected source identities and label sets, frozen at construction.

    The composition owner authenticates the catalog bytes. This pure resolver
    rejects invented/rebound references; it cannot adopt a source or promote an
    implementation from one evidence state to another.
    """
    def __init__(self, sources: Mapping[str, Mapping[str, str]],
                 maturity_scales: Mapping[str, tuple[str, ...]]):
        self._sources = {namespace: dict(items) for namespace, items in sources.items()}
        self._scales = {namespace: frozenset(labels) for namespace, labels in maturity_scales.items()}

    def validate_source(self, reference: SourceReference) -> SourceReference:
        if type(reference) is not SourceReference:
            raise ContractError("UNSUPPORTED_SOURCE_REFERENCE")
        if any(type(value) is not str or not value for value in
               (reference.namespace, reference.original_id, reference.commitment)):
            raise ContractError("UNSUPPORTED_SOURCE_REFERENCE")
        entries = self._sources.get(reference.namespace)
        if entries is None:
            raise ContractError("UNSUPPORTED_SOURCE_NAMESPACE")
        commitment = entries.get(reference.original_id)
        if commitment is None:
            raise ContractError("UNSUPPORTED_ORIGINAL_IDENTIFIER")
        if reference.commitment != commitment:
            raise ContractError("SOURCE_COMMITMENT_MISMATCH")
        return reference

    def validate_maturity(self, namespace: str, label: str) -> tuple[str, str]:
        if type(namespace) is not str or type(label) is not str:
            raise ContractError("UNSUPPORTED_MATURITY_REFERENCE")
        labels = self._scales.get(namespace)
        if labels is None:
            raise ContractError("UNSUPPORTED_MATURITY_NAMESPACE")
        if label not in labels:
            raise ContractError("UNSUPPORTED_MATURITY_LABEL")
        return namespace, label

    def require_same_scale(self, left: tuple[str, str], right: tuple[str, str]) -> None:
        if any(type(value) is not tuple or len(value) != 2 for value in (left, right)):
            raise ContractError("UNSUPPORTED_MATURITY_REFERENCE")
        self.validate_maturity(*left)
        self.validate_maturity(*right)
        if left[0] != right[0]:
            raise ContractError("MATURITY_SCALES_NOT_COMPARABLE")
