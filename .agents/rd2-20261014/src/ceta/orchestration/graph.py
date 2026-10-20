"""Deterministic typed graph compilation over explicitly selected source bytes.

This module has no discovery, persistence, worker or permission side effects.
Source order controls explicit overrides; node and edge order inside a fragment
does not change the effective definition. Original byte hashes remain bound.
"""
from collections import defaultdict
import heapq

from ceta.contracts.graphs import (CompiledGraph, GraphScopeCeiling, GraphSource,
    FRAGMENT_PROFILE, GRAPH_PROFILE, MAX_EDGES, MAX_GRAPH_BYTES, MAX_NODES,
    MAX_SOURCES, RELATIONS, graph_hash, node_spec, require)
from ceta.contracts.store_transactions import commitment, identifier
from ceta.contracts.wire import ContractError, RecordCodec, canonical_bytes, strict_loads


_FRAGMENT_FIELDS = frozenset({"profile", "fragment_id", "graph_id", "scope_id", "nodes", "edges", "overrides"})


def _node_hash(node):
    return graph_hash(b"CETA:graph-node-spec:v1", canonical_bytes(node))


def _order(nodes, edges):
    # Communication is not an execution prerequisite. The other four typed
    # relations remain separately visible but all constrain legal progression.
    incoming = {node: set() for node in nodes}
    outgoing = defaultdict(set)
    for edge in edges:
        if edge["relation"] != "COMMUNICATION":
            incoming[edge["target"]].add(edge["source"])
            outgoing[edge["source"]].add(edge["target"])
    queue = [key for key, parents in incoming.items() if not parents]
    heapq.heapify(queue)
    result = []
    while queue:
        current = heapq.heappop(queue)
        result.append(current)
        for child in sorted(outgoing[current]):
            incoming[child].remove(current)
            if not incoming[child]:
                heapq.heappush(queue, child)
    require(len(result) == len(nodes), "GRAPH_HARD_CYCLE")
    return result


