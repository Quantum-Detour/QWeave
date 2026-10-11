# QMRP: Project Overview

**Quantum Multipath Routing with Parity Postselection**  
**Status:** Agreed project direction and implementation specification; no completed platform or experimental advantage is claimed.  
**Companion file:** `qmrp-todo.md`

## 1. The complete idea

Build a research platform that studies whether encoding a traveling logical qubit across two physical qubits, routing them through separate hardware paths, and rejecting detected errors can improve the quality of a quantum result enough to justify its overhead.

The platform combines four routing algorithms, three processor topology families, a reproducible Qiskit experiment pipeline, and an interactive **Quantum Packet Tracer**. It supports a Bell-pair research benchmark first, then reuses the same controls, routing traces, and analytics for other supported circuits.

The central question is:

> When do connectivity, route length, and noise make multipath protection worthwhile compared with standard and noise-aware single-path routing?

This is a quantum routing and error-detection project. Classical Raft consensus, AI features, and game mechanics are outside the scope.

## 2. Research contribution and break-even hypothesis

The proposed contribution is an experimental characterization of the trade-off between physical connectivity, redundant transport, and output quality. Novelty relative to prior literature must be investigated; combining these components does not automatically establish a new quantum code or routing algorithm.

### Hypothesis

Under some error models and endpoint arrangements, two sufficiently reliable routes permit parity postselection to improve conditional output fidelity. Beyond a certain detour, gate count, or error level, encoding and routing overhead can eliminate that benefit.

The result should be a **break-even map with uncertainty**, not a promised exact universal threshold. Multiple transitions or no beneficial region are valid findings.

Study three related questions:

1. **Topology:** Which graphs and endpoint regions admit feasible, low-cost route pairs?
2. **Protection:** Which errors are detected, which remain undetected, and how much additional noise does protection introduce?
3. **Resources:** How much fidelity improvement survives after accounting for attempted shots, acceptance, gates, qubits, and runtime?

Compare fidelity gains against both SABRE and the noise-aware method. Report separate fidelity and resource trade-offs rather than reducing everything to an unexplained score. If a deployment-style break-even criterion is needed, predefine a target fidelity and minimum acceptable yield before evaluating results.

## 3. Connection to the USask challenge

The primary specification is the supplied **Qiskit Fall Fest Challenge Hyperbolic Futures - quanTA USask.pdf**.

| Challenge requirement | Project implementation |
| --- | --- |
| Three processor models | Five-node reference, contemporary IBM-style model, finite hyperbolic-inspired model |
| Bell pair at designated ports | Prepare and verify the target Bell state at the prescribed physical output sites |
| Ideal and noisy baselines | Logical ideal reference, noiseless mapped-circuit checks, and noisy routing experiments |
| Protection strategy | Two-qubit repetition encoding with a parity syndrome and postselection |
| Geometry-aware encoding | Choose encoding sites, transport paths, and decoding sites using the coupling graph |
| Circuit cost and yield | Depth, native two-qubit gates, SWAPs, physical qubits, acceptance, and discarded shots |
| Reproducibility | Notebook, configurations, seeds, versions, circuits, and recorded results |
| Future-system recommendation | One concrete connectivity or routing recommendation supported by measurements |

The slides require common processor definitions, fixed ports, and noise assumptions. Obtain the full organizer specification if available. Until then, label chosen graphs and parameters as provisional. Complete all three models; do not quietly remove a model because disjoint routing is unavailable.

The McGill game proposal and spin-chain notebook are alternative directions or supporting material. Gamification is not part of this platform.

## 4. Four algorithms plus an ideal reference

The ideal reference is separate from the four routing algorithms. All four algorithms run under the same specified hardware and noise conditions.

| ID | Name | Routing behavior | Protection |
| --- | --- | --- | --- |
| A | Original | Deterministic shortest-hop routing with explicit SWAPs and a documented tie-break rule | None |
| B | Original + Qiskit built-in | Explicitly selected SABRE routing, with fixed seed and trial settings | None |
| C | Noise-aware | Explicit edge-error-weighted routing, optionally incorporating duration and idle cost | None in the primary comparison |
| D | QMRP: ours | Capacity-constrained routing of an encoded pair, followed by decoding and syndrome extraction | Parity postselection |
| Reference | Ideal logical circuit | No hardware routing noise | Known reference answer where tractable |

SABRE receiving a hardware `Target` is not, by itself, a guarantee of error-weighted route selection. Method C must implement an explicit cost rule and demonstrate that it responds to edge-quality changes.

