"""Synthetic independent bit-flip noise for the first topology comparison."""

from dataclasses import dataclass
from math import isfinite

from qiskit import QuantumCircuit, transpile
from qiskit_aer.noise import NoiseModel, ReadoutError, pauli_error

# Common experimental basis, not an IBM backend's native gate set.
SINGLE_QUBIT_GATES = ("h", "sdg", "rz", "sx", "x", "id")
SYNTHETIC_BASIS = (*SINGLE_QUBIT_GATES, "cx")


@dataclass(frozen=True)
class BitFlipNoise:
    """Probabilities per gate/bit, uniform across sites and independent in time.

    single_qubit: X after each one-qubit gate, including basis rotations.
    two_qubit: independent X on EACH participant after each CX.
    readout: symmetric classical bit-flip probability per measured bit.
    These are illustrative settings, not organizer or hardware calibration data.
    """

    single_qubit: float = 0.001
    two_qubit: float = 0.01
    readout: float = 0.01

    def __post_init__(self) -> None:
        for name in ("single_qubit", "two_qubit", "readout"):
            value = getattr(self, name)
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not isfinite(value) or not 0 <= value <= 1):
                raise ValueError(f"{name} must be a finite probability between 0 and 1")

    def to_aer(self) -> NoiseModel:
        model = NoiseModel(basis_gates=list(SYNTHETIC_BASIS))
        if self.single_qubit:
            error = pauli_error([("X", self.single_qubit), ("I", 1 - self.single_qubit)])
            model.add_all_qubit_quantum_error(error, list(SINGLE_QUBIT_GATES))
        if self.two_qubit:
            error = pauli_error([("X", self.two_qubit), ("I", 1 - self.two_qubit)])
            model.add_all_qubit_quantum_error(error.tensor(error), ["cx"])
        if self.readout:
            p = self.readout
            model.add_all_qubit_readout_error(ReadoutError([[1 - p, p], [p, 1 - p]]))
        return model


def compile_synthetic_circuit(circuit: QuantumCircuit) -> QuantumCircuit:
    """Translate gates without layout/routing or optimization of chosen paths.

    Each SWAP becomes three CX gates; all three receive CX noise when enabled.
    Both comparison arms use this same translation, including basis rotations.
    """
    return transpile(circuit, basis_gates=list(SYNTHETIC_BASIS), optimization_level=0)
