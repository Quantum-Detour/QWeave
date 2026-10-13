"""Provisional, topology-only processor definitions.

Edges describe physical adjacency. For this first circuit, CX is assumed to
work in either direction on each edge; native directions and costs belong to a
later, explicitly configured experiment suite.
"""

from dataclasses import dataclass

import networkx as nx
from qiskit.transpiler import CouplingMap


@dataclass(frozen=True)
class Processor:
    name: str
    description: str
    num_qubits: int
    edges: tuple[tuple[int, int], ...]
    output_ports: tuple[int, int]
    provenance: str

    def graph(self) -> nx.Graph:
        graph = nx.Graph()
        graph.add_nodes_from(range(self.num_qubits))
        graph.add_edges_from(self.edges)
        return graph

    def synthetic_coupling_map(self) -> CouplingMap:
        """Return both CX directions under the topology-only gate assumption."""
        directed_edges = [direction for a, b in self.edges for direction in ((a, b), (b, a))]
        return CouplingMap(couplinglist=directed_edges)


def _radial_edges() -> tuple[tuple[int, int], ...]:
    """A provisional three-layer radial graph, not a regular tiling."""
    edges: list[tuple[int, int]] = []
    for index in range(7):
        inner = index + 1
        edges.extend(
            (
                (0, inner),
                (inner, (index + 1) % 7 + 1),
                (inner, 8 + 2 * index),
                (inner, 9 + 2 * index),
            )
        )
    edges.extend((outer, 8 + (outer - 7) % 14) for outer in range(8, 22))
    return tuple(edges)


PROCESSORS: dict[str, Processor] = {
    "five_node": Processor(
        name="five_node",
        description="Five-site branching reference",
        num_qubits=5,
        edges=((0, 1), (1, 2), (1, 3), (3, 4)),
        output_ports=(0, 4),
        provenance="Provisional branching-tree interpretation of the challenge overview.",
    ),
    "ibm_heavy_hex": Processor(
        name="ibm_heavy_hex",
        description="16-site IBM-style heavy-hex snapshot",
        num_qubits=16,
        edges=(
            (0, 1), (1, 2), (1, 4), (2, 3), (3, 5), (4, 7),
            (5, 8), (6, 7), (7, 10), (8, 9), (8, 11), (10, 12),
            (11, 14), (12, 13), (12, 15), (13, 14),
        ),
        output_ports=(0, 15),
        provenance="Coupling edges copied from qiskit-ibm-runtime 0.50.0 FakeGuadalupeV2; topology only.",
    ),
    "hyperbolic_inspired": Processor(
        name="hyperbolic_inspired",
        description="22-site radial expansion scaffold",
        num_qubits=22,
        edges=_radial_edges(),
        output_ports=(8, 18),
        provenance="Provisional radial graph with 1+7+14 sites; not a verified hyperbolic tiling.",
    ),
}


def get_processor(name: str) -> Processor:
    """Look up one of the three provisional processor models."""
    try:
        return PROCESSORS[name]
    except KeyError as exc:
        choices = ", ".join(PROCESSORS)
        raise ValueError(f"Unknown processor {name!r}; choose one of: {choices}") from exc