Use a declared cost model, such as a sum of negative-log estimated gate-survival terms, with separately documented duration penalties. Treat this as a routing proxy, not an exact fidelity predictor. Use integer-scaled weights for minimum-cost flow.

For a clean comparison, QMRP should share the noise-aware cost assumptions with C, so D versus C isolates the added encoding and route redundancy as far as possible. Add a hop-only QMRP ablation if time permits.

Dynamical decoupling, twirling, and other mitigation or suppression options are secondary experiments. Apply them consistently across eligible methods rather than giving one method an unexplained advantage. Dynamical decoupling needs scheduled idle periods and an appropriate noise model to support meaningful claims.

## 5. Topology and graph model

### Required families

| Model | Purpose | Interpretation constraint |
| --- | --- | --- |
| 2016-inspired five-node reference | Small, constrained reference model | Follow the supplied definition; the slide illustration is a branching tree, not a five-node cross |
| Contemporary IBM-style | Study sparse connectivity with a documented heavy-hex construction or backend snapshot | Distinguish topology-only experiments from experiments using native gates and backend calibration data |
| Hyperbolic-inspired | Study a finite lattice-derived alternative | Record tiling parameters, boundary construction, vertex/face convention, and graph size |

Represent physical connectivity in NetworkX and operation directionality explicitly. Do not interpret drawing distances as physical gate durations. Do not invent reverse-direction native gates; if synthesizing them, count their cost.

A tree has a unique path between any two distinct vertices. That does not prove that every arrangement of two separate launch sites and two separate arrival sites is infeasible. Report route-pair feasibility for the actual endpoint regions.

Hyperbolic geometry does not imply dense connectivity, guaranteed short alternative routes, or universal superiority. Finite boundaries and port selection matter. In optional topology-isolation studies, control graph size, degree or edge budget, native gates, and noise where practical, and disclose unmatched factors.

### Capacity constraints

Split each eligible physical site into an in-node and out-node with capacity one. Use a two-unit flow between endpoint regions, with one unit per launch and arrival site. Remove occupied or reserved sites when required.

This constrains simultaneous route sharing for that transport operation. It does not replace logical-placement tracking, workspace allocation, or circuit scheduling. A flow solution can swap endpoint assignments; track which route contains the data qubit and ensure the final decoding and logical output placement are correct.

## 6. Quantum encoding and what it protects

An unknown qubit is encoded jointly, not copied:

\[
(\alpha|0\rangle+\beta|1\rangle)|0\rangle
\xrightarrow{\mathrm{CNOT}}
\alpha|00\rangle+\beta|11\rangle.
\]

Neither physical route contains an independently recoverable copy. Losing a route is not equivalent to losing one duplicate classical packet.

For the Bell benchmark, reference qubit `r` remains at output port A. Its partner is encoded into traveling qubits `a` and `b`:

\[
|\Phi^+\rangle_{ra}|0\rangle_b
\longrightarrow
\frac{|000\rangle_{rab}+|111\rangle_{rab}}{\sqrt 2}.
\]

Prepare the encoding using physically valid interactions; preparation and any necessary routing count toward overhead. Transport `a` and `b` to distinct sites. The main data qubit must ultimately occupy output port B.

At the destination, apply `CNOT(a, b)` and measure only `b` in Z. Accept syndrome zero. This combines decoding with extraction of the pre-decoding `Z_a Z_b` parity. A separate check ancilla is optional and must be counted if used.

| Error before an ideal decoder | Syndrome | Effect on the accepted Bell pair |
| --- | --- | --- |
| No error | Pass | Correct |
| X on either one traveling qubit | Fail | Shot rejected |
| Z on either one traveling qubit | Pass | Bell phase corrupted |
| X on both traveling qubits | Pass | Logical error remains |
| Z on both traveling qubits | Pass | No logical error in this idealized case |

This is selective error detection, not complete quantum error correction. Reference-qubit noise, encoding/decoding faults, and readout errors also matter. Disjoint paths do not guarantee statistically independent noise.

### Analytical sanity check

For independent net X-error probabilities `p1` and `p2`, perfect encoding/decoding and syndrome measurement, and a noiseless reference:

\[
P_{\mathrm{accept}}=(1-p_1)(1-p_2)+p_1p_2,
\]

\[
F_{\mathrm{accepted}}=
\frac{(1-p_1)(1-p_2)}{(1-p_1)(1-p_2)+p_1p_2}.
\]

Use these equations to validate the implementation, not to predict realistic hardware without further simulation.

