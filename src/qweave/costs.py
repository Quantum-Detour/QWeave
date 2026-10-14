"""Classical routing proxies derived from a fixed backend's native gates."""

from dataclasses import asdict, dataclass
from math import inf, isfinite, log1p
from time import perf_counter
from typing import TYPE_CHECKING

from qiskit import QuantumCircuit

if TYPE_CHECKING:
    from .backends import FakeBackendTestbed
    from .processors import Processor


@dataclass(frozen=True)
class NativeGateCost:
    name: str
    qubits: tuple[int, ...]
    error: float
    cost: float


@dataclass(frozen=True)
class OperationCost:
    operation: str
    qubits: tuple[int, int]
    cost: float
    native_gates: tuple[NativeGateCost, ...]

    def record(self) -> dict:
        return asdict(self)


class BackendOperationCosts:
    """Compile and cache ordered CX/SWAP costs without executing any circuit.

    The backend must remain unchanged for this provider's lifetime. Costs are
    routing heuristics, not predicted Bell fidelities or failure probabilities.
    """

    model = "native-negative-log-gate-error-v2"

    def __init__(self, testbed: "FakeBackendTestbed"):
        self.testbed = testbed
        self.backend_fingerprint = testbed.snapshot.snapshot_sha256
        self.compiler_settings = {
            "optimization_level": testbed.snapshot.optimization_level,
            "optimization_name": testbed.snapshot.optimization_name,
            "approximation_degree": testbed.snapshot.approximation_degree,
            "qubits_initially_zero": testbed.snapshot.qubits_initially_zero,
            "layout_method": testbed.snapshot.layout_method,
            "routing_method": testbed.snapshot.routing_method,
            "compiler_seed": testbed.compiler_seed,
        }
        self.preparation_seconds = 0.0
        self._cache: dict[tuple[str, int, int], OperationCost] = {}

    def validate_processor(self, processor: "Processor") -> None:
        backend = self.testbed.backend
        edges = {tuple(sorted(edge)) for edge in backend.coupling_map.get_edges()}
        if processor.num_qubits != backend.num_qubits or edges != {tuple(sorted(e)) for e in processor.edges}:
            raise ValueError("Routing costs and processor must use the same backend connectivity")

    def native_cost_record(self, circuit: QuantumCircuit) -> dict:
        """Score the executed decomposition without compiling or simulating.

        Gate and readout proxies are separate. Neither predicts fidelity;
        target gate errors also do not fully describe the Aer noise channels.
        """
        gates = []
        readout = []
        for item in circuit.data:
            name = item.operation.name
            if name == 'barrier':
                continue
            qubits = tuple(circuit.find_bit(q).index for q in item.qubits)
            props = self.testbed.target[name].get(qubits)
            error = props.error if props is not None else None
            if error is None or not isfinite(error) or not 0 <= error <= 1:
                raise ValueError(f'Missing or invalid gate error for {name}{qubits}: {error}')
            record = NativeGateCost(name, qubits, float(error),
                                    inf if error == 1 else -log1p(-error))
            (readout if name == 'measure' else gates).append(record)
        return dict(gate_cost=sum(g.cost for g in gates),
                    readout_cost=sum(g.cost for g in readout),
                    native_gates=[asdict(g) for g in gates],
                    readout=[asdict(g) for g in readout],
                    gates=dict(circuit.count_ops()), depth=circuit.depth(),
                    native_two_qubit_gates=sum(len(g.qubits) == 2 for g in gates))

    def operation(self, name: str, source: int, destination: int) -> OperationCost:
        if name not in {"cx", "swap"}:
            raise ValueError("Routing costs support only CX and SWAP")
        key = (name, source, destination)
        if key in self._cache:
            return self._cache[key]
        started = perf_counter()
        try:
            circuit = QuantumCircuit(self.testbed.backend.num_qubits)
            getattr(circuit, name)(source, destination)
            native = self.testbed.compile(circuit)
            gates = []
            for item in native.data:
                if item.operation.name == "barrier":
                    continue
                qubits = tuple(native.find_bit(q).index for q in item.qubits)
                props = self.testbed.target[item.operation.name].get(qubits)
                error = props.error if props is not None else None
                if error is None or not isfinite(error) or not 0 <= error <= 1:
                    raise ValueError(f"Missing or invalid gate error for {item.operation.name}{qubits}: {error}")
                cost = inf if error == 1 else -log1p(-error)
                gates.append(NativeGateCost(item.operation.name, qubits, float(error), cost))
            result = OperationCost(name, (source, destination), sum(g.cost for g in gates), tuple(gates))
            self._cache[key] = result
            return result
        finally:
            self.preparation_seconds += perf_counter() - started
