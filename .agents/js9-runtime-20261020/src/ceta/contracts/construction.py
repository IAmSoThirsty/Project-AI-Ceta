"""Deterministic package construction and gate checklists; no qualification.

Dependency edges determine construction order. Gate membership determines
acceptance obligations. Neither this pure model nor caller-supplied completion
claims permit runtime kickoff, cutover, publication, or a formal gate change.
"""
from dataclasses import dataclass
import hashlib

from .wire import ContractError, strict_loads

MODEL_PROFILE = "ceta-construction-gate-assessment-v1"
_WP_SHA = "2b573de7550336aae7c671e69bb49fa9011889513fec792967f0ed3286819017"
_GATE_SHA = "04afba11afa8a707ac70651d2ef26efed65d75b0d6d6edde44c2399c2a36848b"
_PACKAGE_IDS = tuple("WP-" + str(i).zfill(2) for i in range(28))
_GATE_IDS = tuple("G-" + c for c in "ABCDEFGH")


def _bound_json(raw: bytes, expected_sha: str):
    if type(raw) is not bytes or hashlib.sha256(raw).hexdigest() != expected_sha:
        raise ContractError("CONSTRUCTION_SOURCE_IDENTITY_MISMATCH")
    return strict_loads(raw)


def topological_order(dependencies: tuple[tuple[str, tuple[str, ...]], ...]) -> tuple[str, ...]:
    """Validate a bounded graph and choose the lexically first ready ID.

    This checks graph structure only, not source identity or permission.
    ConstructionPlan additionally binds the full authoritative source bytes.
    """
    if type(dependencies) is not tuple or not 1 <= len(dependencies) <= 256:
        raise ContractError("INVALID_CONSTRUCTION_GRAPH")
    graph = {}
    for row in dependencies:
        if (type(row) is not tuple or len(row) != 2
                or type(row[0]) is not str or not 1 <= len(row[0]) <= 160
                or type(row[1]) is not tuple or len(row[1]) > 256
                or any(type(dep) is not str or not 1 <= len(dep) <= 160 for dep in row[1])):
            raise ContractError("INVALID_CONSTRUCTION_GRAPH")
        name, deps = row
        if name in graph:
            raise ContractError("DUPLICATE_CONSTRUCTION_NODE")
        if len(set(deps)) != len(deps):
            raise ContractError("DUPLICATE_CONSTRUCTION_DEPENDENCY")
        graph[name] = deps
    if any(dep not in graph for deps in graph.values() for dep in deps):
        raise ContractError("UNKNOWN_CONSTRUCTION_DEPENDENCY")
    ordered = []
    completed = set()
    while len(ordered) < len(graph):
        ready = sorted(name for name, deps in graph.items()
                       if name not in completed and set(deps) <= completed)
        if not ready:
            raise ContractError("CONSTRUCTION_DEPENDENCY_CYCLE")
        chosen = ready[0]
        ordered.append(chosen)
        completed.add(chosen)
    return tuple(ordered)


@dataclass(frozen=True)
class WorkPackage:
    package_id: str
    title: str
    path: str
    dependencies: tuple[str, ...]
    component_owners: tuple[str, ...]
    requirement_ids: tuple[str, ...]
    acceptance_ids: tuple[str, ...]
    target_gate: str
    implementation_status: str
    review_status: str
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class Gate:
    gate_id: str
    name: str
    members: tuple[str, ...]
    acceptance: str
    recorded_state: str
    recorded_evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class GateAssessment:
    gate_id: str
    members: tuple[str, ...]
    dependency_closure: tuple[str, ...]
    missing_members: tuple[str, ...]
    missing_dependencies: tuple[str, ...]
    acceptance_evidence_established_under_supplied_inputs: bool
    candidate_satisfied: bool
    acceptance: str
    implementation_status: str = "IMPLEMENTED_NOT_QUALIFIED"
    gate_qualified: bool = False
    runtime_authorized: bool = False


