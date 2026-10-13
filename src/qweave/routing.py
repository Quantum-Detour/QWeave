"""Interchangeable SWAP routers with one fixed-placement restoration policy."""

from dataclasses import dataclass
from time import perf_counter

import networkx as nx
from qiskit import QuantumCircuit
from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import SabreSwap

from .processors import Processor


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
    placement_policy: str = "identity; restore all logical sites by reversing inserted SWAPs"
    benchmark: str = "fixed-port-logical-bell-v2"


def _shortest_path(circuit: QuantumCircuit, processor: Processor, seed: int) -> QuantumCircuit:
    graph = processor.graph()
    routed = circuit.copy_empty_like()
    positions = list(range(circuit.num_qubits))
    occupants = list(range(circuit.num_qubits))
    for item in circuit.data:
        logical = [circuit.find_bit(q).index for q in item.qubits]
        if len(logical) == 2:
            a, b = (positions[q] for q in logical)
            path = min(tuple(p) for p in nx.all_shortest_paths(graph, a, b))
            # Move the second operand towards the first, stopping at its neighbor.
            for source, destination in zip(path[:1:-1], path[-2:0:-1]):
                routed.swap(source, destination)
                occupants[source], occupants[destination] = occupants[destination], occupants[source]
                positions[occupants[source]] = source
                positions[occupants[destination]] = destination
        routed.append(item.operation, [positions[q] for q in logical])
    return routed


def _sabre(circuit: QuantumCircuit, processor: Processor, seed: int) -> QuantumCircuit:
    # Adjacency routing is shared with shortest path. Native directions are
    # handled subsequently by the same backend compiler for both algorithms.
    manager = PassManager(SabreSwap(
        processor.synthetic_coupling_map(), heuristic="decay", seed=seed, trials=1,
    ))
    return manager.run(circuit)


ROUTERS = {"shortest_path": _shortest_path, "sabre": _sabre}


def route_circuit(
    circuit: QuantumCircuit, processor: Processor, *, algorithm: str = "shortest_path", seed: int = 42,
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
    graph = processor.graph()
    for item in circuit.data:
        if len(item.qubits) == 2:
            a, b = (circuit.find_bit(q).index for q in item.qubits)
            if not nx.has_path(graph, a, b):
                raise ValueError(f"Interaction sites {a}, {b} are disconnected on {processor.name}")
    started = perf_counter()
    raw = ROUTERS[algorithm](circuit.copy(), processor, seed)
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
    return physical, RoutingInfo(
        algorithm=algorithm, seed=seed,
        heuristic="decay" if algorithm == "sabre" else None,
        trials=1 if algorithm == "sabre" else None,
        initial_layout=identity, routed_layout=layout, final_layout=identity,
        routing_swaps=tuple(swaps), restoration_swaps=restoration,
        runtime_seconds=perf_counter() - started,
    )
