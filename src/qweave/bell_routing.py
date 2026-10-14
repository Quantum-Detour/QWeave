"""Routing specialized to all-zero Bell preparation with fixed output ports.

Unused zero-state wire identities are not physical output requirements. The
unitary router remains available separately for unknown-input circuits.
"""
from math import isfinite
from time import perf_counter

import networkx as nx
from qiskit import QuantumCircuit

from .routing import RoutingInfo, route_circuit

BELL_BENCHMARK = 'zero-input-fixed-output-bell-v3'
CANDIDATE_LIMIT = 6


def allocate_zero_roles(width, roles):
    """Bind logical roles to indistinguishable zero sites without physical gates."""
    occupants = list(range(width))
    for logical, physical in roles.items():
        old = occupants.index(logical)
        occupants[old], occupants[physical] = occupants[physical], occupants[old]
    return occupants


def layout_of(occupants):
    return tuple(occupants.index(logical) for logical in range(len(occupants)))


def simplify_zero_input_movement(circuit):
    """Remove product-prefix permutations and later provable zero/zero SWAPs.

    H gates before the first CX follow their states through the prefix SWAPs.
    Barriers flush pending gates; after entangling, use conservative zero tracking.
    Never used by the general unknown-input route_circuit interface.
    """
    output = circuit.copy_empty_like()
    pending = [[] for _ in circuit.qubits]
    zero = [True] * circuit.num_qubits
    prefix = True
    removed = []

    def flush():
        for site, gates in enumerate(pending):
            for gate in gates:
                output.append(gate, [site])
            gates.clear()

    for index, item in enumerate(circuit.data):
        sites = [circuit.find_bit(q).index for q in item.qubits]
        name = item.operation.name
        if name == 'barrier':
            flush()
            prefix = False
            output.append(item.operation, sites)
        elif name == 'swap':
            u, v = sites
            if prefix:
                pending[u], pending[v] = pending[v], pending[u]
                removed.append(index)
            elif zero[u] and zero[v]:
                removed.append(index)
            else:
                output.append(item.operation, sites)
            zero[u], zero[v] = zero[v], zero[u]
        elif len(sites) == 1 and name == 'h':
            zero[sites[0]] = False
            if prefix:
                pending[sites[0]].append(item.operation)
            else:
                output.append(item.operation, sites)
        elif name == 'cx':
            flush()
            prefix = False
            u, v = sites
            zero[v] = zero[v] and zero[u]
            output.append(item.operation, sites)
        else:
            raise ValueError('Zero-input movement simplification supports only H/CX/SWAP/barrier')
    flush()
    return output, tuple(removed)


def _outward_path(processor, costs):
    r, d = processor.output_ports
    adjacency = processor.graph()
    graph = nx.DiGraph()
    graph.add_nodes_from(sorted(set(adjacency) - {r}))
    for u in graph:
        for v in sorted(adjacency[u]):
            if v in graph:
                value = costs.operation('swap', u, v).cost
                if isfinite(value):
                    graph.add_edge(u, v, cost=value)
    # Search backwards to get physical outward paths with directed costs.
    distances, reverse_paths = nx.single_source_dijkstra(graph.reverse(copy=False), d, weight='cost')
    candidates = []
    for neighbor in sorted(adjacency[r]):
        cx = costs.operation('cx', r, neighbor)
        if neighbor in distances and isfinite(cx.cost):
            path = tuple(reversed(reverse_paths[neighbor]))
            candidates.append((cx.cost + distances[neighbor], len(path), path, cx))
    if not candidates:
        raise ValueError('No finite-cost outward Bell route')
    total, _, path, cx = min(candidates, key=lambda item: item[:3])
    decision = dict(operands=(r, path[0]), transport_path=path, cx=cx.record(),
                    transport_swaps=[costs.operation('swap', u, v).record()
                                     for u, v in zip(path, path[1:])],
                    restoration_swaps=[], total_cost=total)
    return path, decision


