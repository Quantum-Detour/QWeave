"""Shared maximum optimization preserves physical placement and operation semantics."""

from dataclasses import asdict
import json
import unittest

from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from qweave import BackendOperationCosts, FakeBackendTestbed, OptimizationLevel, build_bell_circuit, bell_fidelity
from qweave.measurements import prepare_bell_measurements, sample_bell_measurements


class OptimizationTests(unittest.TestCase):
    def test_named_settings_and_snapshot_identity(self):
        maximum = FakeBackendTestbed.for_processor("five_node")
        none = FakeBackendTestbed.for_processor("five_node", optimization_level=OptimizationLevel.NONE)
        self.assertEqual(maximum.snapshot.optimization_level, OptimizationLevel.MAXIMUM)
        self.assertEqual(maximum.snapshot.optimization_name, "maximum")
        self.assertEqual(maximum.snapshot.snapshot_sha256, none.snapshot.snapshot_sha256)
        self.assertEqual(maximum.snapshot.approximation_degree, 1.0)
        self.assertFalse(maximum.snapshot.qubits_initially_zero)
        self.assertEqual(json.loads(json.dumps(asdict(maximum.snapshot)))["optimization_level"], 3)
        with self.assertRaisesRegex(ValueError, "enum"):
            FakeBackendTestbed.for_processor("five_node", optimization_level=99)

    def test_isolated_swap_is_not_optimized_away(self):
        bed = FakeBackendTestbed.for_processor("five_node")
        circuit = QuantumCircuit(5)
        circuit.swap(1, 0)
        compiled = bed.compile(circuit)
        self.assertTrue(Operator(compiled).equiv(Operator(circuit)))
        cost = BackendOperationCosts(bed).operation("swap", 1, 0)
        self.assertGreater(cost.cost, 0)
        self.assertEqual(len(cost.native_gates), 3)

    def test_all_methods_share_maximum_and_fixed_ports(self):
        bed = FakeBackendTestbed.for_processor("five_node")
        processor = bed.processor((0, 4), name="five_node")
        costs = BackendOperationCosts(bed)
        for algorithm in ("shortest_path", "sabre", "noise_aware"):
            with self.subTest(algorithm=algorithm):
                built = build_bell_circuit(processor, measure=False, algorithm=algorithm, costs=costs)
                native = bed.compile(built.circuit)
                self.assertEqual(native.layout.final_index_layout(), list(range(5)))
                self.assertAlmostEqual(bell_fidelity(native, (0, 4)), 1)
                self.assertEqual(native, bed.compile(built.circuit))
                prepared = prepare_bell_measurements(built.circuit, (0, 4), testbed=bed)
                clean = sample_bell_measurements(prepared, testbed=bed, shots=30)
                noisy = sample_bell_measurements(prepared, testbed=bed, backend_noise=True, shots=30)
                self.assertIs(clean.circuits, noisy.circuits)
                self.assertEqual(clean.testbed, noisy.testbed)
                self.assertEqual(clean.testbed.optimization_level, OptimizationLevel.MAXIMUM)
                self.assertEqual(clean.fidelity, 1)
                if algorithm == "noise_aware":
                    self.assertEqual(built.routing.cost_compiler_settings["optimization_name"], "maximum")

    def test_maximum_simplifies_cancellations(self):
        maximum = FakeBackendTestbed.for_processor("five_node")
        none = FakeBackendTestbed.for_processor("five_node", optimization_level=OptimizationLevel.NONE)
        circuit = QuantumCircuit(5)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.cx(0, 1)
        optimized = maximum.compile(circuit)
        translated = none.compile(circuit)
        self.assertLess(optimized.count_ops().get("cx", 0), translated.count_ops()["cx"])
        self.assertTrue(Operator(optimized).equiv(Operator(circuit)))


if __name__ == "__main__":
    unittest.main()
