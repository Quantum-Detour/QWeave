"""Inspect and compare ideal and noisy Bell baseline experiments."""

import argparse
from math import isclose

from .circuits import build_bell_circuit
from .measurements import BellMeasurementResult, run_bell_measurements
from .noise import BitFlipNoise
from .processors import PROCESSORS
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify and compare Bell baselines")
    parser.add_argument("--processor", choices=("all", *PROCESSORS), default="all")
    parser.add_argument("--show-circuit", action="store_true", help="Draw executed circuits after SWAP decomposition")
    parser.add_argument("--shots", type=int, default=3072, help="Total shots per processor PER noise setting, across XX/YY/ZZ")
    parser.add_argument("--seed", type=int, default=42, help="Simulator seed (default: 42)")
    parser.add_argument("--noise", choices=("none", "bit-flip"), default="none", help="Compare a noisy run with the noiseless baseline")
    parser.add_argument("--p1", type=float, help="X probability after each one-qubit gate (default: 0.001)")
    parser.add_argument("--p2", type=float, help="Independent X probability per participant after each CX (default: 0.01)")
    parser.add_argument("--readout-error", type=float, help="Symmetric error per measured bit (default: 0.01)")
    args = parser.parse_args()
    if args.shots < 3:
        parser.error("--shots must be at least 3")
    if not 0 <= args.seed <= 2**32 - 3:
        parser.error("--seed must be between 0 and 2**32 - 3")
    noise = None
    if args.noise == "none" and any(p is not None for p in (args.p1, args.p2, args.readout_error)):
        parser.error("Noise probabilities require --noise bit-flip")
    if args.noise == "bit-flip":
        try:
            noise = BitFlipNoise(
                single_qubit=0.001 if args.p1 is None else args.p1,
                two_qubit=0.01 if args.p2 is None else args.p2,
                readout=0.01 if args.readout_error is None else args.readout_error,
            )
        except ValueError as exc:
            parser.error(str(exc))
        print(f"Synthetic independent bit-flip noise: p1={noise.single_qubit}, p2={noise.two_qubit} per CX participant, readout={noise.readout}")

    names = PROCESSORS if args.processor == "all" else (args.processor,)
    failed = False
    for name in names:
        built = build_bell_circuit(name, measure=False)
        print(f"{name}: {built.processor.num_qubits} sites, ports {built.processor.output_ports}")
        print(f"  route: {' -> '.join(map(str, built.route))}")
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

        result = run_bell_measurements(
            built.circuit, built.processor.output_ports, shots=args.shots, seed=args.seed
        )
        _print_measurements("noiseless measurements", result)
        if noise is not None:
            noisy = run_bell_measurements(
                built.circuit, built.processor.output_ports,
                shots=args.shots, seed=args.seed, noise=noise,
            )
            _print_measurements("noisy measurements", noisy)
            print(f"  measured fidelity change (noisy - noiseless): {noisy.fidelity - result.fidelity:+.6f}")
        for basis, measured in result.circuits.items():
            print(f"  {basis} synthetic basis gates: {dict(measured.count_ops())}; depth: {measured.depth()}")
            if args.show_circuit:
                print(measured.draw(output="text", fold=100))
    if failed:
        raise SystemExit(1)
