"""Offline snapshot and synthetic test beds shared by routing implementations."""

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path

from qiskit import QuantumCircuit
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_aer.noise import NoiseModel
from qiskit_ibm_runtime.fake_provider import FakeSherbrooke
from qiskit_ibm_runtime.fake_provider.fake_backend import FakeBackendV2

from .processors import PROCESSOR_CONFIGS, Processor
from .settings import OptimizationLevel


@dataclass(frozen=True)
class BackendSnapshot:
    backend_name: str
    backend_class: str
    num_qubits: int
    calibration_time: str | None
    snapshot_sha256: str
    qiskit_version: str
    aer_version: str
    runtime_version: str
    compiler_seed: int
    noise_source: str = "calibration_snapshot"
    backend_seed: int | None = None
    generator_config: dict | None = None
    optimization_level: OptimizationLevel = OptimizationLevel.MAXIMUM
    optimization_name: str = OptimizationLevel.MAXIMUM.name.lower()
    approximation_degree: float = 1.0
    qubits_initially_zero: bool = False
    layout_method: str = "trivial"
    routing_method: str = "none"
    simulator_method: str = "matrix_product_state"
    noise_recipe: str = "NoiseModel.from_backend: gate_error, readout_error, thermal_relaxation; temperature=0"
    idle_relaxation: bool = False
    mitigation_enabled: bool = False


@dataclass(frozen=True)
class CalibratedGate:
    name: str
    qubits: tuple[int, ...]
    error: float | None
    duration_seconds: float | None


