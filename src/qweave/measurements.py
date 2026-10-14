"""Shot-based Bell fidelity from separate XX, YY, and ZZ experiments."""

from dataclasses import dataclass, field
from collections.abc import Mapping
from math import log, sqrt

from qiskit import ClassicalRegister, QuantumCircuit
from qiskit_aer import AerSimulator

from .verification import _validate_bell_input
from .compilation import compile_ideal_circuit
from .backends import BackendSnapshot, FakeBackendTestbed

BASES = ("XX", "YY", "ZZ")


@dataclass(frozen=True)
class BellMeasurementResult:
    counts: dict[str, dict[str, int]]
    correlations: dict[str, float | None]
    fidelity: float | None
    shots_by_basis: dict[str, int]
    seed: int
    fidelity_interval: tuple[float, float] | None
    circuits: dict[str, QuantumCircuit]
    noise: BackendSnapshot | None
    testbed: BackendSnapshot | None = None
    raw_counts: dict[str, dict[str, int]] = field(default_factory=dict)
    unconditional_counts: dict[str, dict[str, int]] = field(default_factory=dict)
    unconditional_fidelity: float | None = None
    unconditional_interval: tuple[float, float] | None = None
    accepted_by_basis: dict[str, int] = field(default_factory=dict)
    discarded_by_basis: dict[str, int] = field(default_factory=dict)
    acceptance_intervals: dict[str, tuple[float, float]] = field(default_factory=dict)
    syndrome_sites: tuple[int, ...] = ()


def build_bell_measurement_circuits(
    circuit: QuantumCircuit, ports: tuple[int, int]
) -> dict[str, QuantumCircuit]:
    """Copy the preparation and rotate each output into the requested basis.

    Classical bit 0 measures ports[0], bit 1 measures ports[1]. Qiskit count
    strings display bit 1 first; parity is independent of that ordering.
    """
    _validate_bell_input(circuit, ports, check_resources=False)
    if circuit.num_clbits:
        raise ValueError("Measurement preparation must have no classical bits")
    syndrome_sites = tuple((circuit.metadata or {}).get("qweave_syndrome_sites", ()))
    if len(set(syndrome_sites)) != len(syndrome_sites) or any(
        isinstance(site, bool) or not isinstance(site, int)
        or site in ports or not 0 <= site < circuit.num_qubits for site in syndrome_sites
    ):
        raise ValueError("Syndrome sites must be distinct workspace qubits")
    circuits = {}
    for basis in BASES:
        measured = circuit.copy(name=f"{circuit.name}_{basis}")
        measured.add_register(ClassicalRegister(2, "bell"))
        measured.barrier(label="preparation_complete")
        if syndrome_sites:
            syndrome = ClassicalRegister(len(syndrome_sites), "syndrome")
            measured.add_register(syndrome)
            measured.measure(syndrome_sites, syndrome)
        measured.barrier(label="syndrome_complete")
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


def bell_fidelity_interval(counts: Mapping[str, Mapping[str, int]]) -> tuple[float, float]:
    """Conservative 95% sampling interval using simultaneous Hoeffding bounds.

    For each even-parity probability use epsilon=sqrt(log(6/0.05)/(2N)).
    A union bound covers all three bases, then propagate endpoints through F.
    Assumes independent shots. Covers sampling error, not measurement bias or
    uncertainty in the assumed noise model. Do not clip the fidelity interval.
    """
    correlations = bell_correlations(counts)
    bounds = {}
    for basis, correlation in correlations.items():
        p = (1 + correlation) / 2
        epsilon = sqrt(log(6 / 0.05) / (2 * sum(counts[basis].values())))
        bounds[basis] = (2 * max(0, p - epsilon) - 1, 2 * min(1, p + epsilon) - 1)
    x, y, z = (bounds[basis] for basis in BASES)
    return ((1 + x[0] - y[1] + z[0]) / 4, (1 + x[1] - y[0] + z[1]) / 4)


def run_bell_measurements(
    circuit: QuantumCircuit, ports: tuple[int, int], *, shots: int = 3072, seed: int = 42,
    testbed: FakeBackendTestbed | None = None, backend_noise: bool = False,
) -> BellMeasurementResult:
    """Run Aer experiments with optional noise and a total shot budget across bases.

    Divide shots equally; give any remainder to XX, then YY. Seed each basis
    with seed + its index. Recorded syndrome sites enable zero-syndrome postselection.
    """
    circuits = prepare_bell_measurements(circuit, ports, testbed=testbed)
    return sample_bell_measurements(
        circuits, shots=shots, seed=seed, testbed=testbed, backend_noise=backend_noise,
    )


