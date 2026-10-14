"""Interchangeable SWAP routers with one fixed-placement restoration policy."""

from dataclasses import dataclass
from math import isfinite
from time import perf_counter

import networkx as nx
from qiskit import QuantumCircuit
from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import SabreSwap

from .processors import Processor
from .costs import BackendOperationCosts


@dataclass(frozen=True)
class RoutingInfo:
    algorithm: str
    seed: int
    heuristic: str | None
    trials: int | None
    initial_layout: tuple[int, ...]
    routed_layout: tuple[int, ...]  # logical index -> physical site before restoration
    final_layout: tuple[int, ...]
    routing_swaps: tuple[tuple[int, int], ...]
    restoration_swaps: tuple[tuple[int, int], ...]
    runtime_seconds: float
    cost_model: str | None = None
    cost_backend_fingerprint: str | None = None
    cost_compiler_settings: dict | None = None
    cost_preparation_seconds: float = 0.0
    estimated_routing_cost: float | None = None
    cost_decisions: tuple[dict, ...] = ()
    placement_policy: str = "identity; restore all logical sites by reversing inserted SWAPs"
    benchmark: str = "fixed-port-logical-bell-v2"
    protection: dict | None = None
    movement_audit: dict | None = None


def _route_with_selector(circuit: QuantumCircuit, select_path):
    """Shared placement tracking and gate emission for path-based routers."""
    routed = circuit.copy_empty_like()
    positions = list(range(circuit.num_qubits))
    occupants = list(range(circuit.num_qubits))
    decisions = []
    for item in circuit.data:
        logical = [circuit.find_bit(q).index for q in item.qubits]
        if len(logical) == 2:
            a, b = (positions[q] for q in logical)
            transport, decision = select_path(a, b)
            if decision is not None:
                decisions.append(decision)
            for source, destination in zip(transport, transport[1:]):
                routed.swap(source, destination)
                occupants[source], occupants[destination] = occupants[destination], occupants[source]
                positions[occupants[source]] = source
                positions[occupants[destination]] = destination
        routed.append(item.operation, [positions[q] for q in logical])
    return routed, tuple(decisions)


def _shortest_path(circuit, processor, seed, costs=None):
    graph = processor.graph()

    def select(a, b):
        path = min(tuple(p) for p in nx.all_shortest_paths(graph, a, b))
        return tuple(reversed(path[1:])), None

    return _route_with_selector(circuit, select)


def _noise_aware(circuit, processor, seed, costs):
    adjacency = processor.graph()

    def select(a, b):
        # Ordered SWAP arguments must agree with emitted instructions. The
        # restoration wrapper reverses their sequence, not their arguments.
        transport_graph = nx.DiGraph()
        transport_graph.add_nodes_from(sorted(set(adjacency) - {a}))
        for u in sorted(transport_graph):
            for v in sorted(adjacency[u]):
                if v == a:
                    continue
                weight = 2 * costs.operation("swap", u, v).cost
                if isfinite(weight):
                    transport_graph.add_edge(u, v, cost=weight)
        distances, paths = nx.single_source_dijkstra(transport_graph, b, weight="cost")
        candidates = []
        for neighbor in sorted(adjacency[a]):
            cx = costs.operation("cx", a, neighbor)
            if neighbor in distances and isfinite(cx.cost):
                path = tuple(paths[neighbor])
                candidates.append((distances[neighbor] + cx.cost, len(path) - 1, path, cx))
        if not candidates:
            raise ValueError(f"No finite-cost route for CX({a}, {b}) on {processor.name}")
        total, _, path, cx = min(candidates, key=lambda candidate: candidate[:3])
        swaps = [costs.operation("swap", u, v).record() for u, v in zip(path, path[1:])]
        return path, {
            "operands": (a, b), "transport_path": path,
            "cx": cx.record(), "transport_swaps": swaps,
            "restoration_swaps": list(reversed(swaps)), "total_cost": total,
        }

    return _route_with_selector(circuit, select)


def _sabre(circuit: QuantumCircuit, processor: Processor, seed: int, costs=None):
    # Adjacency routing is shared with shortest path. Native directions are
    # handled subsequently by the same backend compiler for both algorithms.
    manager = PassManager(SabreSwap(
        processor.synthetic_coupling_map(), heuristic="decay", seed=seed, trials=1,
    ))
    return manager.run(circuit), ()


