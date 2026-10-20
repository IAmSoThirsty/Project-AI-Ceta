"""Immutable graph compilation inputs; graph data never grants execution rights."""
from dataclasses import dataclass
import hashlib
import re

from .store_transactions import commitment, identifier
from .wire import ContractError, canonical_bytes, strict_loads


FRAGMENT_PROFILE = "ceta-graph-fragment-v1"
GRAPH_PROFILE = "ceta-compiled-graph-v1"
MAX_GRAPH_BYTES = 4 * 1024 * 1024
MAX_SOURCES = 64
MAX_NODES = 1024
MAX_EDGES = 8192
RELATIONS = frozenset({"DEPENDENCY", "COMMUNICATION", "REVIEW", "AUTHORIZATION", "EVIDENCE"})
KINDS = frozenset({"AGENT", "REVIEW", "GATE", "HUMAN", "INTEGRATION"})
ACCESS = frozenset({"READ", "WRITE", "EXECUTE", "RELEASE"})
_PATH_PART = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_. -]{0,119}")
_RESERVED = frozenset({"CON", "PRN", "AUX", "NUL", *["COM" + str(i) for i in range(1, 10)],
                       *["LPT" + str(i) for i in range(1, 10)]})


def require(value, code):
    if value is not True:
        raise ContractError(code)


def graph_hash(domain, wire):
    require(type(wire) is bytes, "GRAPH_BYTES_REQUIRED")
    return "sha256:" + hashlib.sha256(domain + b"\0" + wire).hexdigest()


def graph_path(value):
    require(type(value) is str and 0 < len(value) <= 1024, "GRAPH_SOURCE_PATH")
    parts = value.split("/")
    require(len(parts) <= 16 and all(_PATH_PART.fullmatch(part) and not part.endswith((".", " "))
        and part.split(".")[0].upper() not in _RESERVED for part in parts), "GRAPH_SOURCE_PATH")


def resource(value, *, scope_id):
    require(type(value) is dict and set(value) == {"resource_id", "revision", "access", "scope_id"},
        "GRAPH_RESOURCE_FIELDS")
    identifier(value["resource_id"])
    require(value["scope_id"] == scope_id, "GRAPH_RESOURCE_SCOPE")
    require(type(value["access"]) is str and value["access"] in ACCESS, "GRAPH_RESOURCE_ACCESS")
    if value["revision"] is not None:
        commitment(value["revision"])
    return dict(value)


def resources(values, *, scope_id):
    require(type(values) is list and len(values) <= 4096, "GRAPH_RESOURCES_BOUND")
    result = [resource(row, scope_id=scope_id) for row in values]
    keys = [(row["resource_id"], row["access"]) for row in result]
    require(len(set(keys)) == len(keys), "GRAPH_RESOURCE_DUPLICATE")
    return sorted(result, key=lambda row: (row["resource_id"], row["access"]))


def node_spec(value, *, scope_id):
    require(type(value) is dict and set(value) ==
        {"node_id", "kind", "role", "proposal_ref", "scope_resources"}, "GRAPH_NODE_FIELDS")
    identifier(value["node_id"])
    require(type(value["kind"]) is str and value["kind"] in KINDS, "GRAPH_NODE_KIND")
    require(type(value["role"]) is str and 0 < len(value["role"]) <= 4096, "GRAPH_NODE_ROLE")
    if value["proposal_ref"] is not None:
        identifier(value["proposal_ref"])
    return {**value, "scope_resources": resources(value["scope_resources"], scope_id=scope_id)}


@dataclass(frozen=True, slots=True)
class GraphSource:
    """Exact bounded source bytes selected by an explicit discovery owner."""
    relative_path: str
    wire: bytes

    def __post_init__(self):
        graph_path(self.relative_path)
        require(type(self.wire) is bytes and 0 < len(self.wire) <= 1024 * 1024,
            "GRAPH_SOURCE_BYTES_BOUND")
        require(type(strict_loads(self.wire)) is dict, "GRAPH_FRAGMENT_OBJECT_REQUIRED")

    @property
    def sha256(self):
        return hashlib.sha256(self.wire).hexdigest()


@dataclass(frozen=True, slots=True)
class GraphScopeCeiling:
    """A captured caller ceiling. Its shape does not authenticate the caller."""
    scope_id: str
    resources_wire: bytes

    def __post_init__(self):
        identifier(self.scope_id)
        require(type(self.resources_wire) is bytes, "GRAPH_CEILING_BYTES_REQUIRED")
        parsed = strict_loads(self.resources_wire)
        checked = resources(parsed, scope_id=self.scope_id)
        require(canonical_bytes(checked) == self.resources_wire, "GRAPH_CEILING_NOT_CANONICAL")

    @classmethod
    def capture(cls, scope_id, values):
        return cls(scope_id, canonical_bytes(resources(values, scope_id=scope_id)))


@dataclass(frozen=True, slots=True)
class CompiledGraph:
    """An inspectable compilation result requiring revalidation at each consumer.

    The immutable definition and original fragments remain available. No state,
    receipt, executor, permit or authority supplied by a fragment is accepted.
    """
    graph_id: str
    scope: GraphScopeCeiling
    sources: tuple[GraphSource, ...]
    definition_wire: bytes
    fingerprint: str
    plan_node_wires: tuple[bytes, ...]

    def __post_init__(self):
        identifier(self.graph_id)
        require(type(self.scope) is GraphScopeCeiling, "GRAPH_CEILING_REQUIRED")
        GraphScopeCeiling(self.scope.scope_id, self.scope.resources_wire)
        require(type(self.sources) is tuple and 1 <= len(self.sources) <= MAX_SOURCES,
            "GRAPH_SOURCE_COUNT")
        captured = []
        for item in self.sources:
            require(type(item) is GraphSource, "GRAPH_SOURCE_TYPE")
            captured.append(GraphSource(item.relative_path, item.wire))
        require(sum(len(item.wire) for item in captured) <= MAX_GRAPH_BYTES, "GRAPH_BYTES_BOUND")
        object.__setattr__(self, "sources", tuple(captured))
        require(type(self.definition_wire) is bytes and 0 < len(self.definition_wire) <= MAX_GRAPH_BYTES,
            "GRAPH_DEFINITION_BOUND")
        commitment(self.fingerprint)
        require(graph_hash(b"CETA:compiled-graph:v1", self.definition_wire) == self.fingerprint,
            "GRAPH_FINGERPRINT_MISMATCH")
        require(type(self.plan_node_wires) is tuple and 1 <= len(self.plan_node_wires) <= MAX_NODES
            and all(type(row) is bytes and 0 < len(row) <= 1024 * 1024 for row in self.plan_node_wires),
            "GRAPH_PLAN_NODE_BOUND")


__all__ = ["GraphSource", "GraphScopeCeiling", "CompiledGraph", "FRAGMENT_PROFILE", "GRAPH_PROFILE"]
