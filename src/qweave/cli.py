"""Small command-line entry point for inspecting the first circuit scaffold."""

import argparse
from math import isclose

from .circuits import build_bell_circuit
from .measurements import build_bell_measurement_circuits, run_bell_measurements
from .processors import PROCESSORS
from .verification import BELL_FIDELITY_TOLERANCE, bell_fidelity


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and verify noiseless Bell baselines")
    parser.add_argument("--processor", choices=("all", *PROCESSORS), default="all")
    parser.add_argument("--show-circuit", action="store_true")
    parser.add_argument("--shots", type=int, default=3072, help="Total shots per processor across XX/YY/ZZ (default: 3072)")
    parser.add_argument("--seed", type=int, default=42, help="Simulator seed (default: 42)")
    args = parser.parse_args()
    if args.shots < 3:
        parser.error("--shots must be at least 3")
    if not 0 <= args.seed <= 2**32 - 3:
        parser.error("--seed must be between 0 and 2**32 - 3")

    names = PROCESSORS if args.processor == "all" else (args.processor,)
    failed = False
    for name in names:
        built = build_bell_circuit(name, measure=False)
        print(f"{name}: {built.processor.num_qubits} sites, ports {built.processor.output_ports}")
        print(f"  route: {' -> '.join(map(str, built.route))}")
        try:
            fidelity = bell_fidelity(built.circuit, built.processor.output_ports)
        except ValueError as exc:
            print(f"  verification error: {exc}")
            failed = True
            continue
        passed = isclose(fidelity, 1.0, abs_tol=BELL_FIDELITY_TOLERANCE, rel_tol=0.0)
        failed |= not passed
        print(f"  ideal Bell fidelity: {fidelity:.12f} — {'PASS' if passed else 'FAIL'}")

        result = run_bell_measurements(
            built.circuit, built.processor.output_ports, shots=args.shots, seed=args.seed
        )
        print(f"  noiseless measurements: {args.shots} total shots; seed: {args.seed}")
        for basis, correlation in result.correlations.items():
            print(f"  <{basis}>: {correlation:+.6f}; shots: {result.shots_by_basis[basis]}; counts: {result.counts[basis]}")
        print(f"  measured Bell fidelity (1 + XX - YY + ZZ) / 4: {result.fidelity:.12f}")
        for basis, measured in build_bell_measurement_circuits(
            built.circuit, built.processor.output_ports
        ).items():
            print(f"  {basis} gates: {dict(measured.count_ops())}; depth: {measured.depth()}")
            if args.show_circuit:
                print(measured.draw(output="text", fold=100))
    if failed:
        raise SystemExit(1)