class GraphCompiler:
    """Compile descriptions into schema-checked PENDING PlanNodes.

    The supplied scope ceiling is checked exactly per resource and access mode;
    READ never implies WRITE, EXECUTE or RELEASE. This is a ceiling comparison,
    not authentication or a current policy/admission decision.
    """
    def __init__(self, codec):
        require(type(codec) is RecordCodec, "GRAPH_CODEC_REQUIRED")
        self._codec = RecordCodec(strict_loads(canonical_bytes(codec._schema)))

    def compile(self, sources, *, graph_id, scope_ceiling):
        identifier(graph_id)
        require(type(scope_ceiling) is GraphScopeCeiling, "GRAPH_CEILING_REQUIRED")
        scope = GraphScopeCeiling(scope_ceiling.scope_id, scope_ceiling.resources_wire)
        require(type(sources) is tuple and 1 <= len(sources) <= MAX_SOURCES, "GRAPH_SOURCE_COUNT")
        copied = []
        for item in sources:
            require(type(item) is GraphSource, "GRAPH_SOURCE_TYPE")
            copied.append(GraphSource(item.relative_path, item.wire))
        sources = tuple(copied)
        require(sum(len(item.wire) for item in sources) <= MAX_GRAPH_BYTES, "GRAPH_BYTES_BOUND")
        require(len({source.relative_path.casefold() for source in sources}) == len(sources),
            "GRAPH_DUPLICATE_SOURCE_PATH")
        ceiling = {(row["resource_id"], row["access"]): row["revision"]
            for row in strict_loads(scope.resources_wire)}
        nodes, edges, lineage, fragments = {}, {}, [], set()
        total_nodes, total_edges = 0, 0
        for source in sources:
            document = strict_loads(source.wire)
            require(set(document) == _FRAGMENT_FIELDS, "GRAPH_FRAGMENT_FIELDS")
            require(document["profile"] == FRAGMENT_PROFILE, "GRAPH_FRAGMENT_PROFILE")
            identifier(document["fragment_id"])
            require(document["fragment_id"] not in fragments, "GRAPH_FRAGMENT_DUPLICATE")
            fragments.add(document["fragment_id"])
            require(document["graph_id"] == graph_id and document["scope_id"] == scope.scope_id,
                "GRAPH_FRAGMENT_SCOPE")
            require(type(document["nodes"]) is list and type(document["edges"]) is list
                and type(document["overrides"]) is list, "GRAPH_FRAGMENT_COLLECTIONS")
            total_nodes += len(document["nodes"])
            total_edges += len(document["edges"])
            require(total_nodes <= MAX_NODES and total_edges <= MAX_EDGES
                and len(document["overrides"]) <= len(document["nodes"]), "GRAPH_COLLECTION_BOUND")
            replacements = {}
            for override in document["overrides"]:
                require(type(override) is dict and set(override) == {"node_id", "expected_node_sha256"},
                    "GRAPH_OVERRIDE_FIELDS")
                identifier(override["node_id"])
                commitment(override["expected_node_sha256"])
                require(override["node_id"] not in replacements, "GRAPH_OVERRIDE_DUPLICATE")
                replacements[override["node_id"]] = override["expected_node_sha256"]
            local_ids = set()
            for value in document["nodes"]:
                node = node_spec(value, scope_id=scope.scope_id)
                key = node["node_id"]
                require(key not in local_ids, "GRAPH_NODE_DUPLICATE_IN_FRAGMENT")
                local_ids.add(key)
                for item in node["scope_resources"]:
                    pair = item["resource_id"], item["access"]
                    require(pair in ceiling and (ceiling[pair] is None or ceiling[pair] == item["revision"]),
                        "GRAPH_SCOPE_CEILING_EXCEEDED")
                previous = nodes.get(key)
                if previous is None:
                    require(key not in replacements, "GRAPH_OVERRIDE_WITHOUT_ORIGINAL")
                else:
                    require(key in replacements, "GRAPH_NODE_DUPLICATE_REQUIRES_OVERRIDE")
                    require(_node_hash(previous) == replacements.pop(key), "GRAPH_OVERRIDE_STALE")
                    lineage.append({"node_id": key, "source": source.relative_path,
                        "before": _node_hash(previous), "after": _node_hash(node)})
                nodes[key] = node
            require(not replacements, "GRAPH_OVERRIDE_WITHOUT_REPLACEMENT")
            for edge in document["edges"]:
                require(type(edge) is dict and set(edge) == {"source", "target", "relation"}, "GRAPH_EDGE_FIELDS")
                identifier(edge["source"])
                identifier(edge["target"])
                require(type(edge["relation"]) is str and edge["relation"] in RELATIONS, "GRAPH_EDGE_RELATION")
                require(edge["source"] != edge["target"], "GRAPH_EDGE_SELF_REFERENCE")
                key = edge["source"], edge["target"], edge["relation"]
                require(key not in edges, "GRAPH_EDGE_DUPLICATE")
                edges[key] = dict(edge)
        require(bool(nodes), "GRAPH_EMPTY")
        ordered_edges = [edges[key] for key in sorted(edges)]
        for edge in ordered_edges:
            require(edge["source"] in nodes and edge["target"] in nodes, "GRAPH_EDGE_UNRESOLVED")
            if edge["relation"] == "REVIEW":
                require(nodes[edge["source"]]["kind"] == "REVIEW", "GRAPH_REVIEW_SOURCE_KIND")
        order = _order(nodes, ordered_edges)
        definition = {"profile": GRAPH_PROFILE, "graph_id": graph_id, "scope_id": scope.scope_id,
            "schema_sha256": graph_hash(b"CETA:graph-schema:v1", canonical_bytes(self._codec._schema)),
            "scope_ceiling": strict_loads(scope.resources_wire),
            "sources": [{"relative_path": item.relative_path, "sha256": item.sha256,
                         "bytes": len(item.wire)} for item in sources],
            "nodes": [nodes[key] for key in sorted(nodes)], "edges": ordered_edges,
            "overrides": lineage, "topological_order": order}
        wire = canonical_bytes(definition)
        fingerprint = graph_hash(b"CETA:compiled-graph:v1", wire)
        pending = []
        for key in order:
            node = nodes[key]
            record = {"record_type": "PlanNode", "schema_version": "1",
                "record_id": "plan-node:" + graph_hash(b"CETA:plan-node-id:v1",
                    canonical_bytes([graph_id, scope.scope_id, key, fingerprint])).split(":")[1],
                "scope_id": scope.scope_id, "causation_ref": None, "graph_id": graph_id,
                "graph_fingerprint": fingerprint, **node,
                "dependencies": sorted(edge["source"] for edge in ordered_edges
                    if edge["target"] == key and edge["relation"] == "DEPENDENCY"),
                "state": "PENDING", "executor_session": None, "fence_generation": 0,
                "lease_expires_at": None, "receipt_refs": []}
            raw = canonical_bytes(record)
            self._codec.decode(raw)
            pending.append(raw)
        return CompiledGraph(graph_id, scope, sources, wire, fingerprint, tuple(pending))

    def validate(self, compiled):
        require(type(compiled) is CompiledGraph, "COMPILED_GRAPH_REQUIRED")
        try:
            rebuilt = self.compile(compiled.sources, graph_id=compiled.graph_id, scope_ceiling=compiled.scope)
            require(rebuilt.definition_wire == compiled.definition_wire
                and rebuilt.fingerprint == compiled.fingerprint
                and rebuilt.plan_node_wires == compiled.plan_node_wires, "COMPILED_GRAPH_CHANGED")
        except AttributeError as error:
            raise ContractError("COMPILED_GRAPH_INCOMPLETE") from error
        return rebuilt


__all__ = ["GraphCompiler"]
