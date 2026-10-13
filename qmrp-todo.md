# QWeave: Build Checklist

Compare four quantum routing methods across three processor models, then explore their results through a Quantum Packet Tracer and research dashboard. Detailed explanations are in [qmrp-project-overview.md](qmrp-project-overview.md).

**Current progress:** Shortest path, SABRE, and noise-aware routing now share logical Bell preparation, fixed initial placement, output restoration, native compilation, measurements, noise, and reporting. Five-node and the frozen 85-cell HYPERTILING {7,3} model use seeded GenericBackendV2 properties; IBM uses the supplied notebook's 127-qubit FakeSherbrooke snapshot. Manual bit-flip controls have been removed. Measurement results include conservative 95% sampling intervals. The compiler now defaults to named MAXIMUM optimization (Qiskit level 3) for all methods, with fixed layout, no rerouting, and exact synthesis. All 42 tests pass. All nine A/B/C processor combinations passed exact-fidelity and report-consistency checks at maximum optimization with 3,072 shots per arm. The radial placeholder has been replaced with a generated cell-adjacency lattice (interior degree 7), frozen ports (5, 31), generator metadata and a graph fingerprint. Organizer confirmation of graph/ports and QMRP protection remain pending.

## 1. Topologies and Bell baseline

- [ ] Confirm the five-node, IBM heavy-hex, and hyperbolic graph definitions, fixed output ports, and allowed gate directions.
- [x] Replace the radial placeholder with a frozen HYPERTILING {7,3} cell-adjacency graph; record generator/version/parameters, edges, ports and SHA256.
- [ ] Plot each complete hardware graph with its selected route beside the circuit diagram.
- [x] Build the shortest-path Bell circuit and verify ideal output fidelity with Qiskit on all three provisional graphs.
- [x] Check every compiled two-qubit interaction against graph edges in tests under the current synthetic bidirectional-CX convention.
- [ ] Validate interactions against organizer-confirmed graphs and native gate directions.
- [x] Validate compiled IBM baseline operations and fixed placement against FakeSherbrooke's native target; verify ideal fidelity after native translation.
- [x] Add XX, YY, and ZZ measurement circuits and calculate Bell fidelity: F = (1 + ⟨XX⟩ − ⟨YY⟩ + ⟨ZZ⟩) / 4.
- [x] Add conservative 95% sampling intervals to measured Bell fidelity using simultaneous Hoeffding bounds.

## 2. Four routing methods

- [x] A — Original: deterministic shortest-path routing with explicit SWAPs for the Bell baseline.
- [x] B — Qiskit built-in: SabreSwap with fixed seed, decay heuristic, and one trial; shared Bell pipeline with shortest path.
- [x] Validate fixed-port ideal correctness and native compilation on all three models; check restoration costs, deterministic routing, and shared clean/noisy execution.
- [x] Use a shared OptimizationLevel enum, maximum optimization by default, and recorded compiler settings for execution and routing-cost estimation.
- [x] C — Noise-aware: weighted Dijkstra using cached native CX/SWAP error costs from the same backend, including shared output restoration.
- [ ] D — QMRP: encode across two qubits, find capacity-constrained disjoint routes, decode, and postselect using the parity syndrome.
- [ ] Track logical-qubit placement and workspace; use separate launch/arrival sites and record shortest-path fallbacks when protection is infeasible.
- [ ] Verify noiseless correctness across all methods, detection of single bit flips, and the limitations of the parity check.

## 3. Noisy comparison and research

- [ ] Complete the nine required benchmark cases: ideal baseline, noisy baseline, and noisy + protection for each of the five-node, contemporary IBM-style, and hyperbolic-inspired processor models, using the common processor definitions, fixed output ports, and noise assumptions.
- [ ] Run all four methods on all three models with matched ports, placement constraints, noise assumptions, and attempted-shot budgets; retain a separate ideal reference.
- [x] Compare noiseless and noisy shortest-path Bell baselines on all three provisional graphs with matched shots and backend-derived gate/readout errors.
- [x] Translate SWAPs and measurement rotations to backend-native gates, apply backend-derived noise, and report executed gate costs and unprotected yield.
- [x] Add a shared offline FakeSherbrooke test bed with calibration-derived gate/readout noise, directed gate error/duration data, and identical native circuits for clean/noisy comparisons.
- [x] Add seeded GenericBackendV2 test beds for the custom graph inputs and derive processor connectivity from the selected backends.
- [ ] Extend backend-derived native gate/readout noise to encoding and decoding; study depolarizing noise and relaxation across all routing methods.
- [ ] Report fidelity, depth, native two-qubit gates, SWAPs, physical qubits, runtime, accepted/discarded shots, and protection coverage.
- [ ] Sweep noise and port distance to find where QMRP helps or hurts; compare with all baselines and encoded execution without postselection.
- [ ] Save configurations, seeds, versions, counts, and traces. Include a separate feasible protection experiment if QMRP cannot protect a required topology.
- [x] Export baseline JSON reports with seeds, counts, intervals, executed QASM, and fake-backend snapshot hash/version/settings; full routing traces remain pending.

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
