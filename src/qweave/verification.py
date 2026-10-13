"""Exact ideal-state verification for small Bell preparation circuits."""

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, partial_trace, state_fidelity

from .circuits import build_ideal_bell_circuit

MAX_STATEVECTOR_QUBITS = 22
BELL_FIDELITY_TOLERANCE = 1e-10


def _validate_bell_input(circuit: QuantumCircuit, ports: tuple[int, int]) -> None:
    if len(ports) != 2 or any(
        not isinstance(port, int) or isinstance(port, bool)
        or not 0 <= port < circuit.num_qubits
        for port in ports
    ) or ports[0] == ports[1]:
        raise ValueError("ports must contain two distinct, valid physical qubit indices")
    if any(instruction.operation.name == "measure" for instruction in circuit.data):
        raise ValueError("Bell fidelity requires an unmeasured circuit; use measure=False")
    if circuit.num_qubits > MAX_STATEVECTOR_QUBITS:
        raise ValueError(
            f"Statevector resource limit: {circuit.num_qubits} qubits requested; "
            f"maximum is {MAX_STATEVECTOR_QUBITS}"
        )


def bell_fidelity(circuit: QuantumCircuit, ports: tuple[int, int]) -> float:
    """Return exact ideal Phi+ fidelity, tracing workspace from a statevector.

    The Bell target is symmetric under exchange of the two output ports.
    """
    _validate_bell_input(circuit, ports)
    actual = Statevector.from_instruction(circuit)
    workspace = [qubit for qubit in range(circuit.num_qubits) if qubit not in ports]
    output_state = partial_trace(actual, workspace)
    ideal = Statevector.from_instruction(build_ideal_bell_circuit(measure=False))
    return float(state_fidelity(output_state, ideal))
