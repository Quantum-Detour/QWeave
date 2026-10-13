"""Processor connectivity derived from configured offline backends.

Custom graph inputs remain provisional; backend generation supplies native
operations and noise properties, not a verified challenge geometry.
"""

from collections.abc import Mapping, Iterator
from dataclasses import dataclass
from functools import lru_cache

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


@dataclass(frozen=True)
class ProcessorConfig:
    backend_kind: str
    output_ports: tuple[int, int]
    provenance: str
    num_qubits: int | None = None
    edges: tuple[tuple[int, int], ...] = ()


PROCESSOR_CONFIGS = {
    "five_node": ProcessorConfig(
        backend_kind="generic", output_ports=(0, 4), num_qubits=5,
        edges=((0, 1), (1, 2), (1, 3), (3, 4)),
        provenance="Provisional branching-tree interpretation of the challenge overview.",
    ),
    "ibm_heavy_hex": ProcessorConfig(
        backend_kind="sherbrooke", output_ports=(0, 15),
        provenance="FakeSherbrooke from the supplied transpilation notebook; ports remain provisional.",
    ),
    "hyperbolic_inspired": ProcessorConfig(
        backend_kind="generic", output_ports=(8, 18), num_qubits=22,
        edges=_radial_edges(),
        provenance="Provisional radial graph with 1+7+14 sites; not a verified hyperbolic tiling.",
    ),
}


@lru_cache(maxsize=None)
def get_processor(name: str) -> Processor:
    """Derive a default-seed processor from its configured backend."""
    from .backends import FakeBackendTestbed

    testbed = FakeBackendTestbed.for_processor(name)
    return testbed.processor(PROCESSOR_CONFIGS[name].output_ports, name=name)


class _ProcessorCatalog(Mapping[str, Processor]):
    """Preserve catalog lookup while constructing backend-derived models lazily."""

    def __getitem__(self, name: str) -> Processor:
        if name not in PROCESSOR_CONFIGS:
            raise KeyError(name)
        return get_processor(name)

    def __iter__(self) -> Iterator[str]:
        return iter(PROCESSOR_CONFIGS)

    def __len__(self) -> int:
        return len(PROCESSOR_CONFIGS)


PROCESSORS: Mapping[str, Processor] = _ProcessorCatalog()
