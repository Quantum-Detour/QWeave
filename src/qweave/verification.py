"""Exact ideal-state verification for small Bell preparation circuits."""

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, partial_trace, state_fidelity

from .circuits import build_ideal_bell_circuit

MAX_STATEVECTOR_QUBITS = 22
BELL_FIDELITY_TOLERANCE = 1e-10


def _active_sites(circuit: QuantumCircuit, ports: tuple[int, int]) -> list[int]:
    return sorted(set(ports) | {
        circuit.find_bit(qubit).index
        for instruction in circuit.data if instruction.operation.name != "barrier"
        for qubit in instruction.qubits
    })


def _validate_bell_input(circuit: QuantumCircuit, ports: tuple[int, int]) -> None:
    if len(ports) != 2 or any(
        not isinstance(port, int) or isinstance(port, bool)
        or not 0 <= port < circuit.num_qubits
        for port in ports
    ) or ports[0] == ports[1]:
        raise ValueError("ports must contain two distinct, valid physical qubit indices")
    if any(instruction.operation.name == "measure" for instruction in circuit.data):
        raise ValueError("Bell fidelity requires an unmeasured circuit; use measure=False")
    active_count = len(_active_sites(circuit, ports))
    if active_count > MAX_STATEVECTOR_QUBITS:
        raise ValueError(
            f"Statevector resource limit: {active_count} active qubits requested; "
            f"maximum is {MAX_STATEVECTOR_QUBITS} active qubits"
        )


def bell_fidelity(circuit: QuantumCircuit, ports: tuple[int, int]) -> float:
    """Return exact ideal Phi+ fidelity, tracing workspace from a statevector.

    The Bell target is symmetric under exchange of the two output ports.
    """
    _validate_bell_input(circuit, ports)
    # Unused sites stay in |0> and factor out exactly. Compact only this ideal
    # diagnostic; physical indices are retained for calibrated compilation/noise.
    sites = _active_sites(circuit, ports)
    indices = {site: index for index, site in enumerate(sites)}
    compact = QuantumCircuit(len(sites))
    compact.global_phase = circuit.global_phase
    for instruction in circuit.data:
        if instruction.operation.name == "barrier":
            continue
        compact.append(instruction.operation, [indices[circuit.find_bit(q).index] for q in instruction.qubits])
    actual = Statevector.from_instruction(compact)
    output_indices = {indices[port] for port in ports}
    workspace = [qubit for qubit in range(len(sites)) if qubit not in output_indices]
    output_state = partial_trace(actual, workspace)
    ideal = Statevector.from_instruction(build_ideal_bell_circuit(measure=False))
    return float(state_fidelity(output_state, ideal))
