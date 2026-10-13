"""Noise controls and independent analytical checks of measured fidelity."""

import unittest

from qiskit import QuantumCircuit

from qweave import BitFlipNoise, PROCESSORS, build_bell_circuit, build_ideal_bell_circuit
from qweave.measurements import bell_fidelity_interval, run_bell_measurements
from qweave.noise import compile_synthetic_circuit


class NoiseTests(unittest.TestCase):
    def test_invalid_probabilities(self):
        for field in ("single_qubit", "two_qubit", "readout"):
            for value in (-0.01, 1.01, float("nan"), float("inf"), True):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    BitFlipNoise(**{field: value})

    def test_zero_noise_matches_noiseless(self):
        for name in PROCESSORS:
            with self.subTest(processor=name):
                built = build_bell_circuit(name, measure=False)
                clean = run_bell_measurements(built.circuit, built.processor.output_ports, shots=300)
                zero = run_bell_measurements(
                    built.circuit, built.processor.output_ports, shots=300,
                    noise=BitFlipNoise(0, 0, 0),
                )
                self.assertEqual(clean.counts, zero.counts)
                self.assertEqual(zero.fidelity, 1)

    def test_compilation_preserves_edges_and_counts_swap_cost(self):
        for name in PROCESSORS:
            with self.subTest(processor=name):
                built = build_bell_circuit(name, measure=False)
                compiled = compile_synthetic_circuit(built.circuit)
                self.assertEqual(compiled.num_qubits, built.circuit.num_qubits)
                self.assertNotIn("swap", compiled.count_ops())
                swaps = built.circuit.count_ops().get("swap", 0)
                self.assertEqual(compiled.count_ops()["cx"], 1 + 3 * swaps)
                for instruction in compiled.data:
                    if len(instruction.qubits) == 2:
                        a, b = (compiled.find_bit(q).index for q in instruction.qubits)
                        self.assertTrue(built.processor.graph().has_edge(a, b))

    def test_two_qubit_noise_matches_analytical_bell_fidelity(self):
        p = 0.2
        circuit = build_ideal_bell_circuit(measure=False)
        result = run_bell_measurements(circuit, (0, 1), shots=12000, noise=BitFlipNoise(0, p, 0))
        expected = (1 - p)**2 + p**2
        self.assertAlmostEqual(result.fidelity, expected, delta=0.03)
        self.assertLessEqual(result.fidelity_interval[0], expected)
        self.assertGreaterEqual(result.fidelity_interval[1], expected)

    def test_readout_noise_matches_analytical_correlations(self):
        p = 0.1
        circuit = build_ideal_bell_circuit(measure=False)
        result = run_bell_measurements(circuit, (0, 1), shots=12000, noise=BitFlipNoise(0, 0, p))
        self.assertAlmostEqual(result.fidelity, (1 + 3 * (1 - 2 * p)**2) / 4, delta=0.03)

    def test_single_qubit_noise_applies(self):
        circuit = QuantumCircuit(2)
        circuit.x(0)
        clean = run_bell_measurements(circuit, (0, 1), shots=300)
        noisy = run_bell_measurements(circuit, (0, 1), shots=300, noise=BitFlipNoise(1, 0, 0))
        self.assertEqual(clean.correlations["ZZ"], -1)
        self.assertEqual(noisy.correlations["ZZ"], 1)

    def test_swaps_receive_noise(self):
        # There is no preparation CX: any two-qubit noise must come from SWAP.
        circuit = QuantumCircuit(2)
        circuit.x(0)
        circuit.swap(0, 1)
        noisy = run_bell_measurements(circuit, (0, 1), shots=6000, noise=BitFlipNoise(0, 0.5, 0))
        self.assertAlmostEqual(noisy.correlations["ZZ"], 0, delta=0.08)

    def test_noisy_seed_reproducibility(self):
        circuit = build_ideal_bell_circuit(measure=False)
        first = run_bell_measurements(circuit, (0, 1), shots=600, noise=BitFlipNoise(), seed=7)
        second = run_bell_measurements(circuit, (0, 1), shots=600, noise=BitFlipNoise(), seed=7)
        self.assertEqual(first.counts, second.counts)

    def test_interval_remains_nonzero_for_perfect_counts(self):
        small = bell_fidelity_interval({"XX": {"00": 10}, "YY": {"01": 10}, "ZZ": {"11": 10}})
        large = bell_fidelity_interval({"XX": {"00": 1000}, "YY": {"01": 1000}, "ZZ": {"11": 1000}})
        self.assertLess(small[0], large[0])
        self.assertLess(large[0], 1)
        self.assertEqual(large[1], 1)


if __name__ == "__main__":
    unittest.main()