def prepare_bell_measurements(
    circuit: QuantumCircuit, ports: tuple[int, int], *, testbed: FakeBackendTestbed | None = None,
) -> dict[str, QuantumCircuit]:
    """Build and compile XX/YY/ZZ once for reuse in clean and noisy arms."""
    return {
        basis: testbed.compile(measured) if testbed else compile_ideal_circuit(measured)
        for basis, measured in build_bell_measurement_circuits(circuit, ports).items()
    }


def sample_bell_measurements(
    circuits: dict[str, QuantumCircuit], *, shots: int = 3072, seed: int = 42,
    testbed: FakeBackendTestbed | None = None, backend_noise: bool = False,
) -> BellMeasurementResult:
    """Sample circuits returned by prepare_bell_measurements without recompiling.

    Supply the same test bed used for preparation. Each arm receives the full
    shot budget and the same per-basis seed schedule.
    """
    if not isinstance(shots, int) or isinstance(shots, bool) or shots < 3:
        raise ValueError("shots must be an integer total budget of at least 3")
    if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed <= 2**32 - 3:
        raise ValueError("seed must be an integer between 0 and 2**32 - 3")
    if backend_noise and testbed is None:
        raise ValueError("backend_noise requires a fake backend test bed")
    if set(circuits) != set(BASES):
        raise ValueError("Prepared circuits must contain exactly XX, YY, and ZZ")
    simulator = AerSimulator(
        method="matrix_product_state",
        noise_model=testbed.noise_model if backend_noise else None,
    )
    raw_counts = {}
    shots_by_basis = {}
    for index, basis in enumerate(BASES):
        basis_shots = shots // 3 + (index < shots % 3)
        shots_by_basis[basis] = basis_shots
        raw_counts[basis] = dict(simulator.run(
            circuits[basis], shots=basis_shots, seed_simulator=seed + index
        ).result().get_counts())
    return summarize_measurements(raw_counts, circuits, shots_by_basis, seed=seed,
                                  testbed=testbed, backend_noise=backend_noise)


def summarize_measurements(raw_counts, circuits, shots_by_basis, *, seed=42,
                           testbed=None, backend_noise=False):
    """Decode register bits by index; retain both conditional and marginal counts."""
    counts = {}; unconditional = {}; accepted = {}; discarded = {}; intervals = {}
    for basis in BASES:
        circuit = circuits[basis]
        bell_register = next(register for register in circuit.cregs if register.name == 'bell')
        bell_bits = [circuit.find_bit(bit).index for bit in bell_register]
        syndrome_bits = [circuit.find_bit(bit).index for register in circuit.cregs
                         if register.name == 'syndrome' for bit in register]
        counts[basis] = {}; unconditional[basis] = {}
        for outcome, count in raw_counts[basis].items():
            bits = int(outcome.replace(' ', ''), 2)
            bell = ''.join(str((bits >> index) & 1) for index in reversed(bell_bits))
            unconditional[basis][bell] = unconditional[basis].get(bell, 0) + count
            if all(not ((bits >> index) & 1) for index in syndrome_bits):
                counts[basis][bell] = counts[basis].get(bell, 0) + count
        accepted[basis] = sum(counts[basis].values())
        n = shots_by_basis[basis]
        if sum(unconditional[basis].values()) != n:
            raise ValueError('Raw counts do not match attempted-shot budget')
        discarded[basis] = n - accepted[basis]
        p = accepted[basis] / n
        eps = sqrt(log(2 / 0.05) / (2 * n))
        intervals[basis] = (max(0., p-eps), min(1., p+eps))
    defined = all(accepted.values())
    correlations = {basis: (sum((1 if key in ('00', '11') else -1) * n
                               for key, n in counts[basis].items()) / accepted[basis]
                           if accepted[basis] else None) for basis in BASES}
    return BellMeasurementResult(
        counts=counts, correlations=correlations,
        fidelity=measured_bell_fidelity(counts) if defined else None,
        fidelity_interval=bell_fidelity_interval(counts) if defined else None,
        shots_by_basis=shots_by_basis, seed=seed, circuits=circuits,
        noise=testbed.snapshot if backend_noise else None,
        testbed=testbed.snapshot if testbed else None,
        raw_counts=raw_counts, unconditional_counts=unconditional,
        unconditional_fidelity=measured_bell_fidelity(unconditional),
        unconditional_interval=bell_fidelity_interval(unconditional),
        accepted_by_basis=accepted, discarded_by_basis=discarded,
        acceptance_intervals=intervals,
        syndrome_sites=tuple((circuits['XX'].metadata or {}).get('qweave_syndrome_sites', ())),
    )
