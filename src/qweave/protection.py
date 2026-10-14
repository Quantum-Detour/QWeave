"""Bell-specific repetition encoding and capacity-constrained multipath routing.

This is selective error detection, not recovery or a reproduction of a network
coding/spin-chain protocol. Workspace starts in zero; only Bell ports are outputs.
"""
from dataclasses import replace
from math import isfinite
from time import perf_counter

import networkx as nx
from qiskit import QuantumCircuit

from .routing import RoutingInfo
from .bell_routing import BELL_BENCHMARK, allocate_zero_roles, layout_of, route_bell_preparation, simplify_zero_input_movement

COST_SCALE = 10**12


def _swap_graph(processor, costs, excluded=()):
    graph = nx.DiGraph()
    adjacency = processor.graph()
    graph.add_nodes_from(sorted(set(adjacency) - set(excluded)))
    for u in graph:
        for v in sorted(adjacency[u]):
            if v in graph:
                cost = costs.operation('swap', u, v).cost
                if isfinite(cost):
                    graph.add_edge(u, v, cost=cost)
    return graph


def _encoding_plan(graph, adjacency, a, b, costs):
    transport = graph.copy()
    transport.remove_node(a)
    distances, paths = nx.single_source_dijkstra(transport.reverse(copy=False), b, weight='cost')
    candidates = []
    for n in sorted(adjacency[a]):
        if n not in distances:
            continue
        cx_cost = costs.operation('cx', a, n).cost
        if isfinite(cx_cost):
            path = tuple(reversed(paths[n]))
            candidates.append((distances[n] + cx_cost, len(path), path))
    return min(candidates) if candidates else None


def _flow_paths(graph, launches, arrivals):
    """Integer min-cost flow; hop count breaks ties at rounded cost precision."""
    flow_graph = nx.DiGraph()
    hop_scale = 2 * len(graph) + 1
    for v in sorted(graph):
        flow_graph.add_edge((v, 'in'), (v, 'out'), capacity=1, weight=0)
    for u, v, data in sorted(graph.edges(data=True)):
        weight = round(data['cost'] * COST_SCALE) * hop_scale + 1
        flow_graph.add_edge((u, 'out'), (v, 'in'), capacity=1, weight=weight)
    flow_graph.add_node('source', demand=-2)
    flow_graph.add_node('sink', demand=2)
    for v in launches:
        flow_graph.add_edge('source', (v, 'in'), capacity=1, weight=0)
    for v in arrivals:
        flow_graph.add_edge((v, 'out'), 'sink', capacity=1, weight=0)
    try:
        flow = nx.min_cost_flow(flow_graph)
    except nx.NetworkXUnfeasible:
        return None
    paths = []
    for start in launches:
        path = [start]
        while not flow[(path[-1], 'out')].get('sink', 0):
            next_sites = [node[0] for node, value in flow[(path[-1], 'out')].items()
                          if value and isinstance(node, tuple)]
            if len(next_sites) != 1 or next_sites[0] in path:
                raise ValueError('Invalid transport flow decomposition')
            path.append(next_sites[0])
        paths.append(tuple(path))
    return tuple(paths)


def select_qmrp_plan(processor, costs):
    """Classical search only; no quantum executions are used to choose routes."""
    costs.validate_processor(processor)
    adjacency = processor.graph()
    r, d = processor.output_ports
    graph = _swap_graph(processor, costs, excluded=(r,))
    best = None
    for a in sorted(adjacency[r]):
        if a == d:
            continue
        bell_cost = costs.operation('cx', r, a).cost
        if not isfinite(bell_cost):
            continue
        for b in sorted(set(graph) - {a, d}):
            encoding = _encoding_plan(graph, adjacency, a, b, costs)
            if encoding is None:
                continue
            encode_cost, _, encode_path = encoding
            for s in sorted(adjacency[d]):
                if len({r, a, b, d, s}) != 5:
                    continue
                decode_cost = costs.operation('cx', d, s).cost
                if not isfinite(decode_cost):
                    continue
                paths = _flow_paths(graph, (a, b), (d, s))
                if paths is None:
                    continue
                transport_cost = sum(graph[u][v]['cost'] for path in paths
                                     for u, v in zip(path, path[1:]))
                total = bell_cost + encode_cost + transport_cost + decode_cost
                prep_path = ()
                key = (total, sum(len(p)-1 for p in paths) + len(encode_path)-1,
                       a, b, s, paths)
                plan = dict(launches=(a, b), arrivals=(d, s), paths=paths,
                            preposition_path=prep_path, encoding_path=encode_path,
                            cost=total, cost_breakdown=dict(preposition=0., bell_cx=bell_cost,
                            encoding=encode_cost, transport=transport_cost, decoding=decode_cost))
                if best is None or key < best[0]:
                    best = key, plan
    return best[1] if best else None


