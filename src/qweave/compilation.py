"""Gate translation for standalone ideal circuits without a hardware target."""

from qiskit import QuantumCircuit, transpile

from .settings import OptimizationLevel


def compile_ideal_circuit(
    circuit: QuantumCircuit, *, optimization_level: OptimizationLevel = OptimizationLevel.MAXIMUM,
) -> QuantumCircuit:
    """Decompose SWAPs for ideal Aer execution without changing placement.

    Hardware experiments use FakeBackendTestbed.compile instead, including
    their noiseless reference runs.
    """
    return transpile(
        circuit, basis_gates=["h", "sdg", "rz", "sx", "x", "id", "cx"],
        optimization_level=optimization_level, approximation_degree=1.0,
        qubits_initially_zero=False, routing_method="none",
    )
