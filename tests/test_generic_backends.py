"""Synthetic backends retain custom graphs and reproducible noise properties."""

from dataclasses import asdict
import json
import unittest

from qiskit import QuantumCircuit
from qiskit.transpiler.exceptions import TranspilerError

from qweave import PROCESSORS, FakeBackendTestbed, bell_fidelity, build_bell_circuit, run_bell_measurements


class GenericBackendTests(unittest.TestCase):
    def test_generated_properties_reproducible_and_seed_sensitive(self):
        processor = PROCESSORS["five_node"]
        first = FakeBackendTestbed.generic(processor, backend_seed=1234)
        second = FakeBackendTestbed.generic(processor, backend_seed=1234, compiler_seed=99)
        changed = FakeBackendTestbed.generic(processor, backend_seed=1235)
        self.assertEqual(first.snapshot.snapshot_sha256, second.snapshot.snapshot_sha256)
        self.assertEqual(first.gate_calibrations(), second.gate_calibrations())
        self.assertNotEqual(first.snapshot.snapshot_sha256, changed.snapshot.snapshot_sha256)
        self.assertEqual(first.processor((0, 4)).edges, changed.processor((0, 4)).edges)

    def test_custom_topologies_native_gates_and_ideal_fidelity(self):
        for name in ("five_node", "hyperbolic_inspired"):
            with self.subTest(processor=name):
                processor = PROCESSORS[name]
                testbed = FakeBackendTestbed.generic(processor)
                derived = testbed.processor(processor.output_ports, name=name)
                self.assertEqual(derived.name, name)
                self.assertEqual(derived.num_qubits, processor.num_qubits)
                self.assertEqual(set(derived.graph().edges()), set(processor.graph().edges()))
                built = build_bell_circuit(derived, measure=False)
                native = testbed.compile(built.circuit)
                self.assertAlmostEqual(bell_fidelity(native, derived.output_ports), 1, delta=1e-10)
                self.assertEqual(native.layout.final_index_layout(), list(range(processor.num_qubits)))
                for instruction in native.data:
                    qubits = tuple(native.find_bit(q).index for q in instruction.qubits)
                    self.assertTrue(testbed.target.instruction_supported(
                        operation_name=instruction.operation.name, qargs=qubits,
                    ))
                    if len(qubits) == 2:
                        self.assertTrue(processor.graph().has_edge(*qubits))

    def test_native_noise_and_report_provenance(self):
        for name in ("five_node", "hyperbolic_inspired"):
            with self.subTest(processor=name):
                processor = PROCESSORS[name]
                testbed = FakeBackendTestbed.generic(processor)
                built = build_bell_circuit(processor, measure=False)
                clean = run_bell_measurements(built.circuit, processor.output_ports, testbed=testbed, shots=300)
                noisy = run_bell_measurements(
                    built.circuit, processor.output_ports, testbed=testbed, backend_noise=True, shots=300,
                )
                repeat = run_bell_measurements(
                    built.circuit, processor.output_ports, testbed=testbed, backend_noise=True, shots=300,
                )
                self.assertEqual(clean.fidelity, 1)
                self.assertLess(noisy.fidelity, 1)
                self.assertEqual(noisy.counts, repeat.counts)
                self.assertEqual(clean.circuits, noisy.circuits)
                self.assertEqual(clean.testbed, noisy.testbed)
                self.assertIsNone(clean.noise)
                metadata = json.loads(json.dumps(asdict(noisy.noise)))
                self.assertEqual(metadata["noise_source"], "generated_synthetic")
                self.assertIsNone(metadata["calibration_time"])
                self.assertEqual(metadata["backend_seed"], 1234)
                self.assertTrue(metadata["generator_config"]["noise_info"])
                self.assertEqual(metadata["generator_config"]["basis_gates"], ["id", "rz", "sx", "x", "cx"])
                self.assertIn("cx", testbed.noise_model.noise_instructions)
                self.assertIn("measure", testbed.noise_model.noise_instructions)

    def test_nonlocal_gate_rejected_without_rerouting(self):
        testbed = FakeBackendTestbed.generic(PROCESSORS["five_node"])
        circuit = QuantumCircuit(5)
        circuit.cx(0, 4)
        with self.assertRaises(TranspilerError):
            testbed.compile(circuit)

    def test_invalid_generator_seed(self):
        for seed in (-1, True, 1.5):
            with self.subTest(seed=seed), self.assertRaisesRegex(ValueError, "backend_seed"):
                FakeBackendTestbed.generic(PROCESSORS["five_node"], backend_seed=seed)


if __name__ == "__main__":
    unittest.main()
