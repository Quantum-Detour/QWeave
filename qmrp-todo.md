# QWeave: Build Checklist

Compare four quantum routing methods across three processor models, then explore their results through a Quantum Packet Tracer and research dashboard. Detailed explanations are in [qmrp-project-overview.md](qmrp-project-overview.md).

**Current progress:** The noiseless Bell baseline is verified on all three provisional graphs: exact and measured fidelity are 1.0, and all 15 tests passed. Official graph/port confirmation and a verified hyperbolic tiling remain pending.

## 1. Topologies and Bell baseline

- [ ] Confirm the five-node, IBM heavy-hex, and hyperbolic graph definitions, fixed output ports, and allowed gate directions.
- [ ] Plot each complete hardware graph with its selected route beside the circuit diagram.
- [x] Build the shortest-path Bell circuit and verify ideal output fidelity with Qiskit on all three provisional graphs.
- [ ] Check every circuit interaction against the graph and allowed gate directions.
- [x] Add XX, YY, and ZZ measurement circuits and calculate Bell fidelity: F = (1 + ⟨XX⟩ − ⟨YY⟩ + ⟨ZZ⟩) / 4.
- [ ] Add uncertainty to the measured Bell fidelity.

## 2. Four routing methods

- [x] A — Original: deterministic shortest-path routing with explicit SWAPs for the Bell baseline.
- [ ] B — Qiskit built-in: SABRE routing with reproducible settings.
- [ ] C — Noise-aware: routing with explicit edge-error costs.
- [ ] D — QMRP: encode across two qubits, find capacity-constrained disjoint routes, decode, and postselect using the parity syndrome.
- [ ] Track logical-qubit placement and workspace; use separate launch/arrival sites and record shortest-path fallbacks when protection is infeasible.
- [ ] Verify noiseless correctness across all methods, detection of single bit flips, and the limitations of the parity check.

## 3. Noisy comparison and research

- [ ] Run all four methods on all three models with matched ports, placement constraints, noise assumptions, and attempted-shot budgets; retain a separate ideal reference.
- [ ] Include noise on native gates, encoding/decoding, and readout. Start with bit flips, then test depolarizing noise and relaxation.
- [ ] Report fidelity, depth, native two-qubit gates, SWAPs, physical qubits, runtime, accepted/discarded shots, and protection coverage.
- [ ] Sweep noise and port distance to find where QMRP helps or hurts; compare with all baselines and encoded execution without postselection.
- [ ] Save configurations, seeds, versions, counts, and traces. Include a separate feasible protection experiment if QMRP cannot protect a required topology.

## 4. Reusable circuit support

- [ ] Accept supported QASM uploads and Qiskit circuits; validate operations, parameters, and size limits.
- [ ] Reuse the routing pipeline for uploaded circuits, with explicit fallback and support messages.
- [ ] Select an appropriate quality metric for each circuit and verify a phase-sensitive non-Bell example.

## 5. Dashboard and Quantum Packet Tracer

- [ ] Add circuit upload/presets, topology/port selection, noise/shot controls, run-one/run-all actions, and result export.
- [ ] Build graph playback with play/pause, forward/backward steps, scrubbing, speed control, and node/edge inspection.
- [ ] Animate gates, SWAPs, blue/orange QMRP paths, encoding/decoding, recorded syndrome pass/reject outcomes, and fallbacks; support replay of all four methods.
- [ ] Add four-way quality/cost charts, acceptance and coverage, plus noise/distance break-even views linked to individual replays.

## 6. Final validation and delivery

- [ ] Check output ports, unsupported inputs, unavailable routes, zero accepted shots, and agreement between traces and recorded runs.
- [ ] Produce a reproducible notebook, setup instructions, comparison results, and one evidence-backed routing or hardware recommendation.
- [ ] Demonstrate the Bell benchmark and a supported uploaded circuit through the complete dashboard.

**Reporting rule:** Show accepted fidelity alongside yield and uncertainty. A passed syndrome does not guarantee an error-free state; zero accepted shots means fidelity is undefined.