@dataclass(frozen=True, init=False)
class ConstructionPlan:
    packages: tuple[WorkPackage, ...]
    gates: tuple[Gate, ...]
    order: tuple[str, ...]
    source_hashes: tuple[tuple[str, str], ...]

    def __init__(self, work_packages: bytes, gates: bytes) -> None:
        source_wp = _bound_json(work_packages, _WP_SHA)
        source_gates = _bound_json(gates, _GATE_SHA)
        packages = tuple(WorkPackage(
            p["id"], p["title"], p["path"], tuple(p["depends_on"]),
            tuple(p["component_owners"]), tuple(p["requirement_ids"]),
            tuple(p["acceptance_ids"]), p["target_gate"],
            p["implementation_status"], p["review_status"], tuple(p["evidence_refs"]))
            for p in source_wp["packages"])
        gate_rows = tuple(Gate(g["id"], g["name"], tuple(g["required_work_packages"]),
                               g["acceptance"], g["state"], tuple(g["evidence_refs"]))
                          for g in source_gates["gates"])
        if (tuple(p.package_id for p in packages) != _PACKAGE_IDS
                or tuple(g.gate_id for g in gate_rows) != _GATE_IDS):
            raise ContractError("CONSTRUCTION_FULL_SCOPE_REQUIRED")
        members = [name for gate in gate_rows for name in gate.members]
        if len(members) != 28 or set(members) != set(_PACKAGE_IDS):
            raise ContractError("GATE_MEMBERSHIP_COVERAGE_MISMATCH")
        assignments = {name: gate.gate_id for gate in gate_rows for name in gate.members}
        if any(p.target_gate != assignments[p.package_id] for p in packages):
            raise ContractError("GATE_TARGET_MISMATCH")
        order = topological_order(tuple((p.package_id, p.dependencies) for p in packages))
        object.__setattr__(self, "packages", packages)
        object.__setattr__(self, "gates", gate_rows)
        object.__setattr__(self, "order", order)
        object.__setattr__(self, "source_hashes", (
            ("build/work_packages.json", _WP_SHA), ("build/gates.json", _GATE_SHA)))

    def _completed(self, completed_packages: tuple[str, ...]) -> set[str]:
        if (type(completed_packages) is not tuple or len(completed_packages) > 28
                or any(type(name) is not str or name not in _PACKAGE_IDS
                       for name in completed_packages)
                or len(set(completed_packages)) != len(completed_packages)):
            raise ContractError("INVALID_COMPLETED_PACKAGE_CLAIMS")
        return set(completed_packages)

    def construction_ready(self, completed_packages: tuple[str, ...]) -> tuple[str, ...]:
        """Readiness under unauthenticated claims; not authority to start work."""
        completed = self._completed(completed_packages)
        graph = {p.package_id: p.dependencies for p in self.packages}
        if any(not set(graph[name]) <= completed for name in completed):
            raise ContractError("INCOHERENT_COMPLETED_PACKAGE_CLAIMS")
        return tuple(p.package_id for p in self.packages
                     if p.package_id not in completed and set(p.dependencies) <= completed)

    def gate(self, gate_id: str) -> Gate:
        for gate in self.gates:
            if gate.gate_id == gate_id:
                return gate
        raise ContractError("UNKNOWN_CONSTRUCTION_GATE")

    def dependency_closure(self, package_ids: tuple[str, ...]) -> tuple[str, ...]:
        selected = self._completed(package_ids)
        graph = {p.package_id: p.dependencies for p in self.packages}
        expanded = set(selected)
        pending = list(selected)
        while pending:
            for dependency in graph[pending.pop()]:
                if dependency not in expanded:
                    expanded.add(dependency)
                    pending.append(dependency)
        return tuple(name for name in self.order if name in expanded)

    def assess_gate(self, gate_id: str, completed_packages: tuple[str, ...],
                    acceptance_evidence_verified: bool,
                    evidence_refs: tuple[str, ...]) -> GateAssessment:
        """Retain the exact gate acceptance body, including non-package duties.

        Evidence truth/configuration/independence is not verified in this leaf.
        All-positive fixture inputs still confer no formal gate qualification.
        """
        completed = self._completed(completed_packages)
        gate = self.gate(gate_id)
        if (type(acceptance_evidence_verified) is not bool
                or type(evidence_refs) is not tuple or len(evidence_refs) > 128
                or any(type(ref) is not str or not 1 <= len(ref) <= 1024 for ref in evidence_refs)
                or len(set(evidence_refs)) != len(evidence_refs)):
            raise ContractError("INVALID_GATE_EVIDENCE_CLAIMS")
        closure = self.dependency_closure(gate.members)
        missing_members = tuple(name for name in gate.members if name not in completed)
        missing_deps = tuple(name for name in closure
                             if name not in completed and name not in gate.members)
        established = acceptance_evidence_verified and bool(evidence_refs)
        return GateAssessment(
            gate.gate_id, gate.members, closure, missing_members, missing_deps,
            established, not missing_members and not missing_deps and established,
            gate.acceptance)

