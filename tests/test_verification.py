"""Checks of Bell coherence and physical output placement."""

from contextlib import redirect_stdout
from io import StringIO
from math import isclose
import unittest
from unittest.mock import patch

from qiskit import QuantumCircuit

from qweave import PROCESSORS, bell_fidelity, build_bell_circuit, build_ideal_bell_circuit
from qweave.cli import main
from qweave.verification import BELL_FIDELITY_TOLERANCE, MAX_STATEVECTOR_QUBITS


class BellVerificationTests(unittest.TestCase):
    def test_ideal_reference(self):
        circuit = build_ideal_bell_circuit(measure=False)
        self.assertAlmostEqual(bell_fidelity(circuit, (0, 1)), 1.0, delta=1e-10)

    def test_all_physical_baselines(self):
        for name in PROCESSORS:
            with self.subTest(processor=name):
                built = build_bell_circuit(name, measure=False)
                fidelity = bell_fidelity(built.circuit, built.processor.output_ports)
                self.assertTrue(isclose(fidelity, 1.0, abs_tol=BELL_FIDELITY_TOLERANCE, rel_tol=0))

    def test_phase_error_is_detected(self):
        built = build_bell_circuit("five_node", measure=False)
        built.circuit.z(built.processor.output_ports[0])
        self.assertAlmostEqual(
            bell_fidelity(built.circuit, built.processor.output_ports), 0.0, delta=1e-10
        )

    def test_wrong_output_pair_fails(self):
        built = build_bell_circuit("five_node", measure=False)
        self.assertAlmostEqual(bell_fidelity(built.circuit, (0, 1)), 0.25, delta=1e-10)

    def test_invalid_ports(self):
        circuit = build_ideal_bell_circuit(measure=False)
        for ports in ((0, 0), (-1, 1), (0, 2), (0,), (0, 1, 2), (0, 1.0)):
            with self.subTest(ports=ports), self.assertRaisesRegex(ValueError, "ports"):
                bell_fidelity(circuit, ports)

    def test_measurements_rejected(self):
        with self.assertRaisesRegex(ValueError, "unmeasured"):
            bell_fidelity(build_ideal_bell_circuit(), (0, 1))

    def test_resource_limit_precedes_simulation(self):
        circuit = QuantumCircuit(MAX_STATEVECTOR_QUBITS + 1)
        with patch("qweave.verification.Statevector.from_instruction") as simulate:
            with self.assertRaisesRegex(ValueError, "resource limit"):
                bell_fidelity(circuit, (0, 1))
            simulate.assert_not_called()

    def test_cli_fails_for_incorrect_state(self):
        output = StringIO()
        with patch("sys.argv", ["qweave", "--processor", "five_node"]), \
                patch("qweave.cli.bell_fidelity", return_value=0.0), \
                redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            main()
        self.assertEqual(raised.exception.code, 1)
        self.assertIn("FAIL", output.getvalue())


if __name__ == "__main__":
    unittest.main()
