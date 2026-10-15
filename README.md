# QWeave: Geometry-Aware Quantum Routing & Parity Postselection

**Qiskit Fall Fest 2026 Challenge: Hyperbolic Futures**  
*Host: quanTA, University of Saskatchewan (Prof. Steven Rayan)*  
*Team Members:*
- **Aaron Huang**
- **Calvin Cheng**
- **Bhaskar Mahajan**

---

## Table of Contents
- [1. Challenge Deliverables & Executive Summary](#1-challenge-deliverables--executive-summary)
- [2. Experimental Setup, Qiskit APIs & Lattice Generation](#2-experimental-setup-qiskit-apis--lattice-generation)
  - [A. Processor Lattices & Generation Methodology](#a-processor-lattices--generation-methodology)
  - [B. Simulation Engine & Exact State Verification](#b-simulation-engine--exact-state-verification)
  - [C. Circuit Construction Qiskit APIs](#c-circuit-construction-qiskit-apis)
  - [D. Adding Hardware Noise (Qiskit APIs)](#d-adding-hardware-noise-qiskit-apis)
- [3. Deliverable 02: Graphs and Circuits](#3-deliverable-02-graphs-and-circuits)
  - [A. The Three Coupling Graphs with Marked Ports](#a-the-three-coupling-graphs-with-marked-ports)
  - [B. Transpiled Native Circuits & Execution Structure](#b-transpiled-native-circuits--execution-structure)
- [4. Deliverable 03: Quantitative Comparison](#4-deliverable-03-quantitative-comparison)
  - [Physical Qubit Accounting](#physical-qubit-accounting)
- [5. Deliverable 04: Scientific Interpretation](#5-deliverable-04-scientific-interpretation)
  - [A. Why We Evaluated Three Baseline Algorithms (A, B, C)](#a-why-we-evaluated-three-baseline-algorithms-a-b-c)
  - [B. What QMRP Detects vs. What It Misses](#b-what-qmrp-detects-vs-what-it-misses)
  - [C. Limitations & Trade-Off Analysis](#c-limitations--trade-off-analysis)
- [6. Deliverable 05: Hardware or Software Recommendation](#6-deliverable-05-hardware-or-software-recommendation)
- [7. Inspirations & References](#7-inspirations--references)
  - [Noise-Aware Routing](#noise-aware-routing)
  - [QMRP & Hyperbolic Protection](#qmrp--hyperbolic-protection)
- [8. AI Usage Statement](#8-ai-usage-statement)
- [9. Reproducibility & Viewing Results](#9-reproducibility--viewing-results)
  - [A. Setup & Locked Dependencies](#a-setup--locked-dependencies)
  - [B. Execution & Results](#b-execution--results)

---

## 1. Challenge Deliverables & Executive Summary

This repository delivers the complete submission for the **Qiskit Fall Fest 2026 Challenge ("Hyperbolic Futures", quanTA USask)**. The challenge investigates whether encoding a traveling logical qubit across two physical rails, routing them along disjoint hardware paths, and rejecting detected errors via parity postselection (**QMRP: Quantum Multipath Routing Protection**) can improve Bell state fidelity enough to justify its operational and shot-yield overhead.

The five submission deliverables specified in the challenge rubric (pages 9–13 of the challenge specification) are mapped to repository artifacts as follows:

| Deliverable | Requirement | Location in Repository |
|---|---|---|
| **01 Reproducible Execution** | Runnable Qiskit code, locked dependencies, noise assumptions, seeds, and recorded results. | [`src/qweave/`](src/qweave/), [`pyproject.toml`](pyproject.toml), [`uv.lock`](uv.lock), [`out.log`](out.log) |
| **02 Graphs and Circuits** | The three coupling graphs with designated ports marked, and transpiled native circuits. | Section 3 below, [`results/visual_summary.html`](results/visual_summary.html), and CLI `--show-circuit` |
| **03 Quantitative Comparison** | Fidelity (with uncertainty), circuit cost, SWAP overhead, physical qubit usage, and yield across core cases. | Section 4 below, [`results/visual_summary.html`](results/visual_summary.html), and [`out.log`](out.log) |
| **04 Scientific Interpretation** | Explanation of results, why multiple baselines were tested, and limitations of parity postselection. | Section 5 below |
| **05 Hardware or Software Recommendation** | One specific design choice for future cloud systems, supported by our results. | Section 6 below |

---

## 2. Experimental Setup, Qiskit APIs & Lattice Generation

### A. Processor Lattices & Generation Methodology

The challenge benchmarks quantum routing across three distinct processor architectures:

1. **2016 Five-Node Reference**:
   - **Generation**: Generated programmatically using NetworkX in [`src/qweave/processors.py`](src/qweave/processors.py).
   - **Topology Details**: Two variants are maintained:
     - `five_node`: The original 2016 branching-tree layout `((0, 1), (1, 2), (1, 3), (3, 4))` with ports `(0, 4)`. Because a tree has only a single acyclic path between ports 0 and 4, multipath routing cannot form vertex-disjoint rails.
     - `five_node_multipath`: A 5-qubit cycle topology `((0, 1), (1, 2), (2, 3), (3, 4), (4, 1))` with ports `(0, 4)`. This preserves the 5-qubit scale while introducing an alternate path (0→1→2→3→4 vs 0→1→4) to enable vertex-disjoint multipath routing.
   - **Parameters**: 5 qubits, 5 edges, ports `(0, 4)`, graph diameter = 2 hops.

2. **IBM Heavy-Hex (Contemporary Architecture)**:
   - **Generation**: Generated directly using Qiskit's built-in `FakeSherbrooke` provider (`qiskit_ibm_runtime.fake_provider.FakeSherbrooke`).
   - **Topology Details**: Represents IBM's 127-qubit Eagle r3 processor. Qubits are arranged on a heavy-hexagonal lattice designed to minimize frequency collisions while supporting low-degree connectivity. Native 2-qubit basis is Echoed Cross-Resonance (`ecr`).
   - **Parameters**: 127 qubits, 144 edges, ports `(0, 15)` spanning 6 hops across the heavy-hex lattice.

3. **Hyperbolic Lattice {7,3} (Future Architecture)**:
   - **Generation**: Generated using the third-party open-source library **`HYPERTILING`** (version 1.5.1) via [`scripts/generate_hyperbolic.py`](scripts/generate_hyperbolic.py).
   - **Topology Details**: Constructs a regular heptagonal tiling of the hyperbolic Poincaré disk with Schläfli symbol `{p=7, q=3}` (heptagons meeting 3 at each vertex) up to generation level $n=4$ using the SRS kernel (`HyperbolicTiling(p=7, q=3, n=4, kernel="SRS", center="cell")`). Qubits are assigned to cell centers, and coupling edges connect adjacent cells sharing a polygon boundary (interior degree 7).
   - **Parameters**: 85 qubits, 189 edges. Designated output ports `(5, 31)` are deterministically selected as the lexicographically smallest pair achieving the maximum graph diameter (6 hops). Graph geometry and coordinates are frozen into [`src/qweave/data/hyperbolic_7_3_cells.json`](src/qweave/data/hyperbolic_7_3_cells.json).

### B. Simulation Engine & Exact State Verification
- **Measurement Sampling**: Simulated with `qiskit_aer.AerSimulator` using the `matrix_product_state` (MPS) simulation method without artificial bond-dimension truncation.
- **Exact State Verification**: Before noisy execution, all unmeasured circuit variants are verified using `qiskit.quantum_info.Statevector`. Non-output workspace qubits are traced out via `partial_trace`, and the reduced two-qubit density matrix is evaluated against the ideal Bell state $|\Phi^+\rangle = \frac{|00\rangle + |11\rangle}{\sqrt{2}}$ using `state_fidelity`. Every synthesized circuit is validated to achieve exact noiseless state fidelity $F = 1.000000000000$ (tolerance: $10^{-10}$) before measurement experiments proceed.

### C. Circuit Construction Qiskit APIs
All circuits are constructed using standard Qiskit primitives:
- `qiskit.circuit.QuantumCircuit`, `QuantumRegister`, and `ClassicalRegister`.
- Core gate primitives: `h`, `cx`, `swap`, `barrier`, and `measure`.
- **Measurement Basis Rotations**: To measure the Bell state fidelity $F(\Phi^+) = \frac{1 + \langle XX \rangle - \langle YY \rangle + \langle ZZ \rangle}{4}$, three separate circuit variants are created for each routing method:
  - **$XX$ Basis**: Applies an $H$ gate to both output ports immediately before measurement.
  - **$YY$ Basis**: Applies an $S^\dagger$ (`sdg`) phase gate followed by an $H$ gate to both output ports.
  - **$ZZ$ Basis**: Measures both output ports directly in the computational $Z$ basis.
- **Syndrome Extraction**: For protected QMRP circuits, the traveling rails' parity $Z_a Z_b$ is transferred to a syndrome ancilla via a terminal `cx` before being measured into a dedicated classical register `ClassicalRegister(1, "syndrome")`. Only measurement shots with syndrome bit $0$ are accepted.

### D. Adding Hardware Noise (Qiskit APIs)
- **IBM Heavy-Hex Noise Model**: Constructed via `qiskit_aer.noise.NoiseModel.from_backend(FakeSherbrooke())`, incorporating calibration-derived gate depolarization, thermal relaxation during gate execution ($T_1, T_2$), and qubit readout errors on all 127 physical qubits.
- **Five-Node & Hyperbolic Noise Models**: Built with `qiskit.providers.fake_provider.GenericBackendV2` seeded with the exact coupling map and native basis (`id, rz, sx, x, cx`). Setting `noise_info=True` with fixed `--backend-seed 1234` introduces realistic hardware-inspired gate errors ($10^{-3}$ to $10^{-2}$), thermal relaxation, and readout errors.
- **Transpilation Pass Manager**: Compilation uses `qiskit.transpiler.generate_preset_pass_manager` with optimization level 3 (`MAXIMUM`), `approximation_degree=1.0` (exact unitary synthesis), and `routing_method="none"` (preserving our explicit physical routes). Phase barriers preserve boundaries between state preparation, encoding, transport, decoding, and measurement.

---

## 3. Deliverable 02: Graphs and Circuits

### A. The Three Coupling Graphs with Marked Ports

```
Five-Node Multipath (5 Qubits)          IBM Heavy-Hex FakeSherbrooke (127 Qubits)
   [0]* ─── [1] ─── [2]                  [0]* ─── [1] ─── [2] ─── ... ─── [14] ─── [15]*
     │        │       │                  (Sparse heavy-hexagonal lattice, degree 2-3,
     └───────[4]*─── [3]                  diameter: 6 hops between ports 0 and 15)
(*Ports: 0 and 4; distance: 2 hops)

Hyperbolic {7,3} Lattice (85 Qubits, Poincaré Heptagonal Tiling)
   Regular heptagonal cell graph; interior coordination number = 7.
   Ports: 5 and 31 (Lexicographically smallest diameter pair; distance: 6 hops).
```

### B. Transpiled Native Circuits & Execution Structure

All circuits compile to backend-native gates (`rz`, `sx`, `cx`/`ecr`, `x`). 

#### 1. Baseline Circuits (Single-Path Routing: Methods A, B, C)
For single-path transport, a local Bell state is initialized at port $A$, and the second qubit is routed to port $B$ using a sequence of native SWAP operations (decomposed into 3 $CX$ gates).

```
         Preparation       Transport (SWAPs)               Basis Rotation & Measurement
q_0: ────┤ H ├──■──────────────────────────────────────────[Basis Rot]───┤M (bell[0])├──
                │
q_1: ────|0>────┼───────X─────────────── ... ─────────────
                │       │
q_k: ────|0>────X───────X───────X─────── ... ─────X───────
                                │                 │
q_dst: ──|0>────────────────────X─────── ... ─────X───────[Basis Rot]───┤M (bell[1])├──
```

#### 2. Protected Circuit (Multipath QMRP: Method D)
QMRP encodes the traveling qubit into two physical rails, routes them across vertex-disjoint paths, checks their joint parity via an ancilla, and postselects on zero syndrome:

```
         Preparation   Encoding         Disjoint Transport              Decoding & Parity Check   Measurement
q_src: ──┤ H ├──■─────────────────────────────────────────────────────────────────────────────────┤M (bell[0])├──
                │
rail_1: ─|0>────┼───────■───────────[SWAP Path 1]────────────────────────■────────────────────────
                │       │                                                │
rail_2: ─|0>────X───────X───────────[SWAP Path 2]────────────────────────┼───────■────────────────
                                                                         │       │
ancilla: |0>─────────────────────────────────────────────────────────────┼───────┼───────■────────┤M (syndrome)├──
                                                                         │       │       │
q_dst: ──|0>─────────────────────────────────────────────────────────────X───────X───────X────────┤M (bell[1])├──
```

#### 3. Native Transpiled Gate Decompositions (Five-Node ZZ Baseline Example)
The fully transpiled native circuit on `GenericBackendV2` utilizes native `rz, sx, cx` gates:
```
global phase: π/4
         ┌─────────┐┌────┐┌─────────┐
q_0 -> 0 ┤ Rz(π/2) ├┤ √X ├┤ Rz(π/2) ├──■───────────────────────────░────░───┌─┐
         └─────────┘└────┘└─────────┘┌─┴─┐     ┌───┐               ░    ░   └╥┘
q_1 -> 1 ────────────────────────────┤ X ├──■──┤ X ├──■────────────░────░────╫──
                                     └───┘┌─┴─┐└─┬─┘┌─┴─┐          ░    ░    ║
q_4 -> 4 ─────────────────────────────────┤ X ├──■──┤ X ├──────────░────░────╫─┤M├
                                          └───┘     └───┘          ░    ░    ║ └╥┘
 bell: 2/════════════════════════════════════════════════════════════════════╩══╩═
                                                                             0  1 
```

> [!TIP]
> **Interactive Visualization**: Complete interactive network topologies with highlighted ports, multi-phase circuit timelines, and interactive benchmark charts are viewable in [`results/visual_summary.html`](results/visual_summary.html).

---

## 4. Deliverable 03: Quantitative Comparison

The core 9 benchmark cases required by the challenge (Ideal Baseline, Noisy Baseline, Noisy + Protection across all three processors) were audited under identical experimental controls (total shot budget: 3,072 shots per algorithm per processor, split evenly into 1,024 shots each for $XX$, $YY$, and $ZZ$ bases; master seed: `42`; backend seed: `1234`):

```text
Final summary (backend noise; ZZ circuit metrics)
┌────────────┬───────────────────────────┬───────────┬────────┬─────────────────────────┬───────┬──────────────────────┬───────┬──────────┐
│ Processor  │ Algorithm                 │ Noiseless │  Noisy │ Physical Qubits / Total │ SWAPs │ Native 2-qubit gates │ Depth │ Accepted │
├────────────┼───────────────────────────┼───────────┼────────┼─────────────────────────┼───────┼──────────────────────┼───────┼──────────┤
│ Five-node  │ A: Shortest path          │    1.0000 │ 0.9751 │       3 / 5 (60.0%)     │     1 │                    4 │     8 │  100.00% │
│ (multipath)│ B: SABRE                  │    1.0000 │ 0.9751 │       3 / 5 (60.0%)     │     1 │                    4 │     8 │  100.00% │
│            │ C: Noise-aware            │    1.0000 │ 0.9751 │       3 / 5 (60.0%)     │     1 │                    4 │     8 │  100.00% │
│            │ C-MC: Simulation-assisted │    1.0000 │ 0.9751 │       3 / 5 (60.0%)     │     1 │                    4 │     8 │  100.00% │
│            │ D: QMRP (Parity Checked)  │    1.0000 │ 0.9711 │       5 / 5 (100.0%)    │     2 │                    9 │    11 │   98.05% │
├────────────┼───────────────────────────┼───────────┼────────┼─────────────────────────┼───────┼──────────────────────┼───────┼──────────┤
│ IBM        │ A: Shortest path          │    1.0000 │ 0.7842 │       6 / 127 (4.7%)    │     4 │                   13 │    56 │  100.00% │
│ Heavy-Hex  │ B: SABRE                  │    1.0000 │ 0.7710 │       6 / 127 (4.7%)    │     4 │                   13 │    30 │  100.00% │
│            │ C: Noise-aware            │    1.0000 │ 0.7842 │       6 / 127 (4.7%)    │     4 │                   13 │    56 │  100.00% │
│            │ C-MC: Simulation-assisted │    1.0000 │ 0.7842 │       6 / 127 (4.7%)    │     4 │                   13 │    56 │  100.00% │
│            │ D: QMRP (Parity Checked)  │    1.0000 │ 0.7709 │       8 / 127 (6.3%)    │     8 │                   27 │   113 │   87.43% │
├────────────┼───────────────────────────┼───────────┼────────┼─────────────────────────┼───────┼──────────────────────┼───────┼──────────┤
│ Hyperbolic │ A: Shortest path          │    1.0000 │ 0.9219 │       7 / 85  (8.2%)    │     5 │                   16 │    34 │  100.00% │
│ {7,3}      │ B: SABRE                  │    1.0000 │ 0.9258 │       7 / 85  (8.2%)    │     5 │                   16 │    22 │  100.00% │
│            │ C: Noise-aware            │    1.0000 │ 0.9028 │       8 / 85  (9.4%)    │     7 │                   22 │    58 │  100.00% │
│            │ C-MC: Simulation-assisted │    1.0000 │ 0.9185 │       7 / 85  (8.2%)    │     6 │                   19 │    54 │  100.00% │
│            │ D: QMRP (Parity Checked)  │    1.0000 │ 0.9208 │       9 / 85 (10.6%)    │    12 │                   39 │    93 │   90.69% │
└────────────┴───────────────────────────┴───────────┴────────┴─────────────────────────┴───────┴──────────────────────┴───────┴──────────┘
Fidelity uses accepted XX/YY/ZZ shots; each row uses its own attempted-shot budget.
```

### Physical Qubit Accounting
As explicitly required by the challenge rubric, physical qubits actively used during compilation (including transport wires and syndrome ancillas) are distinguished from the chip's total capacity:
- **Five-node Processor**: 3 physical qubits used for baselines, 5 physical qubits used for QMRP (100% of total 5-qubit chip capacity).
- **IBM Heavy-Hex (`FakeSherbrooke`)**: 6 physical qubits used for baselines, 8 physical qubits used for QMRP (only ~4.7% to 6.3% of the 127-qubit chip capacity).
- **Hyperbolic Lattice (`{7,3}`)**: 7–8 physical qubits used for baselines, 9 physical qubits used for QMRP (8.2% to 10.6% of the 85-qubit chip capacity).

---

## 5. Deliverable 04: Scientific Interpretation

### A. Why We Evaluated Three Baseline Algorithms (A, B, C)
Rather than comparing QMRP against a single arbitrary baseline, we benchmarked it against three distinct routing paradigms:
1. **Method A: Shortest Path**: Deterministic minimal-hop Dijkstra routing.
2. **Method B: SABRE**: Industry-standard Qiskit heuristic routing (`SabreSwap` with `decay` lookahead).
3. **Method C & C-MC: Noise-Aware & Simulation-Assisted**: Weighted routing minimizing cumulative calibration error logs ($-\sum \log(1 - \epsilon_{\text{gate}})$), alongside a Monte Carlo simulation-assisted variant (C-MC).

**Core Finding**: **No single baseline is universally superior across different hardware topologies:**
- On **IBM Heavy-Hex**, SABRE produced the lowest circuit depth (**30** vs. 56 for Shortest Path), but had slightly lower fidelity (0.7710 vs. 0.7842) due to allocating gates across noisier physical links.
- On the **Hyperbolic Lattice**, SABRE achieved the highest fidelity (**0.9258**) and lowest depth (**22**). Meanwhile, Noise-Aware took an overly conservative detour (SWAPs: 7, depth: 58) that actually degraded fidelity to 0.9028.
- Evaluating QMRP against multiple competitive baselines ensures a fair, unbiased benchmark, avoiding artificial claims of advantage over an unoptimized reference.

### B. What QMRP Detects vs. What It Misses
- **Detected Errors ($S=1$, shot discarded)**: Any single Pauli $X$ (bit-flip) error occurring on either traveling rail during transport.
- **Undetected Errors ($S=0$, logical fidelity degrades)**:
  - Pauli $Z$ (phase-flip) errors on either rail: $Z$ errors commute with the encoding $CX$ operations and are invisible to the repetition parity check.
  - Correlated or simultaneous double bit-flip errors ($X \otimes X$) on both rails.
  - Idle thermal relaxation ($T_1, T_2$) on the stationary reference qubit $R$ at port $A$ while waiting for the traveling rails to traverse multi-hop paths.
  - Gate errors occurring during the encoding, decoding, or syndrome extraction operations themselves.

### C. Limitations & Trade-Off Analysis
1. **Conditional Fidelity Improvement**: Within its own circuit execution, parity postselection is mathematically effective. On the Hyperbolic lattice, the unpostselected fidelity of QMRP is **0.8564**; filtering out the 9.31% failing shots lifts the conditional fidelity to **0.9208**.
2. **Overhead Penalty Cancels Net Benefit**: The extra operations required for multipath protection (encoding $CX$, decoding $CX$, syndrome measurement, and routing two separate physical rails along longer alternate paths) more than double the native 2-qubit gate count (39 vs 16) and nearly quadruple circuit depth (93 vs 22). Under realistic superconducting error rates ($10^{-3}$ to $10^{-2}$), the noise accumulated by these extra gates offsets the detected error filtering.
3. **Statistical Inconclusiveness**: On the Hyperbolic lattice, QMRP's accepted fidelity of $0.9208$ (95% CI: $[0.8447, 0.9786]$) overlaps with SABRE's fidelity of $0.9258$ (95% CI: $[0.8548, 0.9968]$). QMRP does not achieve a statistically significant improvement over optimized single-path baselines under realistic physical noise.

---

## 6. Deliverable 05: Hardware or Software Recommendation

> [!IMPORTANT]
> ### Recommendation: Geometry- and Distance-Aware Selective Routing Policy
> Quantum cloud compilers and schedulers should **not** enable multipath repetition encoding as a default transport mechanism. Instead, compilers should apply a selective routing policy based on hardware geometry and topological distance:
> 
> 1. **Short-to-Medium Distances ($d \le 4$)**: Enforce single-path noise-adaptive routing (such as SABRE or calibration-weighted shortest path). Over short distances, the gate and SWAP overhead of encoding, dual-rail transport, and syndrome extraction invariably exceeds the transport error rate.
> 2. **High-Degree Alternative Geometries (Hyperbolic Lattices, $d \ge 5$)**: Expose multipath parity postselection as an **opt-in compiler pass** *only* under two conditions:
>    - The user explicitly prioritizes output state fidelity over throughput and can tolerate a **5% to 15% shot discard penalty**.
>    - The hardware platform's local 2-qubit gate error rates ($\epsilon_{\text{gate}}$) are substantially lower than cumulative link errors along long routing paths, preventing encoding and decoding errors from dominating the noise budget.

---

## 7. Inspirations & References

### Noise-Aware Routing
- **Title**: *Noise-Adaptive Compiler Mappings for Noisy Intermediate-Scale Quantum Computers*
- **Authors**: Prakash Murali, Jonathan M. Baker, Ali Javadi Abhari, Frederic T. Chong, Margaret Martonosi
- **Conference / Comments**: To appear in ASPLOS '19
- **Subjects**: Quantum Physics (`quant-ph`); Programming Languages (`cs.PL`)
- **Submission Date**: 30 Jan 2019
- **arXiv Link**: [arXiv:1901.11054](https://arxiv.org/abs/1901.11054)
- **DOI**: [10.48550/arXiv.1901.11054](https://doi.org/10.48550/arXiv.1901.11054)

```bibtex
@misc{murali2019noiseadaptivecompilermappingsnoisy,
      title={Noise-Adaptive Compiler Mappings for Noisy Intermediate-Scale Quantum Computers}, 
      author={Prakash Murali and Jonathan M. Baker and Ali Javadi Abhari and Frederic T. Chong and Margaret Martonosi},
      year={2019},
      eprint={1901.11054},
      archivePrefix={arXiv},
      primaryClass={quant-ph},
      url={https://arxiv.org/abs/1901.11054}, 
}
```

### QMRP & Hyperbolic Protection
- **Title**: *Geometry-optimized hyperbolic codes for modular fault-tolerant quantum architectures*
- **Authors**: Ahmed Adel Mahmoud (`ahmed.mahmoud@usask.ca`) and Steven Rayan (`rayan@math.usask.ca`)
- **Affiliation**: Centre for Quantum Topology and Its Applications (quanTA), Department of Mathematics and Statistics, University of Saskatchewan, Saskatoon, Saskatchewan, Canada
- **Submission Date**: 07 Oct 2026
- **Citation**: arXiv:2610.10948v1 [quant-ph]
- **arXiv Link**: [arXiv:2610.10948](https://arxiv.org/abs/2610.10948)
- **HTML View & References**: [https://arxiv.org/html/2610.10948v1#bib](https://arxiv.org/html/2610.10948v1#bib)
- **License**: CC BY-NC-ND 4.0

```bibtex
@misc{mahmoud2026geometryoptimizedhyperboliccodesmodular,
      title={Geometry-optimized hyperbolic codes for modular fault-tolerant quantum architectures},
      author={Ahmed Adel Mahmoud and Steven Rayan},
      year={2026},
      eprint={2610.10948},
      archivePrefix={arXiv},
      primaryClass={quant-ph},
      url={https://arxiv.org/abs/2610.10948},
      note={quanTA, University of Saskatchewan. License: CC BY-NC-ND 4.0}
}
```

---

## 8. AI Usage Statement

In accordance with competition rules and guidelines, AI assistance (Google Antigravity / Gemini) was utilized during the development and iteration of this project for:
1. **Architectural Scaffolding & Modularization**: Structuring the repository into modular components for offline fake backend management, topological graph ingestion, and compilation pass managers.
2. **Circuit Movement Optimization**: Ideating and verifying the zero-input movement simplifier ([`simplify_zero_input_movement`](src/qweave/bell_routing.py)), which recognized that workspace qubits initialized in $|0\rangle$ do not require bidirectional SWAP exchanges, cutting native two-qubit gate overhead in half.
3. **Rigorous Statistical Formulations**: Implementing simultaneous 95% Hoeffding sampling bounds and Bonferroni-adjusted Clopper-Pearson difference intervals for fidelity measurements.
4. **Rich Visualizations**: Assisting in the generation of Plotly-based interactive network graphs and circuit phase flows ([`results/visual_summary.html`](results/visual_summary.html)).

All quantum circuits, error models, and scientific interpretations were independently audited and verified against exact Qiskit simulation targets.

---

## 9. Reproducibility & Viewing Results

### A. Setup & Locked Dependencies

- **Python Requirement**: `Python 3.12+`
- **Install `uv`** ([Standalone Installer Guide](https://docs.astral.sh/uv/getting-started/installation/#standalone-installer)):
  - **macOS and Linux**:
    ```sh
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
  - **Windows (PowerShell)**:
    ```powershell
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```
- **Clone Repository & Sync Dependencies**:
  ```sh
  git clone https://github.com/Quantum-Detour/QWeave.git
  cd QWeave
  uv sync
  ```

### B. Execution & Results
Run the complete benchmark suite across all processors:
```sh
uv run qweave --noise backend --processor all
```

**Results Locations:**
- **Terminal Summary**: Prints the audited quantitative comparison table and circuit metrics directly to the terminal.
- **Interactive Visual Report**: Automatically compiled and written to [`results/visual_summary.html`](results/visual_summary.html). Open this HTML file in any web browser to view the interactive coupling topologies, multi-phase circuit timelines, and dynamic fidelity/overhead charts.

