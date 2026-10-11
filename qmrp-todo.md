# QMRP: Implementation TODO

**Purpose:** Actionable work plan for the project defined in `qmrp-project-overview.md`.  
**Status:** Planning checklist. Unchecked items are future work, not completed implementation.  
**Scope:** Four algorithms + ideal reference; three topology families; Bell research; reusable circuit support; Quantum Packet Tracer; analytics. No Raft, AI, or gamification.

## Priority and dependency order

- **P0:** Scientific correctness and required benchmark.
- **P1:** Complete platform, Packet Tracer, and reproducibility.
- **P2:** Extra research and optional hardware/suppression studies.

Work in order: freeze assumptions → topologies/contracts → baselines → protection → execution/metrics → research sweeps → integrated dashboard → submission. Frontend layout work can begin against a clearly labeled fixture schema, but final charts and animations must use actual run records.

## 0. Freeze the specification — P0

- [ ] Obtain organizer graph definitions, output ports, noise assumptions, and any reference code.
- [ ] Record provisional choices explicitly wherever official definitions are missing.
- [ ] Freeze the four method names: A Original; B Qiskit SABRE; C Noise-aware; D QMRP.
- [ ] Keep the noiseless logical reference outside the four-method comparison.
- [ ] Define primary Bell ports and the initial logical-to-physical mapping for each model.
- [ ] Define a final-port restoration policy and include its cost in every affected method.
- [ ] Select the native gate basis and directional-gate conventions for each experiment suite.
- [ ] Define common-shot-budget, optimizer-setting, seed, and uncertainty policies.
- [ ] Choose the baseline and resource constraints used to declare a break-even region.
- [ ] Define supported QASM versions, circuit operations, measurement patterns, and size limits.
- [ ] Distinguish the required common benchmark from optional controlled-topology and backend-calibration studies.
- [ ] Review prior work before claiming algorithmic novelty.

**Done when:** One versioned configuration document specifies all comparison assumptions and open organizer dependencies.

## 1. Environment and data contracts — P0

- [ ] Choose and pin compatible Python, Qiskit, Aer, NetworkX, Streamlit, and Plotly versions.
- [ ] Verify import, compile, and simulator smoke runs in a reproducible environment.
- [ ] Define shared backend modules for topology, parsing, routing, protection, simulation, metrics, and traces.
- [ ] Define configuration/result/trace schemas with explicit versions.
- [ ] Define statuses: success, partial protection, fallback, unsupported circuit, infeasible mapping, simulator limit, and execution failure.
- [ ] Keep user measurement bits and injected syndrome bits distinguishable.
- [ ] Record circuit/topology hashes, seeds, versions, noise parameters, and mappings.
- [ ] Establish simulator resource caps and a compatible method-selection policy.

**Done when:** A notebook and a frontend can consume the same backend result contract without interpreting undocumented fields.

## 2. Generate and inspect topologies — P0

- [ ] Implement the prescribed five-node reference graph; do not replace it with a cross by assumption.
- [ ] Implement a documented heavy-hex construction or load a versioned backend snapshot.
- [ ] Implement a finite hyperbolic-lattice-derived graph and document tiling, truncation, and site convention.
- [ ] Validate node IDs, edges, connected components, operation directions, and selected ports.
- [ ] Store graph construction parameters and a deterministic hash.
- [ ] Plot all three graphs with ports, workspace candidates, and direction information where relevant.
- [ ] Compute graph size, degree distribution, port distance, and endpoint-region route feasibility.
- [ ] Separate hop distance from physical duration and drawing distance.
- [ ] If running a topology-only comparison, use a common synthetic basis/noise model and disclose graph-resource differences.

**Done when:** All three graphs are reproducible, their origins are documented, and their ports/resources can be inspected.

## 3. Circuit ingestion and placement — P0/P1

