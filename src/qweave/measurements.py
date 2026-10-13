"""Shot-based Bell fidelity from separate XX, YY, and ZZ experiments."""

from dataclasses import dataclass
from collections.abc import Mapping

from qiskit import ClassicalRegister, QuantumCircuit
from qiskit_aer import AerSimulator

from .verification import _validate_bell_input

BASES = ("XX", "YY", "ZZ")


@dataclass(frozen=True)
class BellMeasurementResult:
    counts: dict[str, dict[str, int]]
    correlations: dict[str, float]
    fidelity: float
    shots_by_basis: dict[str, int]
    seed: int


def build_bell_measurement_circuits(
    circuit: QuantumCircuit, ports: tuple[int, int]
) -> dict[str, QuantumCircuit]:
    """Copy the preparation and rotate each output into the requested basis.

    Classical bit 0 measures ports[0], bit 1 measures ports[1]. Qiskit count
    strings display bit 1 first; parity is independent of that ordering.
    """
    _validate_bell_input(circuit, ports)
    if circuit.num_clbits:
        raise ValueError("Measurement preparation must have no classical bits")
    circuits = {}
    for basis in BASES:
        measured = circuit.copy(name=f"{circuit.name}_{basis}")
        measured.add_register(ClassicalRegister(2, "bell"))
        for port in ports:
            if basis == "YY":
                measured.sdg(port)
            if basis != "ZZ":
                measured.h(port)
        measured.measure(ports, (0, 1))
        circuits[basis] = measured
    return circuits


def bell_correlations(counts: Mapping[str, Mapping[str, int]]) -> dict[str, float]:
    """Estimate each parity as (N00 + N11 - N01 - N10) / N."""
    if set(counts) != set(BASES):
        raise ValueError("Counts must contain exactly XX, YY, and ZZ")
    correlations = {}
    for basis in BASES:
        outcomes = counts[basis]
        if any(
            key not in {"00", "01", "10", "11"}
            or not isinstance(value, int) or isinstance(value, bool) or value < 0
            for key, value in outcomes.items()
        ):
            raise ValueError("Counts require two-bit outcomes and nonnegative integers")
        shots = sum(outcomes.values())
        if shots == 0:
            raise ValueError(f"Bell fidelity is undefined: no shots for {basis}")
        correlations[basis] = sum(
            (1 if key in ("00", "11") else -1) * value
            for key, value in outcomes.items()
        ) / shots
    return correlations


def measured_bell_fidelity(counts: Mapping[str, Mapping[str, int]]) -> float:
    """Apply (1 + XX - YY + ZZ) / 4 without clipping sampling fluctuations."""
    correlations = bell_correlations(counts)
    return (1 + correlations["XX"] - correlations["YY"] + correlations["ZZ"]) / 4


def run_bell_measurements(
    circuit: QuantumCircuit, ports: tuple[int, int], *, shots: int = 3072, seed: int = 42
) -> BellMeasurementResult:
    """Run noiseless Aer experiments with a total shot budget across all bases.

    Divide shots equally; give any remainder to XX, then YY. Seed each basis
    with seed + its index. All shots are retained; no postselection is applied.
    """
    if not isinstance(shots, int) or isinstance(shots, bool) or shots < 3:
        raise ValueError("shots must be an integer total budget of at least 3")
    if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed <= 2**32 - 3:
        raise ValueError("seed must be an integer between 0 and 2**32 - 3")
    circuits = build_bell_measurement_circuits(circuit, ports)
    simulator = AerSimulator(method="matrix_product_state")
    counts = {}
    shots_by_basis = {}
    for index, basis in enumerate(BASES):
        basis_shots = shots // 3 + (index < shots % 3)
        shots_by_basis[basis] = basis_shots
        counts[basis] = dict(simulator.run(
            circuits[basis], shots=basis_shots, seed_simulator=seed + index
        ).result().get_counts())
    return BellMeasurementResult(
        counts=counts, correlations=bell_correlations(counts),
        fidelity=measured_bell_fidelity(counts), shots_by_basis=shots_by_basis, seed=seed,
    )
