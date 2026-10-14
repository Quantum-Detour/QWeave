# QWeave: Build Checklist

Compare four quantum routing methods across three processor models, then explore their results through a Quantum Packet Tracer and research dashboard. Detailed explanations are in [qmrp-project-overview.md](qmrp-project-overview.md).

**Current progress:** A/B/C, experimental simulation-assisted C, and the Bell-specific QMRP transform share backend properties, native compilation settings, simulation, measurement analysis, and reporting. The new `five_node_multipath` uses the custom five-edge cycle with fixed ports (0,4); the original `five_node` tree remains unchanged. IBM uses FakeSherbrooke and the custom/lattice graphs use seeded GenericBackendV2 properties. The audited all-zero Bell builder eliminates zero-state prepositioning fairly across methods. QMRP charges local encoding, one-way ancilla movement, disjoint transport, and decoding, and reports accepted-only plus unpostselected fidelity from the same samples. Infeasible cases use a labeled unprotected fallback without an additional experiment. The original tree is excluded from the default three-processor comparison. Maximum optimization preserves protection phase boundaries. Organizer confirmation, arbitrary-circuit protection, systematic noise/distance sweeps, and dashboard replay remain pending.

## 1. Topologies and Bell baseline

- [ ] Confirm the five-node, IBM heavy-hex, and hyperbolic graph definitions, fixed output ports, and allowed gate directions.
- [x] Add `five_node_multipath` with the user-specified cycle and ports (0,4), explicitly custom and not organizer-confirmed; preserve `five_node`.
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
- [x] C — Noise-aware: weighted Dijkstra using cached native CX/SWAP error costs from the same backend, using a local CX plus one-way outward SWAP costs for all-zero Bell preparation.
- [x] D — QMRP (Bell benchmark with zero workspace): encode across two qubits, find capacity-constrained disjoint routes, decode, and postselect using the parity syndrome.
- [x] Track Bell logical roles and workspace permutations; use separate launch/arrival sites and record shortest-path fallbacks when protection is infeasible.
- [x] Verify noiseless correctness across all methods, single-X detection, undetected Z/double-X errors, and independent-X analytical acceptance/fidelity.

- [x] Audit all-zero Bell movement across A/B/C/D; remove initial zero-state permutations and score one-way transport while preserving fixed output ports.
- [x] Add simulation-assisted C to the main Bell CLI as a separate C-MC row alongside original C; use bounded routes, equal noisy training budgets, and the shared final measurement/report pipeline.
- [x] Compare the old and current hyperbolic C/QMRP routes after the same movement simplification; record estimated costs, compiled native costs, gate counts, depths, and encoding/decoding cost components.

## 3. Noisy comparison and research

- [ ] Complete the nine required benchmark cases: ideal baseline, noisy baseline, and noisy + protection for each of the five-node, contemporary IBM-style, and hyperbolic-inspired processor models, using the common processor definitions, fixed output ports, and noise assumptions.
- [x] Run all four methods on the custom five-node, IBM and hyperbolic models with fixed ports, shared backend noise and attempted-shot budgets; retain ideal references and archive the original tree outside the default suite. Document D's zero-workspace assumption and phase boundaries.
- [x] Compare noiseless and noisy shortest-path Bell baselines on all three provisional graphs with matched shots and backend-derived gate/readout errors.
- [x] Translate SWAPs and measurement rotations to backend-native gates, apply backend-derived noise, and report executed gate costs and unprotected yield.
- [x] Add a shared offline FakeSherbrooke test bed with calibration-derived gate/readout noise, directed gate error/duration data, and identical native circuits for clean/noisy comparisons.
- [x] Add seeded GenericBackendV2 test beds for the custom graph inputs and derive processor connectivity from the selected backends.
- [x] Apply shared backend native gate/readout/thermal noise to encoding, transport, decoding, and syndrome readout.
- [ ] Systematically sweep depolarizing noise and relaxation across all routing methods.
- [x] Report fidelity and uncertainty, depth, native two-qubit gates, SWAPs, active physical qubits, routing runtime, accepted/discarded shots and multipath coverage for Bell experiments.
- [ ] Sample the old and current simplified hyperbolic routes with fixed backend noise and independent seeds; report fidelity differences, 95% intervals, QMRP acceptance, and unfiltered fidelity. The compilation audit alone cannot establish which route performs better.
- [x] Run the hyperbolic simulation-assisted C study with six candidates, independent held-out shots, 95% difference intervals, and training shot/runtime cost. The observed gain over current C was inconclusive and it did not beat SABRE in the held-out point estimates; repeat on other processors and with larger budgets before claiming a general advantage.
- [ ] Complete the frozen multi-seed C versus QMRP comparison across all three processors and report 95% difference intervals; the earlier partial artifacts were removed at the user's request.
- [ ] Sweep noise and port distance to find where QMRP helps or hurts; compare with all baselines and encoded execution without postselection.
- [x] Export schema-4 configurations, seeds, versions, joint/accepted counts, paths and protection phase/placement records.
- [ ] Complete unified gate-by-gate replay traces across all methods.
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

**Validation:** See [qmrp-movement-audit.md](qmrp-movement-audit.md) and the current [out.log summary](qmrp-results.md). The separate multi-seed comparison is incomplete; its generated artifacts were removed at the user’s request.

**Reporting rule:** Show accepted fidelity alongside yield and uncertainty. A passed syndrome does not guarantee an error-free state; zero accepted shots means fidelity is undefined.
