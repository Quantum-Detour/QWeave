"""Basic Bell circuits shared by the three processor models."""

from dataclasses import dataclass

import networkx as nx
from qiskit import QuantumCircuit

from .processors import Processor, get_processor
from .routing import RoutingInfo
from .bell_routing import route_bell_preparation
from .costs import BackendOperationCosts


@dataclass(frozen=True)
class BellCircuit:
    processor: Processor
    route: tuple[int, ...]
    circuit: QuantumCircuit
    routing: RoutingInfo


def build_ideal_bell_circuit(*, measure: bool = True) -> QuantumCircuit:
    """Two-logical-qubit reference, separate from physical routing methods."""
    circuit = QuantumCircuit(2, 2 if measure else 0, name="ideal_bell")
    circuit.h(0)
    circuit.cx(0, 1)
    if measure:
        circuit.measure(0, 0)
        circuit.measure(1, 1)
    return circuit


def build_bell_circuit(
    processor: str | Processor, *, measure: bool = True,
    algorithm: str = "shortest_path", seed: int = 42,
    costs: BackendOperationCosts | None = None,
    training_shots: int = 3072,
) -> BellCircuit:
    """Prepare a Bell pair from all-zero inputs at fixed physical output ports.

    ``route`` is the deterministic shortest reference path, not SABRE's trace.
    Actual inserted/restoration SWAPs are recorded in ``routing``.
    """
    if isinstance(processor, str):
        processor = get_processor(processor)

    port_a, port_b = processor.output_ports
    graph = processor.graph()
    if port_a == port_b or not all(port in graph for port in (port_a, port_b)):
        raise ValueError(f"Invalid output ports for {processor.name}: {processor.output_ports}")
    try:
        route = min(tuple(path) for path in nx.all_shortest_paths(graph, port_a, port_b))
    except nx.NetworkXNoPath as exc:
        raise ValueError(f"Output ports are disconnected on {processor.name}") from exc

    logical = QuantumCircuit(processor.num_qubits, name=f"bell_{processor.name}")
    logical.compose(build_ideal_bell_circuit(measure=False), qubits=processor.output_ports, inplace=True)
    circuit, routing = route_bell_preparation(logical, processor, algorithm=algorithm, seed=seed,
                                              costs=costs, training_shots=training_shots)
    if measure:
        from .measurements import build_bell_measurement_circuits
        circuit = build_bell_measurement_circuits(circuit, processor.output_ports)["ZZ"]
    return BellCircuit(processor=processor, route=route, circuit=circuit, routing=routing)
