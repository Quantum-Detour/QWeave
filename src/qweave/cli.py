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
from .processors import PROCESSOR_CONFIGS
from .routing import ROUTERS
from .verification import BELL_FIDELITY_TOLERANCE, bell_fidelity


def _print_measurements(label: str, result: BellMeasurementResult) -> None:
    shots = sum(result.shots_by_basis.values())
    print(f"  {label}: {shots} total shots; seed: {result.seed}")
    for basis, correlation in result.correlations.items():
        print(f"    <{basis}>: {correlation:+.6f}; shots: {result.shots_by_basis[basis]}; counts: {result.counts[basis]}")
    print(f"    measured Bell fidelity (1 + XX - YY + ZZ) / 4: {result.fidelity:.12f}")
    low, high = result.fidelity_interval
    print(f"    conservative 95% sampling interval: [{low:.6f}, {high:.6f}]")
    print(f"    accepted: {shots}/{shots} (100%); discarded: 0; unprotected baseline")


def _result_record(result: BellMeasurementResult) -> dict:
    return {
        "counts": result.counts, "correlations": result.correlations,
        "fidelity": result.fidelity, "fidelity_interval": result.fidelity_interval,
        "interval_method": "95% simultaneous Hoeffding bounds",
        "shots_by_basis": result.shots_by_basis, "seed": result.seed,
        "accepted_shots": sum(result.shots_by_basis.values()), "discarded_shots": 0,
        "testbed": asdict(result.testbed) if result.testbed else None,
        "noise": asdict(result.noise) if result.noise else None,
        "circuits": {
            basis: {"qasm3": qasm3.dumps(circuit), "gates": dict(circuit.count_ops()), "depth": circuit.depth()}
            for basis, circuit in result.circuits.items()
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify and compare Bell baselines")
    parser.add_argument("--processor", choices=("all", *PROCESSOR_CONFIGS), default="all")
    parser.add_argument("--algorithm", choices=("all", *ROUTERS), default="all", help="Routing strategy; all compares methods on one shared backend")
    parser.add_argument("--show-circuit", action="store_true", help="Draw executed circuits after SWAP decomposition")
    parser.add_argument("--shots", type=int, default=3072, help="Total shots per algorithm per processor PER noise setting, across XX/YY/ZZ")
    parser.add_argument("--seed", type=int, default=42, help="Simulator seed (default: 42)")
    parser.add_argument("--noise", choices=("none", "backend"), default="none", help="backend uses FakeSherbrooke for IBM and seeded GenericBackendV2 for custom graphs")
    parser.add_argument("--backend-seed", type=int, default=1234, help="Seed for synthetic backend properties, independent of shot sampling (default: 1234)")
    parser.add_argument("--report", type=Path, help="Save configuration, snapshot identity, counts, metrics, and executed QASM circuits as JSON")
    args = parser.parse_args()
    if args.shots < 3:
        parser.error("--shots must be at least 3")
    if not 0 <= args.seed <= 2**32 - 3:
        parser.error("--seed must be between 0 and 2**32 - 3")
    if args.backend_seed < 0:
        parser.error("--backend-seed must be nonnegative")
    names = PROCESSOR_CONFIGS if args.processor == "all" else (args.processor,)
    algorithms = tuple(ROUTERS) if args.algorithm == "all" else (args.algorithm,)
    records = []
    failed = False
    for name in names:
        testbed = FakeBackendTestbed.for_processor(
            name, backend_seed=args.backend_seed, compiler_seed=args.seed,
        )
        print(f"Test bed: {testbed.snapshot.backend_class}; source: {testbed.snapshot.noise_source}; {testbed.snapshot.num_qubits} sites")
        if testbed.snapshot.backend_seed is not None:
            print(f"  synthetic properties seed: {testbed.snapshot.backend_seed}")
        else:
            print(f"  calibration: {testbed.snapshot.calibration_time}")
        print(f"  SHA256: {testbed.snapshot.snapshot_sha256}")
        print("  native compilation: fixed physical placement, optimization level 0; no rerouting or mitigation")
        processor = testbed.processor(PROCESSOR_CONFIGS[name].output_ports, name=name)
        for algorithm in algorithms:
            built = build_bell_circuit(processor, measure=False, algorithm=algorithm, seed=args.seed)
            print(f"{name} / {algorithm}: {built.processor.num_qubits} sites, ports {built.processor.output_ports}")
            print(f"  graph source: {PROCESSOR_CONFIGS[name].provenance}")
            if PROCESSOR_CONFIGS[name].topology_metadata:
                print(f"  topology SHA256: {PROCESSOR_CONFIGS[name].topology_metadata['artifact_sha256']}")
            print(f"  shortest reference path: {' -> '.join(map(str, built.route))}")
            print(f"  routing SWAPs: {built.routing.routing_swaps}")
            print(f"  output-restoration SWAPs: {built.routing.restoration_swaps}")
            print(f"  SWAPs before decomposition: {built.circuit.count_ops().get('swap', 0)}")
            try:
                fidelity = bell_fidelity(built.circuit, built.processor.output_ports)
            except ValueError as exc:
                print(f"  verification error: {exc}")
                failed = True
                continue
            passed = isclose(fidelity, 1.0, abs_tol=BELL_FIDELITY_TOLERANCE, rel_tol=0.0)
            failed |= not passed
            print(f"  ideal Bell fidelity: {fidelity:.12f} — {'PASS' if passed else 'FAIL'}")
            native_fidelity = bell_fidelity(testbed.compile(built.circuit), built.processor.output_ports)
            native_passed = isclose(native_fidelity, 1.0, abs_tol=BELL_FIDELITY_TOLERANCE, rel_tol=0)
            failed |= not native_passed
            print(f"  native circuit ideal fidelity: {native_fidelity:.12f} — {'PASS' if native_passed else 'FAIL'}")

            prepared = prepare_bell_measurements(built.circuit, built.processor.output_ports, testbed=testbed)
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
                print(f"  measured fidelity change (noisy - noiseless): {noisy.fidelity - result.fidelity:+.6f}")
            for basis, measured in result.circuits.items():
                print(f"  {basis} backend native gates: {dict(measured.count_ops())}; depth: {measured.depth()}")
                if args.show_circuit:
                    print(measured.draw(output="text", fold=100, idle_wires=False))
            if args.report:
                records.append({
                    "algorithm": "A" if algorithm == "shortest_path" else "B",
                    "routing": asdict(built.routing),
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
        args.report.write_text(json.dumps({"schema_version": 2, "runs": records}, indent=2) + "\n")
        print(f"Saved report: {args.report}")
    if failed:
        raise SystemExit(1)
