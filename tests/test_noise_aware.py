"""Native-cost accounting, weighted routing, and shared-pipeline regressions."""

from dataclasses import asdict
from math import inf, log1p
import json
import unittest
from unittest.mock import patch

from qiskit import QuantumCircuit

from qweave import OptimizationLevel, BackendOperationCosts, FakeBackendTestbed, PROCESSORS, Processor, bell_fidelity, build_bell_circuit
from qweave.costs import OperationCost
from qweave.measurements import prepare_bell_measurements, sample_bell_measurements
from qweave.routing import route_circuit


class ControlledCosts:
    model = "controlled-test"
    backend_fingerprint = "test"
    preparation_seconds = 0.0

    def __init__(self, overrides=None, default=1.0):
        self.overrides = overrides or {}
        self.default = default

    def validate_processor(self, processor):
        pass

    def operation(self, name, u, v):
        return OperationCost(name, (u, v), self.overrides.get((name, u, v), self.default), ())


def topology(edges, n=5, ports=(0, 4)):
    return Processor("controlled", "controlled", n, tuple(edges), ports, "test")


class WeightedRoutingTests(unittest.TestCase):
    def test_longer_cleaner_route_and_error_sensitivity(self):
        processor = topology(((0, 1), (1, 4), (0, 2), (2, 3), (3, 4)))
        costs = ControlledCosts({("swap", 1, 4): 10.0})
        with patch("qiskit_aer.AerSimulator.run", side_effect=AssertionError("Route selection must not execute")):
            chosen = build_bell_circuit(processor, measure=False, algorithm="noise_aware", costs=costs)
        self.assertEqual(chosen.routing.routing_swaps, ((2, 3), (3, 4)))
        self.assertEqual(chosen.routing.estimated_routing_cost, 3.0)
        self.assertAlmostEqual(bell_fidelity(chosen.circuit, processor.output_ports), 1)
        changed = build_bell_circuit(processor, measure=False, algorithm="noise_aware", costs=ControlledCosts())
        self.assertEqual(changed.routing.routing_swaps, ((1, 4),))

    def test_ordered_costs_and_restoration_arguments(self):
        processor = topology(((0, 1), (1, 2)), n=3, ports=(0, 2))
        costs = ControlledCosts({("swap", 2, 1): 5, ("swap", 1, 2): 10, ("cx", 0, 1): 3})
        built = build_bell_circuit(processor, measure=False, algorithm="noise_aware", costs=costs)
        self.assertEqual(built.routing.estimated_routing_cost, 13)
        self.assertEqual(built.routing.restoration_swaps, ())
        self.assertEqual(built.routing.routing_swaps, ((1, 2),))
        decision = built.routing.cost_decisions[0]
        self.assertEqual(decision["restoration_swaps"], [])
        self.assertEqual(decision["transport_swaps"][0]["qubits"], (1, 2))

    def test_tree_equal_zero_adjacent_and_unavailable(self):
        tree = PROCESSORS["five_node"]
        shortest = build_bell_circuit(tree, measure=False)
        for value in (0.0, 1.0):
            result = build_bell_circuit(tree, measure=False, algorithm="noise_aware", costs=ControlledCosts(default=value))
            self.assertEqual(shortest.circuit, result.circuit)
        adjacent = topology(((0, 1),), n=2, ports=(0, 1))
        built = build_bell_circuit(adjacent, measure=False, algorithm="noise_aware", costs=ControlledCosts())
        self.assertEqual(built.routing.routing_swaps, ())
        self.assertEqual(built.routing.estimated_routing_cost, 1)
        with self.assertRaisesRegex(ValueError, "finite-cost"):
            build_bell_circuit(tree, algorithm="noise_aware", costs=ControlledCosts(default=inf))
        with self.assertRaisesRegex(ValueError, "requires"):
            build_bell_circuit(tree, algorithm="noise_aware")
        with self.assertRaisesRegex(ValueError, "disconnected"):
            build_bell_circuit(topology(((0, 1),), n=3, ports=(0, 2)), algorithm="noise_aware", costs=ControlledCosts())

    def test_zero_weight_cycles_and_reproducibility(self):
        processor = topology(((0, 1), (1, 4), (0, 2), (2, 3), (3, 4), (1, 3)))
        first = build_bell_circuit(processor, algorithm="noise_aware", costs=ControlledCosts(default=0))
        repeat = build_bell_circuit(processor, algorithm="noise_aware", costs=ControlledCosts(default=0))
        self.assertEqual(first.circuit, repeat.circuit)
        self.assertEqual(first.routing.cost_decisions, repeat.routing.cost_decisions)

    def test_shared_path_router_regression(self):
        processor = PROCESSORS["five_node"]
        a = build_bell_circuit(processor, measure=False)
        b = build_bell_circuit(processor, measure=False, algorithm="sabre")
        self.assertEqual(a.routing.routing_swaps, ((1, 3), (3, 4)))
        self.assertEqual(b.routing.routing_swaps, ((3, 4), (1, 0)))
        for built in (a, b):
            self.assertEqual(tuple(built.routing.final_layout[p] for p in (0,4)), (0,4))
            self.assertAlmostEqual(bell_fidelity(built.circuit, (0, 4)), 1)

    def test_multiple_cx_tracks_placement(self):
        processor = PROCESSORS["five_node"]
        circuit = QuantumCircuit(5)
        circuit.h(0)
        circuit.cx(0, 4)
        circuit.cx(0, 2)
        circuit.cx(0, 2)
        routed, info = route_circuit(circuit, processor, algorithm="noise_aware", costs=ControlledCosts())
        self.assertEqual(len(info.cost_decisions), 3)
        self.assertAlmostEqual(bell_fidelity(routed, (0, 4)), 1)