- [ ] Add Bell and small general-circuit presets, including at least one phase-sensitive or non-Clifford example.
- [ ] Accept Qiskit `QuantumCircuit` objects through the backend API.
- [ ] Add supported QASM upload parsing with clear validation errors.
- [ ] Reject or explicitly handle unbound parameters, dynamic control flow, nonterminal user measurements, and unsupported operations.
- [ ] Normalize gates without dropping semantics, classical outputs, or measurement ordering.
- [ ] Extract two-qubit interactions and maintain logical-to-physical placement after every SWAP.
- [ ] Track occupied sites, clean workspace, syndrome storage, and workspace reset/reuse.
- [ ] Enforce capacity and output-port requirements before simulation.
- [ ] Set and explain limits for exact reference calculations.

**Done when:** Supported inputs round-trip into an equivalent normalized circuit, and unsupported inputs fail clearly before execution.

## 4. Implement the three unprotected baselines — P0

### A. Original shortest-path routing

- [ ] Implement shortest-hop routing with a deterministic tie-break rule.
- [ ] Insert and trace SWAPs; update placement for every affected logical qubit.
- [ ] Preserve gate direction and final output placement.

### B. Qiskit built-in routing

- [ ] Select SABRE explicitly with reproducible seeds and trial settings.
- [ ] Use the same initial-mapping constraints as the other methods in the primary comparison.
- [ ] Extract the final layout and any restoration operations.
- [ ] Capture routing operations before SWAP decomposition and native costs afterward.

### C. Noise-aware routing

- [ ] Define an explicit error-weighted routing cost; document optional timing terms.
- [ ] Implement weighted path selection without assuming that supplying a Target changes SABRE into a noise-aware optimizer.
- [ ] Create a case where increasing one edge's error changes the selected route.
- [ ] Distinguish routing-cost estimates from measured output fidelity.

### Shared gate

- [ ] Verify noiseless logical equivalence on entangled and non-Clifford inputs for A, B, and C.
- [ ] Verify all native two-qubit operations obey connectivity/direction constraints.
- [ ] Count all final-port restoration operations.

**Done when:** All three methods implement the same logical task correctly and produce comparable circuit/resource records.

## 5. Implement QMRP route planning — P0

- [ ] Define separate launch and arrival sites for the data and redundancy qubits.
- [ ] Account for physical encoding/decoding connections and the reserved Bell reference site.
- [ ] Construct the split-node flow graph with unit vertex capacity.
- [ ] Add source/sink demands for two units and integer-scaled edge costs.
- [ ] Exclude unavailable workspace and conflicting occupied sites.
- [ ] Solve candidate endpoint-region configurations using minimum-cost flow.
- [ ] Extract routes and verify disjointness, endpoints, and native-edge validity.
- [ ] Handle swapped endpoint assignments without losing data-qubit identity.
- [ ] Include encoding, decoding, endpoint alignment, and any restoration costs when comparing candidates.
- [ ] Report whether endpoint search is exhaustive or heuristic; do not claim global optimality without justification.
- [ ] Add shortest-path fallback with explicit reason codes.
- [ ] Distinguish no route, no free workspace, directionality limits, and policy restrictions.

**Done when:** Selected route pairs are physically schedulable and fallback decisions are explainable. Feasibility is measured, not forced to fit a preferred architecture story.

## 6. Implement and validate protection — P0

- [ ] Encode with a valid CNOT into a clean redundancy qubit.
- [ ] Route both components while maintaining their joint state and avoiding unintended logical operations on the encoding.
- [ ] Decode with the correctly oriented CNOT and measure only the redundancy/syndrome qubit.
- [ ] Define shot acceptance as passing all inserted checks.
- [ ] Return accepted logical data to the required site before the next logical operation.
- [ ] Handle syndrome storage and reset/reuse without leaking results into user output registers.
- [ ] Verify that a Bell-entangled input remains correct in the noiseless accepted branch.
- [ ] Inject X on either rail and confirm rejection with ideal checking.
- [ ] Inject Z on one rail and confirm that it can pass while corrupting Bell phase.
- [ ] Inject X on both rails and confirm the undetected logical error.
- [ ] Match the independent-X analytical acceptance and conditional-fidelity formulas within sampling uncertainty.
- [ ] Include noisy encoding, decoding, syndrome measurement, and reference-qubit operations in realistic runs.
- [ ] Verify correctness across multiple protection blocks and fallback transitions.
- [ ] Add a separately labeled feasible protection control for any topology where QMRP performs no protection.