def _bell_path_circuit(processor, path, algorithm='noise_aware'):
    reference, _ = processor.output_ports
    circuit = QuantumCircuit(processor.num_qubits, name=f'bell_{processor.name}_{algorithm}')
    circuit.h(reference)
    circuit.cx(reference, path[0])
    for source, destination in zip(path, path[1:]):
        circuit.swap(source, destination)
    return circuit


def bell_route_candidates(processor, costs):
    """Bounded, deterministic Bell candidates for offline simulation research.

    Production Method C still selects its weighted route with _outward_path.
    This enumerator always includes A and C, then up to four short alternatives.
    """
    reference, destination = processor.output_ports
    graph = processor.graph()
    shortest = min(tuple(p) for p in nx.all_shortest_paths(graph, reference, destination))[1:]
    weighted, _ = _outward_path(processor, costs)
    candidates = {shortest, weighted}
    transport = graph.copy()
    transport.remove_node(reference)
    alternatives = []
    for neighbor in sorted(graph[reference]):
        if not nx.has_path(transport, neighbor, destination):
            continue
        for index, route in enumerate(nx.shortest_simple_paths(transport, neighbor, destination)):
            if index >= 3:
                break
            path = tuple(route)
            if len(path) <= len(shortest) + 2:
                proxy = costs.operation('cx', reference, path[0]).cost + sum(
                    costs.operation('swap', u, v).cost for u, v in zip(path, path[1:]))
                if isfinite(proxy):
                    alternatives.append((len(path), proxy, path))
    for _, _, path in sorted(alternatives):
        if len(candidates) >= CANDIDATE_LIMIT:
            break
        candidates.add(path)
    return dict(reference_path=shortest, weighted_path=weighted,
                paths=tuple(sorted(candidates)))


