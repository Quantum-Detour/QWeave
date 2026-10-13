"""Basic Bell circuits shared by the three processor models."""

from dataclasses import dataclass

import networkx as nx
from qiskit import QuantumCircuit

from .processors import Processor, get_processor


@dataclass(frozen=True)
class BellCircuit:
    processor: Processor
    route: tuple[int, ...]
    circuit: QuantumCircuit


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
    processor: str | Processor, *, measure: bool = True
) -> BellCircuit:
    """Prepare a Bell pair at the selected physical output ports.

    The first output qubit stays at port A. The second is created beside it,
    then moved through initially clean sites by explicit SWAPs. Among shortest
    paths, the lexicographically smallest sequence of site IDs wins.
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

    circuit = QuantumCircuit(
        processor.num_qubits, 2 if measure else 0, name=f"bell_{processor.name}"
    )
    circuit.h(port_a)
    circuit.cx(route[0], route[1])
    for source, destination in zip(route[1:-1], route[2:]):
        circuit.swap(source, destination)
    if measure:
        circuit.measure(port_a, 0)
        circuit.measure(port_b, 1)
    return BellCircuit(processor=processor, route=route, circuit=circuit)