**Done when:** Protection is validated for entangled data, its blind spots are demonstrated, and every required topology has a real protected experiment.

## 7. Native compilation, noise, and execution — P0

- [ ] Preserve hand-selected physical routes through native-gate translation.
- [ ] Prevent optimization from silently removing the intended protection or changing benchmark semantics.
- [ ] Decompose SWAPs into native operations and ensure their noise is actually applied.
- [ ] Implement independent X-noise sanity runs first.
- [ ] Add depolarizing, thermal-relaxation, and readout-noise profiles with explicit parameter meanings.
- [ ] Include basis-rotation noise for measurement-based verification.
- [ ] If modeling idle relaxation, schedule and model waiting periods explicitly.
- [ ] Add a correlated-noise stress case and state its construction.
- [ ] Run ideal references, noiseless transformed checks, and all twelve noisy method/topology cases.
- [ ] Store raw counts, per-check outcomes where available, accepted counts, and runtime metadata.
- [ ] Use equal total attempted-shot budgets, including all Bell measurement bases.

**Done when:** A recorded result can be traced to the exact circuit, topology, noise model, seeds, and execution budget.

## 8. Metrics and break-even research — P0/P1

- [ ] Implement Bell XX, YY, and ZZ estimation with identical syndrome-selection rules.
- [ ] Compute Bell fidelity and documented uncertainty; retain basis-specific acceptance.
- [ ] Handle zero accepted shots as undefined quality.
- [ ] Add circuit-specific metrics without labeling distribution distance as state fidelity.
- [ ] Count depth, native two-qubit gates, SWAPs, used physical qubits, shots, and protection coverage.
- [ ] Separate compile time, simulator wall time, and modeled circuit duration.
- [ ] Report conditional fidelity beside yield and attempted-shot cost.
- [ ] Sweep noise at fixed ports for the main study.
- [ ] Sweep prespecified port pairs/distances in a separate extension.
- [ ] Repeat across sampling and compiler seeds; report uncertainty in method differences.
- [ ] Compare QMRP to A, B, and C, not only the weakest baseline.
- [ ] Include encoded execution without postselection as an ablation.
- [ ] Identify beneficial, harmful, inconclusive, infeasible, and fallback-only regions separately.
- [ ] Confirm apparent crossover regions with additional measurements rather than treating coarse-grid interpolation as an exact threshold.
- [ ] Record failure cases and negative findings alongside successful cases.

**Done when:** The study can explain where protection helps, what it costs, and what cannot be concluded.

## 9. Build the complete interactive dashboard — P1

### Experiment Controls

- [ ] Circuit presets and supported QASM upload.
- [ ] Topology, mapping/ports, method, noise profile, shot budget, and seed controls.
- [ ] Pre-run support/resource checks and clear error messages.
- [ ] Run-one/run-all actions, progress, and cancellation where supported.
- [ ] Saved-run selection, configuration export, and results download.
- [ ] Keep recorded results labeled with their original settings after controls change.

### Quantum Packet Tracer — required, not optional

- [ ] Render physical nodes/edges and logical-qubit occupancy.
- [ ] Implement play, pause, next/previous step, scrubber, and speed controls.
- [ ] Animate single/two-qubit gates and SWAP-induced state movement.
- [ ] Show QMRP routes in blue/orange with text/shape distinctions.
- [ ] Show encoding, decoding, and syndrome-measurement events explicitly.
- [ ] Support node/edge inspection for occupancy, operation, noise, and cost.
- [ ] Replay each of the four methods for the same input experiment.
- [ ] Align comparison playback by logical operations when compiled steps differ.
- [ ] Select a recorded shot for green pass/red reject syndrome display.
- [ ] Label pass as syndrome acceptance, not proof of correctness.
- [ ] Show fallback location, reason, and replacement route.
- [ ] Distinguish trace operations, sampled measurements, and any simulator-only fault ground truth.
- [ ] Synchronize trace selection with resource and run details.

### Four-Way Analytics