def route_bell_preparation(logical, processor, *, algorithm, seed, costs=None, training_shots=3072):
    r, d = processor.output_ports
    instructions = [(item.operation.name, tuple(logical.find_bit(q).index for q in item.qubits))
                    for item in logical.data]
    if (logical.num_qubits != processor.num_qubits or logical.num_clbits
            or instructions != [('h', (r,)), ('cx', (r, d))]):
        raise ValueError('Bell routing supports only fixed-port H/CX preparation from all-zero inputs')
    if algorithm == 'qmrp':
        return route_circuit(logical, processor, algorithm=algorithm, seed=seed, costs=costs)
    if algorithm not in {'shortest_path', 'noise_aware', 'noise_aware_mc', 'sabre'}:
        raise ValueError(f'Unknown routing algorithm {algorithm!r}')
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**32:
        raise ValueError('Routing seed must be an integer between 0 and 2**32 - 1')
    started = perf_counter()
    before = costs.preparation_seconds if costs else 0.
    decisions = ()
    if algorithm == 'sabre':
        raw, _ = route_circuit(logical, processor, algorithm=algorithm, seed=seed)
    else:
        if algorithm in {'noise_aware', 'noise_aware_mc'}:
            if costs is None:
                raise ValueError(f'{algorithm} requires backend-derived operation costs')
            costs.validate_processor(processor)
            if algorithm == 'noise_aware_mc':
                if isinstance(training_shots, bool) or not isinstance(training_shots, int) or training_shots < 3:
                    raise ValueError('training_shots must be an integer of at least 3')
                from .measurements import prepare_bell_measurements, sample_bell_measurements
                from numpy.random import SeedSequence
                selection_started = perf_counter()
                candidates = bell_route_candidates(processor, costs)
                seeds = [int(child.generate_state(1)[0]) % (2**32-3)
                         for child in SeedSequence([seed, processor.num_qubits, 0xC0DE]).spawn(len(candidates['paths']))]
                if len({value+i for value in seeds for i in range(3)} | {seed, seed+1, seed+2}) != 3*len(seeds)+3:
                    raise ValueError('Training and evaluation simulator seeds overlap')
                training = []
                compilation_seconds = simulation_seconds = 0.0
                for candidate, simulator_seed in zip(candidates['paths'], seeds):
                    begun = perf_counter()
                    candidate_circuit = _bell_path_circuit(processor, candidate, algorithm)
                    native = costs.testbed.compile(candidate_circuit)
                    measured = prepare_bell_measurements(candidate_circuit, processor.output_ports,
                                                          testbed=costs.testbed)
                    compilation_seconds += perf_counter()-begun
                    native_cost = costs.native_cost_record(native)
                    begun = perf_counter()
                    result = sample_bell_measurements(measured, shots=training_shots,
                            seed=simulator_seed, testbed=costs.testbed, backend_noise=True)
                    elapsed = perf_counter()-begun
                    simulation_seconds += elapsed
                    training.append(dict(path=candidate, seed=simulator_seed,
                        fidelity=result.fidelity, shots_by_basis=result.shots_by_basis,
                        counts=result.counts, simulation_seconds=elapsed,
                        native_gate_cost=native_cost['gate_cost'],
                        native_two_qubit_gates=native_cost['native_two_qubit_gates'],
                        dependency_duration_seconds=native_cost['dependency_duration_seconds']))
                selected = min(training, key=lambda row: (-row['fidelity'],
                               row['native_gate_cost'], row['path']))
                path = selected['path']
                decision = dict(selection_rule='maximum noisy training Bell fidelity; tie by compiled native gate cost, then path',
                    candidate_set=candidates, training=training, selected_path=path,
                    training_shots_per_candidate=training_shots,
                    training_attempted_shots=training_shots*len(training),
                    candidate_compilation_seconds=compilation_seconds,
                    training_simulation_seconds=simulation_seconds,
                    selection_seconds=perf_counter()-selection_started,
                    total_cost=selected['native_gate_cost'],
                    cost_scope='compiled native preparation gate-error proxy; route selected by separate noisy training shots')
            else:
                path, decision = _outward_path(processor, costs)
            decisions = (decision,)
        else:
            path = min(tuple(p) for p in nx.all_shortest_paths(processor.graph(), r, d))[1:]
        raw = _bell_path_circuit(processor, path, algorithm)
    circuit, removed = simplify_zero_input_movement(raw)
    first_cx = next(item for item in circuit.data if item.operation.name == 'cx')
    launch_r, launch_d = [circuit.find_bit(q).index for q in first_cx.qubits]
    occupants = allocate_zero_roles(processor.num_qubits, {r: launch_r, d: launch_d})
    initial = layout_of(occupants)
    swaps = []
    for item in circuit.data:
        if item.operation.name == 'swap':
            u, v = [circuit.find_bit(q).index for q in item.qubits]
            swaps.append((u, v))
            occupants[u], occupants[v] = occupants[v], occupants[u]
    final = layout_of(occupants)
    if final[r] != r or final[d] != d:
        raise ValueError('Simplified Bell routing failed to restore the physical output roles')
    uses_costs = algorithm in {'noise_aware', 'noise_aware_mc'}
    preparation = costs.preparation_seconds-before if costs and uses_costs else 0.
    return circuit, RoutingInfo(
        algorithm=algorithm, seed=seed, heuristic='decay' if algorithm == 'sabre' else None,
        trials=1 if algorithm == 'sabre' else None,
        initial_layout=initial, routed_layout=final, final_layout=final,
        routing_swaps=tuple(swaps), restoration_swaps=(),
        runtime_seconds=max(0., perf_counter()-started-preparation),
        cost_model=('simulation-assisted-noisy-v1' if algorithm == 'noise_aware_mc' else costs.model)
                   if uses_costs else None,
        cost_backend_fingerprint=costs.backend_fingerprint if uses_costs else None,
        cost_compiler_settings=getattr(costs, 'compiler_settings', None) if uses_costs else None,
        cost_preparation_seconds=preparation,
        estimated_routing_cost=decisions[0]['total_cost'] if decisions else None,
        cost_decisions=decisions,
        placement_policy='all-zero input; local Bell allocation; fixed physical output roles; zero workspace identities unrestricted',
        benchmark=BELL_BENCHMARK,
        movement_audit=dict(zero_input=True, local_bell_sites=(launch_r, launch_d),
                            removed_prefix_or_zero_swap_indices=removed,
                            pre_simplification_swaps=int(raw.count_ops().get('swap', 0)),
                            executed_swaps=len(swaps)),
    )