ROUTERS = {"shortest_path": _shortest_path, "sabre": _sabre, "noise_aware": _noise_aware}
# QMRP is a Bell-specific protection transform, dispatched before generic routing.
ROUTERS["qmrp"] = None
ALGORITHM_IDS = {"shortest_path": "A", "sabre": "B", "noise_aware": "C", "qmrp": "D"}


def route_circuit(
    circuit: QuantumCircuit, processor: Processor, *, algorithm: str = "shortest_path", seed: int = 42,
    costs: BackendOperationCosts | None = None,
) -> tuple[QuantumCircuit, RoutingInfo]:
    """Route a unitary H/CX preparation and restore its original physical layout.

    Input SWAPs are excluded so every SWAP in the router output represents a
    placement change. Restoration is physical, charged to both cost and noise.
    This deliberately scoped interface does not yet accept arbitrary uploads.
    """
    if algorithm not in ROUTERS:
        raise ValueError(f"Unknown routing algorithm {algorithm!r}; choose one of {tuple(ROUTERS)}")
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**32:
        raise ValueError("Routing seed must be an integer between 0 and 2**32 - 1")
    if circuit.num_qubits != processor.num_qubits or circuit.num_clbits:
        raise ValueError("Routing requires a full-width circuit without classical bits")
    if any(item.operation.name not in {"h", "cx"} for item in circuit.data):
        raise ValueError("Current routing input supports only H and CX preparation gates")
    if algorithm == "qmrp":
        from .protection import route_qmrp_bell
        return route_qmrp_bell(circuit, processor, seed=seed, costs=costs)
    graph = processor.graph()
    for item in circuit.data:
        if len(item.qubits) == 2:
            a, b = (circuit.find_bit(q).index for q in item.qubits)
            if not nx.has_path(graph, a, b):
                raise ValueError(f"Interaction sites {a}, {b} are disconnected on {processor.name}")
    if algorithm == "noise_aware":
        if costs is None:
            raise ValueError("noise_aware requires backend-derived operation costs")
        costs.validate_processor(processor)
    else:
        costs = None
    preparation_before = costs.preparation_seconds if costs else 0.0
    started = perf_counter()
    raw, decisions = ROUTERS[algorithm](circuit.copy(), processor, seed, costs)
    # Copy instructions into a physical circuit without stale transpiler layout metadata.
    physical = QuantumCircuit(processor.num_qubits, name=f"{circuit.name}_{algorithm}")
    physical.global_phase = raw.global_phase
    swaps = []
    occupants = list(range(processor.num_qubits))
    for item in raw.data:
        sites = tuple(raw.find_bit(q).index for q in item.qubits)
        if len(sites) == 2 and not graph.has_edge(*sites):
            raise ValueError(f"Router emitted unsupported interaction {sites}")
        physical.append(item.operation, sites)
        if item.operation.name == "swap":
            a, b = sites
            swaps.append((a, b))
            occupants[a], occupants[b] = occupants[b], occupants[a]
    layout = tuple(occupants.index(q) for q in range(processor.num_qubits))
    restoration = tuple(reversed(swaps))
    for a, b in restoration:
        physical.swap(a, b)
        occupants[a], occupants[b] = occupants[b], occupants[a]
    identity = tuple(range(processor.num_qubits))
    if tuple(occupants) != identity:
        raise ValueError("Output restoration did not recover the initial placement")
    preparation_seconds = costs.preparation_seconds - preparation_before if costs else 0.0
    return physical, RoutingInfo(
        algorithm=algorithm, seed=seed,
        heuristic="decay" if algorithm == "sabre" else None,
        trials=1 if algorithm == "sabre" else None,
        initial_layout=identity, routed_layout=layout, final_layout=identity,
        routing_swaps=tuple(swaps), restoration_swaps=restoration,
        runtime_seconds=max(0.0, perf_counter() - started - preparation_seconds),
        cost_preparation_seconds=preparation_seconds,
        cost_model=costs.model if costs else None,
        cost_compiler_settings=getattr(costs, "compiler_settings", None) if costs else None,
        cost_backend_fingerprint=costs.backend_fingerprint if costs else None,
        estimated_routing_cost=sum(d["total_cost"] for d in decisions) if costs else None,
        cost_decisions=decisions,
    )
