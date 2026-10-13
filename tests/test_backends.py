"""Verify the notebook's fake backend supplies topology, native target and noise."""

from dataclasses import asdict
import json
import unittest

from qiskit import QuantumCircuit
from qiskit.transpiler.exceptions import TranspilerError

from qweave import (
    PROCESSORS, FakeBackendTestbed, bell_fidelity,
    build_bell_circuit, run_bell_measurements,
)
from qweave.cli import _result_record


class FakeBackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.testbed = FakeBackendTestbed.sherbrooke()
        cls.built = build_bell_circuit(cls.testbed.processor((0, 15)), measure=False)

    def test_matches_notebook_and_processor(self):
        self.assertEqual(self.testbed.snapshot.backend_class, "FakeSherbrooke")
        self.assertEqual(self.testbed.snapshot.num_qubits, 127)
        self.assertEqual(self.built.processor.edges, PROCESSORS["ibm_heavy_hex"].edges)
        calibration = [p for p in self.testbed.gate_calibrations() if p.name == "ecr"]
        self.assertTrue(all(p.duration_seconds > 0 for p in calibration))
        self.assertGreater(len({p.error for p in calibration}), 1)
        self.assertIn("ecr", self.testbed.noise_model.noise_instructions)
        self.assertIn("measure", self.testbed.noise_model.noise_instructions)

    def test_reproducible_snapshot_identity(self):
        other = FakeBackendTestbed.sherbrooke()
        self.assertEqual(self.testbed.snapshot, other.snapshot)
        self.assertEqual(len(self.testbed.snapshot.snapshot_sha256), 64)
        json.dumps(asdict(self.testbed.snapshot))

    def test_native_ideal_fidelity_and_route(self):
        native = self.testbed.compile(self.built.circuit)
        self.assertAlmostEqual(bell_fidelity(native, (0, 15)), 1, delta=1e-10)
        self.assertEqual(native.layout.final_index_layout(), list(range(127)))
        route_edges = {frozenset(edge) for edge in zip(self.built.route, self.built.route[1:])}
        for instruction in native.data:
            qubits = tuple(native.find_bit(q).index for q in instruction.qubits)
            self.assertTrue(self.testbed.target.instruction_supported(
                operation_name=instruction.operation.name, qargs=qubits
            ))
            if len(qubits) == 2:
                self.assertIn(frozenset(qubits), route_edges)
        self.assertLessEqual(native.count_ops().get("ecr", 0), 1 + 3 * self.built.circuit.count_ops()["swap"])

    def test_same_native_circuits_for_clean_and_calibrated_noise(self):
        clean = run_bell_measurements(self.built.circuit, (0, 15), testbed=self.testbed, shots=300)
        noisy = run_bell_measurements(
            self.built.circuit, (0, 15), testbed=self.testbed, backend_noise=True, shots=300,
        )
        repeat = run_bell_measurements(
            self.built.circuit, (0, 15), testbed=self.testbed, backend_noise=True, shots=300,
        )
        self.assertEqual(clean.fidelity, 1)
        self.assertLess(noisy.fidelity, 1)
        self.assertEqual(noisy.counts, repeat.counts)
        self.assertIsNone(clean.noise)
        self.assertEqual(noisy.noise, self.testbed.snapshot)
        self.assertEqual(clean.testbed, noisy.testbed)
        for basis in clean.circuits:
            self.assertEqual(clean.circuits[basis], noisy.circuits[basis])
            self.assertEqual(sum(noisy.counts[basis].values()), 100)
            native = noisy.circuits[basis]
            measured = [(native.find_bit(i.qubits[0]).index, native.find_bit(i.clbits[0]).index)
                        for i in native.data if i.operation.name == "measure"]
            self.assertEqual(measured, [(0, 0), (15, 1)])
        record = json.loads(json.dumps(_result_record(noisy)))
        self.assertEqual(record["testbed"]["snapshot_sha256"], self.testbed.snapshot.snapshot_sha256)
        self.assertIn("OPENQASM 3", record["circuits"]["ZZ"]["qasm3"])

    def test_nonlocal_interaction_cannot_be_silently_rerouted(self):
        circuit = QuantumCircuit(127)
        circuit.cx(0, 126)
        with self.assertRaises(TranspilerError):
            self.testbed.compile(circuit)

    def test_rejects_mismatched_width_and_unsupported_idle_model(self):
        with self.assertRaisesRegex(ValueError, "width"):
            self.testbed.compile(QuantumCircuit(16))
        circuit = QuantumCircuit(127)
        circuit.delay(100, 0)
        with self.assertRaisesRegex(ValueError, "idle"):
            self.testbed.compile(circuit)

    def test_noise_configuration_is_unambiguous(self):
        with self.assertRaisesRegex(ValueError, "requires"):
            run_bell_measurements(self.built.circuit, (0, 15), backend_noise=True)

    def test_exact_verification_discards_only_unused_sites(self):
        circuit = QuantumCircuit(127)
        self.assertAlmostEqual(bell_fidelity(circuit, (0, 126)), 0.5)
        circuit.h(0)
        circuit.cx(0, 126)
        self.assertAlmostEqual(bell_fidelity(circuit, (0, 126)), 1)


if __name__ == "__main__":
    unittest.main()