## 7. Generalized routing engine

The architecture is reusable across circuit types, with explicit capability limits.

1. Accept a supported QASM version or a Qiskit `QuantumCircuit` through the Python API.
2. Validate qubit count, bound parameters, operations, measurements, and resource limits.
3. Normalize supported instructions into a declared gate set while preserving semantics.
4. Allocate physical qubits and record logical-to-physical placement.
5. Route each interaction using A, B, C, or D.
6. For D, insert an encode-transport-decode block only where idle workspace and valid routes exist.
7. Record syndrome bits separately from user output bits; define whole-shot acceptance as passing all inserted checks.
8. Track final placement and enforce required physical output ports, counting any restoration cost.
9. Translate into native operations, preserving intended routes and checking directionality.
10. Execute and export results plus a routing trace.

Encoding can preserve a qubit entangled with the rest of a circuit, but arbitrary gates must not be applied to one encoding component as if it were the unencoded logical qubit. The initial design decodes before subsequent logical operations.

**Initial supported scope:** bound gate-based circuits decomposable into the supported basis, with terminal measurements. Internal syndrome measurements and workspace reset are engine-controlled. Uploaded dynamic control flow, nonterminal user measurements, custom channels, pulses, and unresolved parameters require explicit support or a clear rejection.

No-free-ancilla and no-feasible-route cases trigger the declared standard shortest-path fallback. Label these as hybrid/fallback execution, not fully protected QMRP. Retain the reason and report protected-transport coverage. A simulator limit is a separate status, not a routing failure.

## 8. Experiment design and metrics

### Core experiments

Run all four noisy methods on all three topologies: twelve algorithm/topology combinations, with shared ideal references and noiseless correctness checks. D may be hybrid on some cases; report that plainly.

For the required protected case on a topology where D inserts no checks, add a separately labeled feasible protection control, such as an ancilla-based Bell stabilizer check with routed interactions. An unprotected fallback does not satisfy the protected-case requirement by itself.

Use identical attempted-shot budgets, physical output requirements, initial mapping, gate/noise assumptions, and evaluation procedures within each comparison. Repeat stochastic compilation and sampling across recorded seeds. Keep optimizer settings comparable and document unavoidable differences.

### Bell metric

\[
F_{\Phi^+}=\frac{1+\langle XX\rangle-\langle YY\rangle+\langle ZZ\rangle}{4}.
\]

Use separate basis circuits with the same syndrome acceptance rule. Include measurement-basis rotation noise. Report accepted counts and acceptance per basis. Estimate uncertainty using a documented method, such as bootstrapping measurement counts. Zero accepted shots means fidelity is undefined, not zero. Do not silently clip estimates to hide finite-shot fluctuations.

### Generic-circuit evaluation

| Circuit type | Suitable evaluation |
| --- | --- |
| Bell preparation | Bell fidelity |
| Small pure-state preparation | State fidelity against a tractable ideal reference |
| Sampling circuit | Output-distribution distance with finite-shot uncertainty |
| Observable experiment | Observable error against a known or tractable reference |
| Circuit beyond exact-reference limits | Routing/resource metrics and explicitly limited validation |

Distribution agreement is not a substitute for full quantum-state fidelity. Label simulator-internal exact-state diagnostics separately from measurement-estimated quantities.

### Required resource reporting

- Circuit depth and native two-qubit gate count.
- SWAP count before decomposition and native cost after decomposition.
- Used physical qubits, including workspace/check qubits, separately from total graph size.
- Attempted, accepted, and discarded shots; acceptance by basis or experiment.
- Compile time, simulator runtime, and modeled circuit duration as distinct quantities.
- Number of protected transport blocks, fallback count/reasons, and protection coverage.
- Both conditional output quality and its yield cost.

### Research sweeps and controls

Begin with independent X noise; then add depolarizing noise, thermal relaxation, readout error, and a correlated-error stress test. Schedule explicit idle intervals if making relaxation or waiting-time claims. Sweep noise and graph distance separately; graph hops are not physical meters.

Use held-out or prespecified port pairs for extensions. Include an unencoded baseline, the noise-aware baseline, and encoded execution without postselection to expose the effects of added circuitry and rejection. For a claimed break-even region, compare differences with uncertainty and account for searching across many sweep points.

## 9. Interactive dashboard and Quantum Packet Tracer

**Proposed stack:** Python, Qiskit/Aer, NetworkX, Streamlit, and Plotly. A separate frontend can be considered only if actual interaction requirements exceed the chosen stack.

### A. Experiment Controls

