"""Processor connectivity derived from configured offline backends.

Custom graph inputs remain provisional; backend generation supplies native
operations and noise properties, not a verified challenge geometry.
"""

from collections.abc import Mapping, Iterator
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from importlib.resources import files
import json

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


@dataclass(frozen=True)
class ProcessorConfig:
    backend_kind: str
    output_ports: tuple[int, int]
    provenance: str
    num_qubits: int | None = None
    edges: tuple[tuple[int, int], ...] = ()
    topology_metadata: dict | None = None


def _hyperbolic_config() -> ProcessorConfig:
    """Load the frozen lattice; never regenerate or select ports during a run."""
    raw = files("qweave").joinpath("data/hyperbolic_7_3_cells.json").read_bytes()
    artifact = json.loads(raw)
    parameters = artifact["parameters"]
    metadata = {k: v for k, v in artifact.items() if k not in {"edges", "poincare_cell_centers"}}
    metadata["artifact_sha256"] = sha256(raw).hexdigest()
    return ProcessorConfig(
        backend_kind="generic",
        output_ports=tuple(artifact["output_ports"]), num_qubits=artifact["num_qubits"],
        edges=tuple(tuple(edge) for edge in artifact["edges"]),
        provenance=(
            f"HYPERTILING {artifact['generator_version']}; "
            f"{{{parameters['p']},{parameters['q']}}}, {parameters['kernel']}, n={parameters['n']}; "
            f"cell-adjacency graph, interior degree {artifact['interior_degree']}; frozen graph and ports; "
            "provisional project choice, organizer confirmation pending."
        ),
        topology_metadata=metadata,
    )


PROCESSOR_CONFIGS = {
    "five_node": ProcessorConfig(
        backend_kind="generic", output_ports=(0, 4), num_qubits=5,
        edges=((0, 1), (1, 2), (1, 3), (3, 4)),
        provenance="Provisional branching-tree interpretation of the challenge overview.",
    ),
    "five_node_multipath": ProcessorConfig(
        backend_kind="generic", output_ports=(0, 4), num_qubits=5,
        edges=((0, 1), (1, 2), (2, 3), (3, 4), (4, 1)),
        provenance=("Custom five-qubit topology chosen to enable multipath; "
                    "not a confirmed organizer reference. Original tree retained as five_node."),
    ),
    "ibm_heavy_hex": ProcessorConfig(
        backend_kind="sherbrooke", output_ports=(0, 15),
        provenance="FakeSherbrooke from the supplied transpilation notebook; ports remain provisional.",
    ),
    "hyperbolic_inspired": _hyperbolic_config(),
}


# The original tree remains available only by explicit selection.
COMPARISON_PROCESSORS = ("five_node_multipath", "ibm_heavy_hex", "hyperbolic_inspired")

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
