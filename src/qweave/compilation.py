"""Gate translation for standalone ideal circuits without a hardware target."""

from qiskit import QuantumCircuit, transpile


def compile_ideal_circuit(circuit: QuantumCircuit) -> QuantumCircuit:
    """Decompose SWAPs for ideal Aer execution without changing placement.

    Hardware experiments use FakeBackendTestbed.compile instead, including
    their noiseless reference runs.
    """
    return transpile(
        circuit, basis_gates=["h", "sdg", "rz", "sx", "x", "id", "cx"],
        optimization_level=0,
    )