class FakeBackendTestbed:
    """Use one offline snapshot for connectivity, native gates, and Aer noise.

    Input circuits are already routed and use physical site indices. Native
    translation cannot silently reroute a method's circuit or change placement.
    No cloud service, snapshot refresh, or runtime mitigation is used.
    """

    @classmethod
    def for_processor(
        cls, name: str, *, backend_seed: int = 1234, compiler_seed: int = 42,
        optimization_level: OptimizationLevel = OptimizationLevel.MAXIMUM,
    ) -> "FakeBackendTestbed":
        """Construct the shared backend for a named processor configuration."""
        try:
            config = PROCESSOR_CONFIGS[name]
        except KeyError as exc:
            raise ValueError(f"Unknown processor {name!r}; choose one of: {', '.join(PROCESSOR_CONFIGS)}") from exc
        if config.backend_kind == "sherbrooke":
            return cls.sherbrooke(compiler_seed=compiler_seed, optimization_level=optimization_level)
        if config.backend_kind != "generic" or config.num_qubits is None:
            raise ValueError(f"Invalid backend configuration for {name!r}")
        topology = Processor(
            name=name, description="Custom backend topology input",
            num_qubits=config.num_qubits, edges=config.edges,
            output_ports=config.output_ports, provenance=config.provenance,
        )
        return cls.generic(topology, backend_seed=backend_seed, compiler_seed=compiler_seed, optimization_level=optimization_level)

    @classmethod
    def sherbrooke(cls, *, compiler_seed: int = 42, optimization_level: OptimizationLevel = OptimizationLevel.MAXIMUM) -> "FakeBackendTestbed":
        """Load the same fake backend used in transpile-with-pass-managers.ipynb."""
        return cls(FakeSherbrooke(), compiler_seed=compiler_seed, optimization_level=optimization_level)

    @classmethod
    def generic(
        cls, processor: Processor, *, backend_seed: int = 1234, compiler_seed: int = 42,
        optimization_level: OptimizationLevel = OptimizationLevel.MAXIMUM,
    ) -> "FakeBackendTestbed":
        """Generate a reproducible synthetic target on the given physical graph.

        Both CX directions are assumed on each edge. Generated properties are
        hardware-inspired defaults, not calibrations of an actual device.
        """
        if isinstance(backend_seed, bool) or not isinstance(backend_seed, int) or backend_seed < 0:
            raise ValueError("backend_seed must be a nonnegative integer")
        coupling = sorted({direction for a, b in processor.edges for direction in ((a, b), (b, a))})
        config = {
            "num_qubits": processor.num_qubits,
            "basis_gates": ["id", "rz", "sx", "x", "cx"],
            "coupling_map": [list(edge) for edge in coupling],
            "control_flow": False, "noise_info": True, "seed": backend_seed,
        }
        return cls(GenericBackendV2(**deepcopy(config)), compiler_seed=compiler_seed, generator_config=config, optimization_level=optimization_level)

    def __init__(
        self, backend: FakeBackendV2 | GenericBackendV2, *, compiler_seed: int = 42,
        generator_config: dict | None = None,
        optimization_level: OptimizationLevel = OptimizationLevel.MAXIMUM,
    ):
        if not isinstance(backend, (FakeBackendV2, GenericBackendV2)):
            raise ValueError("The test bed requires an offline snapshot or GenericBackendV2")
        if isinstance(compiler_seed, bool) or not isinstance(compiler_seed, int) or compiler_seed < 0:
            raise ValueError("compiler_seed must be a nonnegative integer")
        if not isinstance(optimization_level, OptimizationLevel):
            raise ValueError("optimization_level must be an OptimizationLevel enum member")
        self.backend = backend
        self.target = backend.target
        self.compiler_seed = compiler_seed
        fingerprint = sha256()
        if isinstance(backend, GenericBackendV2):
            if generator_config is None:
                raise ValueError("Use FakeBackendTestbed.generic to record reproducible generator settings")
            # Hash actual generated properties as well as construction settings.
            # Seeds alone are not a guarantee across Qiskit versions.
            payload = {
                "config": generator_config, "dt": backend.dt,
                "qubits": [
                    {key: getattr(props, key) for key in ("t1", "t2", "frequency")}
                    for props in self.target.qubit_properties
                ],
                "instructions": [
                    {"name": name, "qubits": qubits,
                     "error": props.error if props else None,
                     "duration": props.duration if props else None}
                    for name in sorted(self.target.operation_names)
                    for qubits, props in sorted(self.target[name].items())
                ],
            }
            fingerprint.update(json.dumps(payload, sort_keys=True).encode())
            calibration_time = None
        else:
            for filename in (backend.conf_filename, backend.props_filename):
                fingerprint.update(filename.encode())
                fingerprint.update((Path(backend.dirname) / filename).read_bytes())
            calibration_time = backend.properties().last_update_date.isoformat()
        self.snapshot = BackendSnapshot(
            backend_name=backend.name, backend_class=type(backend).__name__,
            num_qubits=backend.num_qubits,
            calibration_time=calibration_time,
            snapshot_sha256=fingerprint.hexdigest(),
            qiskit_version=version("qiskit"), aer_version=version("qiskit-aer"),
            runtime_version=version("qiskit-ibm-runtime"), compiler_seed=compiler_seed,
            noise_source="generated_synthetic" if generator_config else "calibration_snapshot",
            backend_seed=generator_config["seed"] if generator_config else None,
            generator_config=generator_config,
            optimization_level=optimization_level, optimization_name=optimization_level.name.lower(),
        )
        self.noise_model = NoiseModel.from_backend(
            backend, gate_error=True, readout_error=True, thermal_relaxation=True, temperature=0,
        )

    def processor(self, output_ports: tuple[int, int], *, name: str = "ibm_heavy_hex") -> Processor:
        """Derive graph adjacency from this snapshot, retaining native directions in target."""
        if len(output_ports) != 2 or output_ports[0] == output_ports[1] or any(
            isinstance(p, bool) or not isinstance(p, int) or not 0 <= p < self.backend.num_qubits
            for p in output_ports
        ):
            raise ValueError("Expected two distinct physical output ports within the backend")
        edges = tuple(sorted({tuple(sorted(edge)) for edge in self.backend.coupling_map.get_edges()}))
        graph_source = PROCESSOR_CONFIGS[name].provenance if name in PROCESSOR_CONFIGS else "Caller-supplied topology and ports."
        return Processor(
            name=name, description=f"{type(self.backend).__name__} {self.snapshot.noise_source}",
            num_qubits=self.backend.num_qubits, edges=edges, output_ports=output_ports,
            provenance=f"{self.snapshot.backend_class}; {self.snapshot.noise_source}; sha256={self.snapshot.snapshot_sha256}; graph: {graph_source}",
        )

    def gate_calibrations(self) -> tuple[CalibratedGate, ...]:
        """Expose directed error/duration data for future noise-aware routing costs."""
        return tuple(
            CalibratedGate(name, qubits, props.error if props else None, props.duration if props else None)
            for name in sorted(self.target.operation_names)
            for qubits, props in self.target[name].items() if qubits is not None
        )

    def compile(self, circuit: QuantumCircuit) -> QuantumCircuit:
        if circuit.num_qubits != self.backend.num_qubits:
            raise ValueError("Physical circuit width must match the selected fake backend")
        if any(item.operation.name == "delay" for item in circuit.data):
            raise ValueError("Explicit idle delays require scheduled relaxation support")
        manager = generate_preset_pass_manager(
            optimization_level=self.snapshot.optimization_level, backend=self.backend,
            approximation_degree=self.snapshot.approximation_degree,
            qubits_initially_zero=self.snapshot.qubits_initially_zero,
            layout_method=self.snapshot.layout_method,
            initial_layout=list(range(circuit.num_qubits)),
            routing_method="none", seed_transpiler=self.compiler_seed,
        )
        native = manager.run(circuit)
        if native.layout.final_index_layout() != list(range(circuit.num_qubits)):
            raise ValueError("Native compilation changed the physical placement")
        for instruction in native.data:
            if instruction.operation.name == "barrier":
                continue
            qubits = tuple(native.find_bit(q).index for q in instruction.qubits)
            if not self.target.instruction_supported(
                operation_name=instruction.operation.name, qargs=qubits,
                parameters=list(instruction.operation.params),
            ):
                raise ValueError(f"Unsupported native operation {instruction.operation.name} on {qubits}")
        return native
