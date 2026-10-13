"""Ideal gate translation and measurement uncertainty."""

import unittest

from qweave import PROCESSORS, build_bell_circuit
from qweave.measurements import bell_fidelity_interval
from qweave.compilation import compile_ideal_circuit


class NoiseTests(unittest.TestCase):
    def test_compilation_preserves_edges_and_counts_swap_cost(self):
        for name in PROCESSORS:
            with self.subTest(processor=name):
                built = build_bell_circuit(name, measure=False)
                compiled = compile_ideal_circuit(built.circuit)
                self.assertEqual(compiled.num_qubits, built.circuit.num_qubits)
                self.assertNotIn("swap", compiled.count_ops())
                swaps = built.circuit.count_ops().get("swap", 0)
                self.assertEqual(compiled.count_ops()["cx"], 1 + 3 * swaps)
                for instruction in compiled.data:
                    if len(instruction.qubits) == 2:
                        a, b = (compiled.find_bit(q).index for q in instruction.qubits)
                        self.assertTrue(built.processor.graph().has_edge(a, b))

    def test_interval_remains_nonzero_for_perfect_counts(self):
        small = bell_fidelity_interval({"XX": {"00": 10}, "YY": {"01": 10}, "ZZ": {"11": 10}})
        large = bell_fidelity_interval({"XX": {"00": 1000}, "YY": {"01": 1000}, "ZZ": {"11": 1000}})
        self.assertLess(small[0], large[0])
        self.assertLess(large[0], 1)
        self.assertEqual(large[1], 1)


if __name__ == "__main__":
    unittest.main()