class NativeCostTests(unittest.TestCase):
    def test_native_cost_cache_and_bad_error_values(self):
        bed = FakeBackendTestbed.for_processor("five_node")
        costs = BackendOperationCosts(bed)
        with patch.object(bed, "compile", wraps=bed.compile) as compile_operation:
            operation = costs.operation("swap", 1, 0)
            self.assertIs(operation, costs.operation("swap", 1, 0))
            self.assertEqual(compile_operation.call_count, 1)
        expected = 2 * -log1p(-bed.target["cx"][(1, 0)].error) - log1p(-bed.target["cx"][(0, 1)].error)
        self.assertAlmostEqual(operation.cost, expected)
        self.assertEqual(len(operation.native_gates), 3)
        props = bed.target["cx"][(0, 1)]
        original = props.error
        try:
            for error in (None, float("nan"), -0.1, 1.1):
                props.error = error
                with self.subTest(error=error), self.assertRaisesRegex(ValueError, "gate error"):
                    BackendOperationCosts(bed).operation("cx", 0, 1)
            props.error = 0
            self.assertEqual(BackendOperationCosts(bed).operation("cx", 0, 1).cost, 0)
            props.error = 1
            self.assertEqual(BackendOperationCosts(bed).operation("cx", 0, 1).cost, inf)
        finally:
            props.error = original
        with self.assertRaisesRegex(ValueError, "connectivity"):
            costs.validate_processor(topology(((0, 1),), n=2, ports=(0, 1)))

    def test_all_backends_exact_cost_and_shared_execution(self):
        for name in PROCESSORS:
            with self.subTest(processor=name):
                bed = FakeBackendTestbed.for_processor(name, optimization_level=OptimizationLevel.NONE)
                processor = bed.processor(PROCESSORS[name].output_ports, name=name)
                costs = BackendOperationCosts(bed)
                built = build_bell_circuit(processor, measure=False, algorithm="noise_aware", costs=costs)
                self.assertAlmostEqual(bell_fidelity(built.circuit, processor.output_ports), 1)
                native = bed.compile(built.circuit)
                self.assertAlmostEqual(bell_fidelity(native, processor.output_ports), 1)
                self.assertEqual(tuple(built.routing.final_layout[p] for p in processor.output_ports), processor.output_ports)
                # Sum actual native errors, including the common H preparation.
                native_cost = sum(-log1p(-bed.target[item.operation.name][tuple(native.find_bit(q).index for q in item.qubits)].error) for item in native.data)
                h = QuantumCircuit(processor.num_qubits)
                h.h(processor.output_ports[0])
                h_native = bed.compile(h)
                h_cost = sum(-log1p(-bed.target[item.operation.name][tuple(h_native.find_bit(q).index for q in item.qubits)].error) for item in h_native.data)
                self.assertAlmostEqual(native_cost - h_cost, built.routing.estimated_routing_cost, places=10)
                json.dumps(asdict(built.routing), allow_nan=False)
                prepared = prepare_bell_measurements(built.circuit, processor.output_ports, testbed=bed)
                clean = sample_bell_measurements(prepared, testbed=bed, shots=30)
                noisy = sample_bell_measurements(prepared, testbed=bed, backend_noise=True, shots=30)
                self.assertIs(clean.circuits, noisy.circuits)
                self.assertEqual(clean.shots_by_basis, noisy.shots_by_basis)
                self.assertEqual(clean.testbed, noisy.testbed)
                self.assertEqual(clean.seed, noisy.seed)
                self.assertEqual(clean.fidelity, 1)
                self.assertEqual(built.routing.cost_backend_fingerprint, bed.snapshot.snapshot_sha256)


if __name__ == "__main__":
    unittest.main()
