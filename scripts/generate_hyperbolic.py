"""Regenerate the frozen provisional {7,3} cell-adjacency benchmark.

Run with: uv run python scripts/generate_hyperbolic.py
This deliberately overwrites the benchmark artifact; review its diff before
comparing new results with an earlier graph fingerprint.
"""

from collections import Counter
from importlib.metadata import version
import json
from pathlib import Path

from hypertiling import HyperbolicTiling
import networkx as nx


parameters = {"p": 7, "q": 3, "n": 4, "kernel": "SRS", "center": "cell"}
tiling = HyperbolicTiling(**parameters)
neighbors = [set(map(int, row)) for row in tiling.get_nbrs_list()]
for a, row in enumerate(neighbors):
    if a in row or any(b < 0 or b >= len(tiling) or a not in neighbors[b] for b in row):
        raise ValueError("Expected reciprocal cell adjacency without self-loops")
edges = sorted((a, b) for a, row in enumerate(neighbors) for b in row if a < b)
graph = nx.Graph()
graph.add_nodes_from(range(len(tiling)))
graph.add_edges_from(edges)
if not nx.is_connected(graph) or max(dict(graph.degree()).values()) != parameters["p"]:
    raise ValueError("Expected a connected cell graph with maximum degree p")
distances = dict(nx.all_pairs_shortest_path_length(graph))
diameter = max(max(row.values()) for row in distances.values())
ports = min((a, b) for a, row in distances.items() for b, d in row.items() if a < b and d == diameter)
centers = [tiling.get_center(i) for i in range(len(tiling))]
artifact = {
    "schema_version": 1,
    "generator": "hypertiling.HyperbolicTiling",
    "generator_version": version("hypertiling"),
    "parameters": parameters,
    "adjacency_method": "get_nbrs_list() (SRS default radius search)",
    "qubit_placement": "cell centers",
    "coupling_rule": "neighboring cells sharing a polygon edge",
    "interior_degree": 7,
    "status": "provisional project choice; organizer confirmation pending",
    "num_qubits": len(tiling),
    "edges": edges,
    "output_ports": ports,
    "port_selection": "lexicographically smallest pair attaining graph diameter",
    "port_distance": diameter,
    "degree_histogram": dict(sorted(Counter(dict(graph.degree()).values()).items())),
    "poincare_cell_centers": [[float(z.real), float(z.imag)] for z in centers],
    "documentation": "https://gitpages.physik.uni-wuerzburg.de/hypertiling/hyperweb/doc/examples/quickstart.html",
}
output = Path(__file__).resolve().parents[1] / "src/qweave/data/hyperbolic_7_3_cells.json"
output.write_text(json.dumps(artifact, indent=2) + "\n")
print(f"Saved {len(tiling)} cells, {len(edges)} edges, ports {ports}, distance {diameter}: {output}")
