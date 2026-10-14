"""QMRP topology, syndrome semantics, and shared measurement regressions."""
import unittest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from qweave.processors import PROCESSOR_CONFIGS, Processor
from qweave.circuits import build_bell_circuit
from qweave.costs import OperationCost
from qweave.protection import select_qmrp_plan, _flow_paths
from qweave.measurements import run_bell_measurements, build_bell_measurement_circuits, summarize_measurements
from qweave.verification import bell_fidelity, syndrome_zero_probability
from qweave.backends import FakeBackendTestbed
from qweave.costs import BackendOperationCosts


def processor(name):
    config = PROCESSOR_CONFIGS[name]
    return Processor(name, name, config.num_qubits, config.edges, config.output_ports, config.provenance)


class UniformCosts:
    preparation_seconds = 0.
    model = 'test-directed-costs'
    backend_fingerprint = 'test'
    compiler_settings = {}

    def validate_processor(self, processor):
        pass

    def operation(self, name, u, v):
        return OperationCost(name, (u, v), 3. if name == 'swap' else 1., ())


class ProtectionTests(unittest.TestCase):
    def setUp(self):
        self.processor = processor('five_node_multipath')
        self.costs = UniformCosts()
        self.built = build_bell_circuit(self.processor, measure=False, algorithm='qmrp', costs=self.costs)

    def test_custom_graph_and_original_preserved(self):
        self.assertEqual(set(self.processor.edges), {(0,1),(1,2),(2,3),(3,4),(4,1)})
        self.assertEqual(PROCESSOR_CONFIGS['five_node'].edges, ((0,1),(1,2),(1,3),(3,4)))
        self.assertEqual(self.processor.output_ports, (0,4))
        self.assertIn('not a confirmed organizer', self.processor.provenance)

    def test_paths_preposition_cost_and_ideal(self):
        plan = self.built.routing.protection
        self.assertEqual(plan['paths'], ((1,4),(2,3)))
        self.assertEqual(plan['preposition_path'], ())
        self.assertFalse(set(plan['paths'][0]) & set(plan['paths'][1]))
        self.assertEqual(plan['cost'], 9.)  # two outward SWAPs and three CXs
        self.assertEqual(self.built.circuit.count_ops()['swap'], 2)
        self.assertEqual(self.built.routing.final_layout[4], 4)
        self.assertAlmostEqual(bell_fidelity(self.built.circuit, (0,4)), 1.)
        self.assertAlmostEqual(syndrome_zero_probability(self.built.circuit, (0,4)), 1.)
        again = select_qmrp_plan(self.processor, self.costs)
        self.assertEqual(again['paths'], plan['paths'])
        for item in self.built.circuit.data:
            if len(item.qubits) == 2 and item.operation.name != 'barrier':
                self.assertTrue(self.processor.graph().has_edge(*(self.built.circuit.find_bit(q).index for q in item.qubits)))

    def test_native_compilation_and_postselection(self):
        bed = FakeBackendTestbed.for_processor('five_node_multipath')
        built = build_bell_circuit(self.processor, measure=False, algorithm='qmrp', costs=BackendOperationCosts(bed))
        native = bed.compile(built.circuit)
        self.assertAlmostEqual(bell_fidelity(native, (0,4)), 1.)
        self.assertAlmostEqual(syndrome_zero_probability(native, (0,4)), 1.)
        result = run_bell_measurements(built.circuit, (0,4), shots=99, testbed=bed)
        self.assertEqual(result.fidelity, 1.)
        self.assertEqual(result.accepted_by_basis, dict.fromkeys(('XX','YY','ZZ'),33))
        self.assertEqual(result.syndrome_sites, (3,))
        self.assertEqual(result.unconditional_fidelity, 1.)

    def _fault(self, operations):
        circuit = self.built.circuit.copy_empty_like()
        inserted = False
        for item in self.built.circuit.data:
            if item.operation.name == 'cx' and tuple(self.built.circuit.find_bit(q).index for q in item.qubits) == (4,3):
                for gate, site in operations:
                    getattr(circuit, gate)(site)
                inserted = True
            circuit.append(item.operation, [self.built.circuit.find_bit(q).index for q in item.qubits])
        self.assertTrue(inserted)
        return circuit

    def test_error_detection_and_limitations(self):
        for site in (3,4):
            result = run_bell_measurements(self._fault([('x',site)]), (0,4), shots=90)
            self.assertIsNone(result.fidelity)
            self.assertIsNone(result.fidelity_interval)
            self.assertEqual(sum(result.accepted_by_basis.values()),0)
        for errors in ([('z',3)], [('z',4)], [('x',3),('x',4)]):
            result = run_bell_measurements(self._fault(errors), (0,4), shots=90)
            self.assertEqual(result.fidelity,0.)
            self.assertEqual(sum(result.accepted_by_basis.values()),90)
        result = run_bell_measurements(self._fault([('z',3),('z',4)]), (0,4), shots=90)
        self.assertEqual(result.fidelity,1.)

    def test_analytical_independent_bit_flips(self):
        p1, p2 = .13, .27
        acceptance = correct = 0.
        for x1 in (False,True):
            for x2 in (False,True):
                weight = (p1 if x1 else 1-p1)*(p2 if x2 else 1-p2)
                c = self._fault([('x',site) for flag,site in ((x1,4),(x2,3)) if flag])
                state = Statevector.from_instruction(c)
                pzero = state.probabilities([3])[0]
                acceptance += weight*pzero
                correct += weight*pzero*bell_fidelity(c,(0,4))
        expected = (1-p1)*(1-p2)+p1*p2
        self.assertAlmostEqual(acceptance,expected)
        self.assertAlmostEqual(correct/acceptance,(1-p1)*(1-p2)/expected)

    def test_tree_fallback(self):
        tree = processor('five_node')
        built = build_bell_circuit(tree, measure=False, algorithm='qmrp', costs=self.costs)
        baseline = build_bell_circuit(tree, measure=False)
        self.assertEqual(built.circuit, baseline.circuit)
        self.assertEqual(built.routing.protection['status'], 'unprotected_fallback')

    def test_joint_count_parsing_and_partial_zero_acceptance(self):
        circuits = build_bell_measurement_circuits(self.built.circuit,(0,4))
        raw = {'XX': {'0 00': 8, '1 01':2}, 'YY': {'001':7,'100':3}, 'ZZ': {'1 11':10}}
        result = summarize_measurements(raw,circuits,dict.fromkeys(raw,10))
        self.assertEqual(result.accepted_by_basis,{'XX':8,'YY':7,'ZZ':0})
        self.assertIsNone(result.fidelity)
        self.assertIsNone(result.correlations['ZZ'])
        self.assertEqual(result.unconditional_counts['ZZ'],{'11':10})

    def test_exchanged_endpoints_and_directed_flow_costs(self):
        import networkx as nx
        graph = nx.DiGraph()
        graph.add_edge(1,3,cost=1.); graph.add_edge(2,4,cost=1.)
        graph.add_edge(1,4,cost=10.); graph.add_edge(2,3,cost=10.)
        self.assertEqual(_flow_paths(graph,(1,2),(4,3)),((1,3),(2,4)))
        # Code symmetry permits either component to arrive at the data port.
        c = QuantumCircuit(5)
        c.h(0); c.cx(0,1); c.cx(1,2); c.swap(1,3); c.swap(2,4); c.cx(4,3)
        self.assertAlmostEqual(bell_fidelity(c,(0,4)),1.)

    def test_routed_encoding_used_when_adjacent_launch_infeasible(self):
        # Constrain the launch candidate to exercise non-adjacent routed encoding.
        p = Processor('fixture','fixture',6,((0,1),(1,2),(2,4),(1,3),(3,5),(5,4)),(0,4),'test')
        from unittest.mock import patch
        from qweave.protection import _flow_paths as actual_flow
        def distant_launch(graph, launches, arrivals):
            return actual_flow(graph, launches, arrivals) if launches[1] == 5 else None
        with patch('qweave.protection._flow_paths', side_effect=distant_launch):
            built = build_bell_circuit(p,measure=False,algorithm='qmrp',costs=self.costs)
        self.assertGreater(len(built.routing.protection['encoding_path']),1)
        self.assertEqual(built.routing.protection['status'],'protected')
        self.assertEqual(built.routing.final_layout[4],4)
        self.assertAlmostEqual(bell_fidelity(built.circuit,(0,4)),1.)
        self.assertAlmostEqual(syndrome_zero_probability(built.circuit,(0,4)),1.)


if __name__ == '__main__':
    unittest.main()