- [ ] Quality chart with uncertainty and a metric-appropriate ideal reference.
- [ ] Depth, two-qubit gates, SWAP, qubit-use, and runtime comparisons.
- [ ] Accepted/discarded shots and protection/fallback coverage.
- [ ] Per-topology comparison and downloadable tables.
- [ ] Prevent incompatible metrics from appearing on one misleading fidelity axis.

### Break-Even Research View

- [ ] Noise/distance heatmaps with baseline selector and topology facets.
- [ ] Yield-versus-quality and overhead trade-offs.
- [ ] Click-through from a research point to its configuration and Packet Tracer replay.
- [ ] Explicit labels for uncomputed, interpolated, infeasible, and inconclusive regions.

**Done when:** Users can upload a supported circuit, run all four methods, inspect actual routing, and interpret quality and cost from the same experiment.

## 10. Integration and scientific acceptance gates — P0/P1

- [ ] Bell benchmark runs across all three models with correct output ports.
- [ ] A supported uploaded circuit uses the complete dashboard and all four method paths, including honest fallback.
- [ ] A phase-sensitive/non-Clifford input verifies that the system preserves quantum coherence beyond bit correlations.
- [ ] Noiseless transformations preserve logical behavior and intended acceptance.
- [ ] Tight workspace, no-route, disconnected graph, unsupported input, and zero-acceptance cases are handled correctly.
- [ ] A replayed trace matches the corresponding compiled circuit and recorded syndrome bits.
- [ ] Repeated runs with the same documented settings reproduce results within the declared determinism/sampling model.
- [ ] A frontend change cannot alter backend experimental meaning or silently relabel results.
- [ ] Resource caps prevent unexpectedly expensive simulations and explain limitations.

**Done when:** Correctness, honest metrics, replay consistency, and a supported generic upload are demonstrated end to end.

## 11. Submission and demonstration — P1

- [ ] Produce a reproducible notebook calling the shared backend.
- [ ] Include all three graphs with ports and representative compiled circuits.
- [ ] Include the twelve-method/topology results, ideal references, and any separate protection controls.
- [ ] Export configurations, raw counts, metrics, uncertainties, and traces.
- [ ] Explain the encoding, undetected errors, and acceptance trade-off.
- [ ] Document topology/noise controls and unresolved comparability limits.
- [ ] State whether evidence supports a useful break-even region or a negative finding.
- [ ] Make one specific future-system recommendation supported by results.
- [ ] Record a demo of Bell routing, four-method comparison, dual-route syndrome behavior, fallback, and a supported circuit upload.
- [ ] Include setup instructions, pinned dependencies, seeds, source attribution, and simulator limitations.
- [ ] Remove claims of universal hyperbolic superiority, full error correction, or unrestricted circuit support.

**Done when:** Another person can reproduce the main comparison and understand the limits without relying on the live demo.

## 12. Optional extensions — P2

- [ ] Matched-size/degree topology studies beyond the official benchmark.
- [ ] Additional hyperbolic constructions and finite-boundary sensitivity.
- [ ] Hop-only versus error-weighted QMRP ablation.
- [ ] Dynamical decoupling with explicit scheduling and idle-noise controls.
- [ ] Additional error mitigation applied consistently across eligible methods.
- [ ] Real-backend execution, kept separate from the common simulator benchmark.
- [ ] Broader circuit/control-flow support with dedicated correctness validation.
- [ ] Higher-distance codes or richer checks if the initial protection scope is complete.

## Suggested four-stage sprint

| Stage | Focus | Exit gate |
| --- | --- | --- |
| 1 | Freeze benchmark; topologies; contracts; A/B/C | Baselines are noiselessly correct |
| 2 | QMRP; fallback; noise; metrics | Protection behavior and common comparisons are validated |
| 3 | Dashboard; full Quantum Packet Tracer; sweeps | Real result records drive interactions and analytics |
| 4 | Research interpretation; reproducibility; demo | Required deliverables and acceptance gates pass |

This is an execution order, not a promise that all research and engineering fit into four calendar days. Preserve scientific correctness and the agreed core features; defer P2 extensions first if time is constrained.