def route_qmrp_bell(logical, processor, *, seed, costs):
    r, d = processor.output_ports
    instructions = [(item.operation.name, tuple(logical.find_bit(q).index for q in item.qubits))
                    for item in logical.data]
    if instructions != [('h', (r,)), ('cx', (r, d))]:
        raise ValueError('qmrp currently supports only the fixed-port Bell preparation with zero workspace')
    if costs is None:
        raise ValueError('qmrp requires backend-derived operation costs')
    started = perf_counter()
    before = costs.preparation_seconds
    plan = select_qmrp_plan(processor, costs)
    preparation = costs.preparation_seconds - before
    if plan is None:
        circuit, info = route_bell_preparation(logical, processor, algorithm='shortest_path', seed=seed)
        return circuit, replace(info, algorithm='qmrp',
            runtime_seconds=max(0., perf_counter()-started-preparation),
            cost_preparation_seconds=preparation,
            protection=dict(status='unprotected_fallback', fallback='shortest_path',
                            reason='No finite-cost pair with distinct launch/arrival sites and vertex-disjoint transport',
                            protected_blocks=0, coverage=0.0, syndrome_sites=[]))

    a, b = plan['launches']; _, s = plan['arrivals']
    circuit = QuantumCircuit(processor.num_qubits, name=f'{logical.name}_qmrp')
    phases = []
    swaps = []
    # Allocate zero-state data/ancilla roles where local preparation occurs.
    occupants = allocate_zero_roles(processor.num_qubits,
                                    {r: r, d: a, b: plan['encoding_path'][0]})
    initial_layout = layout_of(occupants)

    def layout():
        return tuple(occupants.index(q) for q in range(processor.num_qubits))

    def emit_swaps(path):
        for u, v in zip(path, path[1:]):
            circuit.swap(u, v)
            swaps.append((u, v))
            occupants[u], occupants[v] = occupants[v], occupants[u]

    def phase(name, emit):
        start = len(circuit.data); initial = layout()
        emit()
        phases.append(dict(name=name, instruction_start=start, instruction_stop=len(circuit.data),
                           wire_placement_before=initial, wire_placement_after=layout()))
        circuit.barrier(label=name)

    phase('bell_preparation', lambda: (circuit.h(r), circuit.cx(r, a)))

    def encode():
        circuit.cx(a, plan['encoding_path'][0])
        emit_swaps(plan['encoding_path'])
    phase('encoding', encode)
    phase('transport', lambda: [emit_swaps(path) for path in plan['paths']])
    phase('decoding', lambda: circuit.cx(d, s))
    wire_layout = layout()
    # Decoding the symmetric code recovers the logical data at d even if the
    # originally data-bearing rail arrived at s. This is code interpretation,
    # not an uncharged physical SWAP. Preserve the wire permutation separately.
    if occupants[d] != d:
        if occupants[s] != d:
            raise ValueError('Encoded data component did not reach either arrival')
        occupants[d], occupants[s] = occupants[s], occupants[d]
    simplified, removed = simplify_zero_input_movement(circuit)
    if removed:
        raise ValueError('QMRP planner retained a redundant zero-input SWAP')
    circuit = simplified
    circuit.metadata = {'qweave_syndrome_sites': [s]}
    protection = dict(status='protected', protected_blocks=1, coverage=1.0,
        coverage_definition='fraction of planned encoded transport blocks protected; preparation is unprotected',
        syndrome_sites=[s], acceptance_rule='all syndrome bits zero', phases=phases,
        **plan, flow_cost_precision=1/COST_SCALE,
        output_roles={'reference': r, 'decoded_data': d, 'syndrome': s},
        component_arrivals=[path[-1] for path in plan['paths']],
        final_wire_permutation=wire_layout,
        decoded_logical_layout=layout(),
        workspace_policy='zero-initialized; wire permutation recorded, encoded components are not independent logical qubits')
    return circuit, RoutingInfo(algorithm='qmrp', seed=seed, heuristic='capacity-one-min-cost-flow', trials=None,
        initial_layout=initial_layout, routed_layout=wire_layout, final_layout=layout(),
        routing_swaps=tuple(swaps), restoration_swaps=(),
        runtime_seconds=max(0., perf_counter()-started-preparation),
        cost_model=costs.model, cost_backend_fingerprint=costs.backend_fingerprint,
        cost_compiler_settings=costs.compiler_settings, cost_preparation_seconds=preparation,
        estimated_routing_cost=plan['cost'], cost_decisions=(plan,),
        placement_policy='all-zero local allocation; fixed Bell output ports; code symmetry permits exchanged arrivals',
        benchmark=BELL_BENCHMARK,
        movement_audit=dict(zero_input=True, preposition_swaps=0, encoding_direction='local CX then one-way ancilla transport',
                            local_bell_sites=(r,a), local_encoding_sites=(a,plan['encoding_path'][0]),
                            executed_swaps=len(swaps)),
        protection=protection)
