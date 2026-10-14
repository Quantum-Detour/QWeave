"""Inspect and compare ideal and noisy Bell baseline experiments."""

import argparse
from dataclasses import asdict
import json
from math import isclose
from pathlib import Path

from qiskit import qasm3

from .backends import FakeBackendTestbed
from .circuits import build_bell_circuit
from .measurements import BellMeasurementResult, prepare_bell_measurements, sample_bell_measurements
from .processors import COMPARISON_PROCESSORS, PROCESSOR_CONFIGS
from .routing import ALGORITHM_IDS, ROUTERS
from .costs import BackendOperationCosts
from .settings import OptimizationLevel
from .verification import BELL_FIDELITY_TOLERANCE, bell_fidelity, syndrome_zero_probability


def _print_measurements(label: str, result: BellMeasurementResult) -> None:
    shots = sum(result.shots_by_basis.values())
    accepted = sum(result.accepted_by_basis.values())
    print(f"  {label}: {shots} total shots; seed: {result.seed}")
    for basis, correlation in result.correlations.items():
        value = f"{correlation:+.6f}" if correlation is not None else "undefined"
        print(f"    <{basis}>: {value}; accepted: {result.accepted_by_basis[basis]}/{result.shots_by_basis[basis]}; counts: {result.counts[basis]}")
    if result.fidelity is None:
        print("    measured Bell fidelity: undefined (a basis has zero accepted shots)")
    else:
        print(f"    measured Bell fidelity (1 + XX - YY + ZZ) / 4: {result.fidelity:.12f}")
        low, high = result.fidelity_interval
        print(f"    conservative 95% sampling interval: [{low:.6f}, {high:.6f}]")
    print(f"    accepted: {accepted}/{shots} ({100*accepted/shots:.2f}%); discarded: {shots-accepted}")
    if result.syndrome_sites:
        print(f"    acceptance intervals (95%, per basis): {result.acceptance_intervals}")
        print(f"    same execution without postselection: {result.unconditional_fidelity:.12f}; interval: {result.unconditional_interval}")


def _result_record(result: BellMeasurementResult) -> dict:
    accepted = sum(result.accepted_by_basis.values())
    attempted = sum(result.shots_by_basis.values())
    return {
        "counts": result.counts, "raw_joint_counts": result.raw_counts,
        "correlations": result.correlations,
        "fidelity": result.fidelity, "fidelity_interval": result.fidelity_interval,
        "interval_method": "95% simultaneous Hoeffding bounds on accepted Bell samples",
        "shots_by_basis": result.shots_by_basis, "seed": result.seed,
        "accepted_shots": accepted, "discarded_shots": attempted-accepted,
        "acceptance": accepted/attempted, "accepted_by_basis": result.accepted_by_basis,
        "discarded_by_basis": result.discarded_by_basis,
        "acceptance_intervals": result.acceptance_intervals,
        "acceptance_interval_method": "95% Hoeffding interval per basis",
        "syndrome_sites": result.syndrome_sites,
        "acceptance_rule": "all syndrome bits zero" if result.syndrome_sites else "retain all shots",
        "without_postselection": {"counts": result.unconditional_counts,
            "fidelity": result.unconditional_fidelity, "fidelity_interval": result.unconditional_interval},
        "testbed": asdict(result.testbed) if result.testbed else None,
        "noise": asdict(result.noise) if result.noise else None,
        "circuits": {
            basis: {"qasm3": qasm3.dumps(circuit), "gates": dict(circuit.count_ops()),
                    "depth": circuit.depth(),
                    "native_two_qubit_gates": sum(len(item.qubits) == 2 and item.operation.name != 'barrier'
                                                  for item in circuit.data),
                    "active_qubits": len({circuit.find_bit(q).index for item in circuit.data
                                          if item.operation.name != 'barrier' for q in item.qubits})}
            for basis, circuit in result.circuits.items()
        },
    }


