"""State preparation permits zero-site reallocation, not arbitrary-state routing."""
import unittest

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, Operator

from qweave.bell_routing import simplify_zero_input_movement, route_bell_preparation
from qweave.routing import route_circuit
from qweave.circuits import build_bell_circuit
from qweave.processors import get_processor
from qweave.verification import bell_fidelity


class MovementAuditTests(unittest.TestCase):
    def test_bell_only_router_rejects_other_logical_workloads(self):
        processor = get_processor('five_node')
        logical = QuantumCircuit(5)
        logical.h(0); logical.cx(0,4); logical.cx(0,2)
        with self.assertRaisesRegex(ValueError, 'only fixed-port'):
            route_bell_preparation(logical,processor,algorithm='shortest_path',seed=42)

    def test_prefix_swap_follows_h_and_preserves_zero_input(self):
        old = QuantumCircuit(5)
        old.h(0); old.swap(0,1); old.swap(4,3); old.cx(1,3)
        old.swap(4,3); old.swap(0,1)
        new, removed = simplify_zero_input_movement(old)
        self.assertEqual(len(removed),2)
        self.assertTrue(Statevector.from_instruction(old).equiv(Statevector.from_instruction(new)))
        self.assertFalse(Operator(old).equiv(Operator(new)))
        self.assertAlmostEqual(bell_fidelity(new,(0,4)),1.)

    def test_unitary_route_is_preserved_but_bell_builder_is_simplified(self):
        processor = get_processor('five_node')
        logical = QuantumCircuit(5)
        logical.h(0); logical.cx(0,4)
        general, _ = route_circuit(logical,processor)
        bell = build_bell_circuit(processor,measure=False)
        self.assertEqual(general.count_ops()['swap'],4)
        self.assertEqual(bell.circuit.count_ops()['swap'],2)
        self.assertTrue(Statevector.from_instruction(general).equiv(Statevector.from_instruction(bell.circuit)))
        self.assertEqual(bell.routing.benchmark,'zero-input-fixed-output-bell-v3')

    def test_only_zero_zero_swaps_are_removed_after_entangling(self):
        circuit = QuantumCircuit(5)
        circuit.h(0); circuit.cx(0,1); circuit.swap(2,3); circuit.swap(1,4)
        new, removed = simplify_zero_input_movement(circuit)
        self.assertEqual(removed,(2,))
        self.assertEqual(new.count_ops()['swap'],1)
        self.assertTrue(Statevector.from_instruction(circuit).equiv(Statevector.from_instruction(new)))