- Upload supported QASM or choose Bell, GHZ, and other validated presets.
- Choose topology, algorithm, mapping/output ports, noise profile, shots, and seeds.
- Display capability/resource checks before execution.
- Run all four methods or replay an already recorded experiment.
- Export configuration and result files.

### B. Quantum Packet Tracer — a core feature

- Interactive graph with physical nodes, permitted edges, and logical-qubit locations.
- Play, pause, next/previous step, timeline scrubbing, and playback-speed controls.
- Operation-level animation of gates and SWAP-induced state movement.
- Blue and orange routes for the two jointly encoded components.
- Visible preparation, encoding, transport, decoding, and syndrome events.
- Clickable nodes/edges showing occupancy, gate activity, assumed errors, and costs.
- Four-method replay on the same experiment; align by logical operation rather than pretending different compiled steps correspond one-to-one.
- Selected-shot syndrome display: green for pass, red for reject, with text labels.
- Highlighted fallback locations and explanations.
- Synchronized overhead and experiment statistics.

The tracer animates recorded operations and sampled measurement outcomes. It does not display directly observed amplitudes, exact physical error locations, or independently readable packets. A passed syndrome is not proof of an error-free quantum state. Any injected fault location is labeled as simulator ground truth.

### C. Four-Way Analytics

Quality comparison with uncertainty and ideal reference; cost comparison; acceptance/discarded-shot breakdown; protection coverage; and downloadable tables. Chart labels adapt to the metric rather than calling every measure fidelity. Historical results retain their original configuration when controls change.

### D. Break-Even Research View

Noise-versus-distance heatmaps, topology facets, fidelity improvement relative to a selected baseline, yield/overhead trade-offs, and click-through to an underlying run and its trace. Display only computed points; distinguish interpolation from simulation results.

There are no scores, levels, player challenges, or other gamification mechanics.

## 10. Architecture and reproducibility

Separate topology definitions, circuit validation, placement/routing, protection transforms, native compilation, simulation, metrics, trace generation, and frontend rendering. The notebook and dashboard should call the same backend functions.

Each result record should contain a schema version; run ID; input circuit/hash; topology definition/hash; ports and mappings; algorithm parameters; native gate/noise configuration; seeds and package versions; compiled circuit reference; metrics and uncertainties; raw counts; syndrome acceptance rule; fallback/protection records; and execution trace.

Trace events should identify the logical operation, physical operation, involved sites, placement before/after, route/protection block, and any available syndrome result. Keep deterministic routing events separate from shot-dependent measurement events.

Large graphs do not imply affordable full-state simulation. Select a compatible simulation method, cap resources, and label approximation or reduced-model assumptions. Never imply successful scientific validation when only a route was compiled.

## 11. Final deliverables

1. Reproducible research notebook with all required topology cases.
2. Four routing implementations and explicit ideal references.
3. Tested protection transform and documented fallback behavior.
4. Interactive dashboard with the complete Quantum Packet Tracer.
5. Graph/circuit visualizations, quantitative comparisons, and sweep results.
6. Machine-readable configurations, metrics, counts, and traces.
7. Research interpretation, limitations, and one evidence-backed future-system recommendation.
8. Demonstration using the Bell benchmark and at least one supported uploaded circuit.

## 12. Sources and supporting material

Primary supplied source: **Qiskit Fall Fest Challenge Hyperbolic Futures - quanTA USask.pdf**, especially pages 5–10 (task, rules, metrics), 12 (interpretation), and 13–14 (submission and rubric).

Supporting supplied notebooks: **transpile-with-pass-managers.ipynb**, **error-mitigation-and-suppression-techniques.ipynb**, and **combine-error-mitigation-techniques.ipynb**. The spin-chain and McGill resources are optional background, not extra mandatory project branches.

Previously consulted technical references:

- [Qiskit SABRE routing](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.transpiler.passes.SabreSwap)
- [NetworkX minimum-cost flow](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.flow.min_cost_flow.html)
- [NetworkX node-disjoint paths](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.connectivity.disjoint_paths.node_disjoint_paths.html)
- [Qiskit Aer noise models](https://qiskit.github.io/qiskit-aer/tutorials/3_building_noise_models.html)
- [IBM repetition-code tutorial](https://quantum.cloud.ibm.com/docs/en/tutorials/repetition-codes)
- [HYPERTILING research paper](https://arxiv.org/abs/2309.10844)

Check API compatibility when choosing implementation versions. These planning documents do not claim that any experiments, software, or architectural advantage have already been completed.