def _print_final_summary(rows: list[dict], *, noise: str) -> None:
    """Summarize the circuits and samples just executed by the CLI."""
    if not rows:
        return
    processor_labels = {
        "five_node_multipath": "Five-node",
        "five_node": "Five-node tree",
        "ibm_heavy_hex": "IBM",
        "hyperbolic_inspired": "Hyperbolic",
    }
    algorithm_labels = {
        "shortest_path": "A: Shortest path",
        "sabre": "B: SABRE",
        "noise_aware": "C: Noise-aware",
        "noise_aware_mc": "C-MC: Simulation-assisted",
        "qmrp": "D: QMRP",
    }
    print(f"\nFinal summary ({'backend noise' if noise == 'backend' else 'noiseless'}; ZZ circuit metrics)")
    print("| Processor | Algorithm | Fidelity | SWAPs | Native 2-qubit gates | Depth | Accepted |")
    print("|---|---|---:|---:|---:|---:|---:|")
    best_by_processor = {
        processor: max((row["fidelity"] for row in rows
                        if row["processor"] == processor and row["fidelity"] is not None),
                       default=None)
        for processor in {row["processor"] for row in rows}
    }
    previous_processor = None
    for row in rows:
        processor = row["processor"]
        label = processor_labels.get(processor, processor) if processor != previous_processor else ""
        fidelity = row["fidelity"]
        displayed_fidelity = "undefined" if fidelity is None else f"{fidelity:.4f}"
        if (fidelity is not None and best_by_processor[processor] is not None
                and isclose(fidelity, best_by_processor[processor], abs_tol=1e-12, rel_tol=0)):
            displayed_fidelity = f"**{displayed_fidelity}**"
        print(f"| {label} | {algorithm_labels[row['algorithm']]} | {displayed_fidelity} | "
              f"{row['swaps']} | {row['native_two_qubit_gates']} | {row['depth']} | "
              f"{row['accepted'] / row['attempted']:.2%} |")
        previous_processor = processor
    print("Fidelity uses accepted XX/YY/ZZ shots; each row uses its own attempted-shot budget.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify and compare Bell baselines")
    parser.add_argument("--processor", choices=("all", *PROCESSOR_CONFIGS), default="all",
                        help="all runs custom five-node, IBM and hyperbolic; five_node selects the archived tree explicitly")
    parser.add_argument("--algorithm", choices=("all", *ROUTERS), default="all", help="Routing strategy; all compares methods on one shared backend")
    parser.add_argument("--show-circuit", action="store_true", help="Draw executed circuits after SWAP decomposition")
    parser.add_argument("--shots", type=int, default=3072, help="Total shots per algorithm per processor PER noise setting, across XX/YY/ZZ")
    parser.add_argument("--seed", type=int, default=42, help="Simulator seed (default: 42)")
    parser.add_argument("--noise", choices=("none", "backend"), default="none", help="backend uses FakeSherbrooke for IBM and seeded GenericBackendV2 for custom graphs")
    parser.add_argument("--backend-seed", type=int, default=1234, help="Seed for synthetic backend properties, independent of shot sampling (default: 1234)")
    parser.add_argument("--optimization", choices=tuple(level.name.lower() for level in OptimizationLevel), default=OptimizationLevel.MAXIMUM.name.lower(), help="Shared native optimization preset (default: maximum, Qiskit level 3)")
    parser.add_argument("--mc-training-shots", type=int, default=3072,
                        help="Noisy training shots per candidate for simulation-assisted C (default: 3072)")
    parser.add_argument("--report", type=Path, help="Save configuration, snapshot identity, counts, metrics, and executed QASM circuits as JSON")
    args = parser.parse_args()
    if args.shots < 3:
        parser.error("--shots must be at least 3")
    if not 0 <= args.seed <= 2**32 - 3:
        parser.error("--seed must be between 0 and 2**32 - 3")
    if args.backend_seed < 0:
        parser.error("--backend-seed must be nonnegative")
    if args.mc_training_shots < 3:
        parser.error("--mc-training-shots must be at least 3")
    if args.algorithm == "noise_aware_mc" and args.noise != "backend":
        parser.error("simulation-assisted C requires --noise backend for route selection and evaluation")
    names = COMPARISON_PROCESSORS if args.processor == "all" else (args.processor,)
    all_algorithms = ("shortest_path", "sabre", "noise_aware", "noise_aware_mc", "qmrp")
    algorithms = (tuple(method for method in all_algorithms
                        if args.noise == "backend" or method != "noise_aware_mc")
                  if args.algorithm == "all" else (args.algorithm,))
    records = []
    summary_rows = []
    failed = False
    for name in names:
        testbed = FakeBackendTestbed.for_processor(
            name, backend_seed=args.backend_seed, compiler_seed=args.seed,
            optimization_level=OptimizationLevel[args.optimization.upper()],
        )
        print(f"Test bed: {testbed.snapshot.backend_class}; source: {testbed.snapshot.noise_source}; {testbed.snapshot.num_qubits} sites")
        if testbed.snapshot.backend_seed is not None:
            print(f"  synthetic properties seed: {testbed.snapshot.backend_seed}")
        else:
            print(f"  calibration: {testbed.snapshot.calibration_time}")
        print(f"  SHA256: {testbed.snapshot.snapshot_sha256}")
        print(f"  native compilation: fixed physical placement, optimization {testbed.snapshot.optimization_name} (level {int(testbed.snapshot.optimization_level)}); no rerouting or mitigation")
        processor = testbed.processor(PROCESSOR_CONFIGS[name].output_ports, name=name)
        costs = BackendOperationCosts(testbed) if set(algorithms) & {"noise_aware", "noise_aware_mc", "qmrp"} else None
        for algorithm in algorithms:
            built = build_bell_circuit(processor, measure=False, algorithm=algorithm, seed=args.seed,
                                      costs=costs, training_shots=args.mc_training_shots)
            print(f"{name} / {algorithm}: {built.processor.num_qubits} sites, ports {built.processor.output_ports}")
            print(f"  graph source: {PROCESSOR_CONFIGS[name].provenance}")
            if PROCESSOR_CONFIGS[name].topology_metadata:
                print(f"  topology SHA256: {PROCESSOR_CONFIGS[name].topology_metadata['artifact_sha256']}")
            print(f"  shortest reference path: {' -> '.join(map(str, built.route))}")
            if built.routing.cost_model:
                print(f"  estimated routing cost (not fidelity): {built.routing.estimated_routing_cost:.8f}")
                print(f"  cost preparation: {built.routing.cost_preparation_seconds:.3f}s; routing: {built.routing.runtime_seconds:.3f}s")
            if algorithm == "noise_aware_mc":
                selection = built.routing.cost_decisions[0]
                print(f"  selected path: {' -> '.join(map(str, selection['selected_path']))}")
                print(f"  route search: {len(selection['training'])} candidates; "
                      f"{selection['training_attempted_shots']} training shots; "
                      f"compilation {selection['candidate_compilation_seconds']:.3f}s; "
                      f"simulation {selection['training_simulation_seconds']:.3f}s")
            print(f"  routing SWAPs: {built.routing.routing_swaps}")
            print(f"  restoration SWAPs (output or encoding workspace): {built.routing.restoration_swaps}")
            print(f"  SWAPs before decomposition: {built.circuit.count_ops().get('swap', 0)}")
            if built.routing.protection:
                protection = built.routing.protection
                print(f"  protection: {protection['status']}; multipath coverage: {protection['coverage']:.0%}")
                if protection.get('reason'):
                    print(f"  fallback reason: {protection['reason']}")
                if protection.get('paths'):
                    print(f"  encoded paths: {protection['paths']}; syndrome: {protection['syndrome_sites']}")
            try:
                fidelity = bell_fidelity(built.circuit, built.processor.output_ports)
                native = testbed.compile(built.circuit)
                native_fidelity = bell_fidelity(native, built.processor.output_ports)
                syndrome_zero = syndrome_zero_probability(built.circuit, built.processor.output_ports)
                native_syndrome_zero = syndrome_zero_probability(native, built.processor.output_ports)
            except ValueError as exc:
                print(f"  verification error: {exc}")
                failed = True
                records.append({"processor": name, "routing_method": algorithm,
                                "status": "simulator_resource_limit" if "resource limit" in str(exc) else "verification_error",
                                "reason": str(exc), "routing": asdict(built.routing)})
                continue
            passed = isclose(fidelity, 1.0, abs_tol=BELL_FIDELITY_TOLERANCE, rel_tol=0.0)
            failed |= not passed
            print(f"  ideal Bell fidelity: {fidelity:.12f} — {'PASS' if passed else 'FAIL'}")
            native_passed = isclose(native_fidelity, 1.0, abs_tol=BELL_FIDELITY_TOLERANCE, rel_tol=0)
            failed |= not native_passed
            print(f"  native circuit ideal fidelity: {native_fidelity:.12f} — {'PASS' if native_passed else 'FAIL'}")

            if built.routing.protection and built.routing.protection.get('syndrome_sites'):
                syndrome_passed = all(isclose(value, 1., abs_tol=BELL_FIDELITY_TOLERANCE, rel_tol=0)
                                      for value in (syndrome_zero, native_syndrome_zero))
                failed |= not syndrome_passed
                print(f"  ideal syndrome-zero probability: {syndrome_zero:.12f}; native: {native_syndrome_zero:.12f} — {'PASS' if syndrome_passed else 'FAIL'}")
            prepared = prepare_bell_measurements(built.circuit, built.processor.output_ports, testbed=testbed)
            cost_audit = None
            if built.routing.cost_model:
                cost_audit = {
                    'routing_estimate': built.routing.estimated_routing_cost,
                    'estimate_scope': ('compiled native preparation gate-error proxy; route selected by separate noisy training shots'
                        if algorithm == 'noise_aware_mc' else
                        'sum of separately compiled CX/SWAP costs; includes QMRP encoding and decoding; excludes H, basis rotations and readout'),
                    'preparation': costs.native_cost_record(native),
                    'measurements': {basis: costs.native_cost_record(circuit)
                                     for basis, circuit in prepared.items()},
                    'interpretation': 'Whole-circuit optimization may change the decomposition. Costs are error proxies, not predicted fidelities.',
                }
                print(f"  compiled preparation gate cost (includes H): {cost_audit['preparation']['gate_cost']:.8f}")
            result = sample_bell_measurements(
                prepared, shots=args.shots, seed=args.seed, testbed=testbed,
            )
            _print_measurements("noiseless measurements", result)
            noisy = None
            if args.noise == "backend":
                noisy = sample_bell_measurements(
                    prepared,
                    shots=args.shots, seed=args.seed,
                    testbed=testbed, backend_noise=True,
                )
                _print_measurements("noisy measurements", noisy)
                if noisy.fidelity is not None and result.fidelity is not None:
                    print(f"  measured fidelity change (noisy - noiseless): {noisy.fidelity - result.fidelity:+.6f}")
            for basis, measured in result.circuits.items():
                print(f"  {basis} backend native gates: {dict(measured.count_ops())}; depth: {measured.depth()}")
                if args.show_circuit:
                    print(measured.draw(output="text", fold=100, idle_wires=False))
            measured_result = noisy if noisy is not None else result
            zz_circuit = measured_result.circuits["ZZ"]
            summary_rows.append({
                "processor": name, "algorithm": algorithm,
                "fidelity": measured_result.fidelity,
                "swaps": int(built.circuit.count_ops().get("swap", 0)),
                "native_two_qubit_gates": sum(
                    len(item.qubits) == 2 and item.operation.name != "barrier"
                    for item in zz_circuit.data
                ),
                "depth": zz_circuit.depth(),
                "accepted": sum(measured_result.accepted_by_basis.values()),
                "attempted": sum(measured_result.shots_by_basis.values()),
            })
            if args.report:
                records.append({
                    "algorithm": ALGORITHM_IDS[algorithm],
                    "status": "completed",
                    "ideal_syndrome_zero_probability": syndrome_zero,
                    "native_ideal_syndrome_zero_probability": native_syndrome_zero,
                    "routing": asdict(built.routing),
                    "native_cost_audit": cost_audit,
                    "routed_preparation_qasm3": qasm3.dumps(built.circuit),
                    "routing_method": algorithm, "processor": name, "num_qubits": built.processor.num_qubits,
                    "ports": built.processor.output_ports, "shortest_reference_path": built.route,
                    "graph_provenance": PROCESSOR_CONFIGS[name].provenance,
                    "edges": built.processor.edges,
                    "topology_metadata": PROCESSOR_CONFIGS[name].topology_metadata,
                    "ideal_fidelity": fidelity, "native_ideal_fidelity": native_fidelity,
                    "noiseless": _result_record(result), "noisy": _result_record(noisy) if noisy else None,
                })
    if args.report:
        args.report.write_text(json.dumps({"schema_version": 4, "runs": records}, indent=2) + "\n")
        print(f"Saved report: {args.report}")
    _print_final_summary(summary_rows, noise=args.noise)
    if failed:
        raise SystemExit(1)
