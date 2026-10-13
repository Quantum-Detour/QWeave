"""Check measurement bases, physical ports, and shot-based estimation."""

import unittest
from math import pi

from qiskit import QuantumCircuit

from qweave import (
    PROCESSORS, bell_fidelity, build_bell_circuit,
    build_bell_measurement_circuits, measured_bell_fidelity, run_bell_measurements,
)


class BellMeasurementTests(unittest.TestCase):
    def test_all_processors(self):
        for name in PROCESSORS:
            with self.subTest(processor=name):
                built = build_bell_circuit(name, measure=False)
                original = built.circuit.copy()
                result = run_bell_measurements(built.circuit, built.processor.output_ports, shots=301)
                self.assertEqual(result.correlations, {"XX": 1.0, "YY": -1.0, "ZZ": 1.0})
                self.assertEqual(result.fidelity, 1.0)
                self.assertEqual(result.shots_by_basis, {"XX": 101, "YY": 100, "ZZ": 100})
                for basis in result.counts:
                    self.assertEqual(sum(result.counts[basis].values()), result.shots_by_basis[basis])
                self.assertEqual(built.circuit, original)

    def test_phase_error(self):
        built = build_bell_circuit("five_node", measure=False)
        built.circuit.z(0)
        result = run_bell_measurements(built.circuit, (0, 4), shots=300)
        self.assertEqual(result.correlations, {"XX": -1.0, "YY": 1.0, "ZZ": 1.0})
        self.assertEqual(result.fidelity, 0.0)

    def test_nonclifford_sampling_matches_exact_and_repeats(self):
        built = build_bell_circuit("five_node", measure=False)
        built.circuit.rz(pi / 3, 0)
        first = run_bell_measurements(built.circuit, (0, 4), shots=12000, seed=17)
        second = run_bell_measurements(built.circuit, (0, 4), shots=12000, seed=17)
        self.assertEqual(first.counts, second.counts)
        self.assertAlmostEqual(first.fidelity, bell_fidelity(built.circuit, (0, 4)), delta=0.04)

    def test_product_state(self):
        result = run_bell_measurements(QuantumCircuit(2), (0, 1), shots=12000)
        self.assertAlmostEqual(result.fidelity, 0.5, delta=0.04)

    def test_count_formula_and_no_clipping(self):
        counts = {
            "XX": {"00": 30, "11": 30, "01": 20, "10": 20},
            "YY": {"00": 10, "11": 10, "01": 40, "10": 40},
            "ZZ": {"00": 50, "11": 50},
        }
        self.assertAlmostEqual(measured_bell_fidelity(counts), 0.7)
        self.assertEqual(measured_bell_fidelity({
            "XX": {"01": 1}, "YY": {"00": 1}, "ZZ": {"01": 1}
        }), -0.5)

    def test_invalid_counts(self):
        for counts in (
            {}, {"XX": {}, "YY": {"00": 1}, "ZZ": {"00": 1}},
            {"XX": {"000": 1}, "YY": {"00": 1}, "ZZ": {"00": 1}},
            {"XX": {"00": -1}, "YY": {"00": 1}, "ZZ": {"00": 1}},
        ):
            with self.subTest(counts=counts), self.assertRaises(ValueError):
                measured_bell_fidelity(counts)

    def test_invalid_inputs(self):
        with self.assertRaisesRegex(ValueError, "unmeasured"):
            built = build_bell_circuit("five_node")
            build_bell_measurement_circuits(built.circuit, (0, 4))
        with self.assertRaisesRegex(ValueError, "classical"):
            build_bell_measurement_circuits(QuantumCircuit(2, 1), (0, 1))
        for kwargs in ({"shots": 2}, {"shots": True}, {"seed": -1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                run_bell_measurements(QuantumCircuit(2), (0, 1), **kwargs)


if __name__ == "__main__":
    unittest.main()
