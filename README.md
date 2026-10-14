# QWeave

QWeave is a work in progress for the QMRP routing study described in
[qmrp-project-overview.md](qmrp-project-overview.md). The implementation plan is
in [qmrp-todo.md](qmrp-todo.md).

## First circuit scaffold

The `src/qweave` package compares shortest path, SABRE, noise-aware routing,
and QMRP Bell preparation. The main multipath suite uses the custom five-node,
IBM, and hyperbolic graphs; the original five-node tree remains a separate
archived reference. `--processor all` runs only the custom five-node, IBM, and
hyperbolic configurations. The tree is available only through explicit
`--processor five_node` selection.

All methods prepare the Bell state from all-zero physical inputs and return it
to the same output ports. Zero workspace identities are unrestricted. A/C prepare
locally and transport outward; SABRE's initial product-state permutations are
simplified under the same zero-input assumption. QMRP prepares and encodes locally,
then moves encoded components outward. The general `route_circuit` interface still
preserves arbitrary-input wire semantics and performs full restoration.

| Processor ID | Sites | Provisional ports | Graph source |
| --- | ---: | --- | --- |
| `five_node` | 5 | 0, 4 | Preserved original provisional branching tree |
| `five_node_multipath` | 5 | 0, 4 | Custom cycle with reference leaf; chosen to enable multipath, not organizer-confirmed |
| `ibm_heavy_hex` | 127 | 0, 15 | `FakeSherbrooke`, matching the supplied transpilation notebook |
| `hyperbolic_inspired` | 85 | 5, 31 | Frozen HYPERTILING `{7,3}` cell-adjacency graph, SRS kernel, four layers |

These graph and port choices are **provisional** until the organizer definitions
are confirmed. The hyperbolic model now comes from a regular tiling; its
parameters and cell-based qubit placement are our provisional choices. The
custom backends use bidirectional CX on every configured graph edge. The IBM
backend supplies its own native gate directions and calibrations. Both noiseless
and noisy CLI runs compile to the selected backend's native target. The builder
retains explicit SWAPs; executed circuits contain their native decomposition.
A/B/C are unprotected; QMRP uses syndrome postselection when routing is feasible.

The IBM model previously used the 16-site Guadalupe graph. It now uses the
127-site Sherbrooke graph; earlier results represent a different hardware model.

Install the locked environment and inspect the circuits:

```sh
uv sync
uv run qweave
uv run qweave --processor five_node --show-circuit
```

Every CLI run verifies the unmeasured preparation with Qiskit's exact
statevector simulator, extracts the two output qubits with `partial_trace`,
and compares them to the ideal Bell state using `state_fidelity`. It prints
`ideal Bell fidelity` and `PASS` when the value is within `1e-10` of 1 (zero
relative tolerance). Any failed check causes a nonzero exit status.
The CLI also runs three separate noiseless measurement experiments on Aer
and computes the required challenge metric:

```text
<PP> = (N00 + N11 - N01 - N10) / shots_in_basis
F(Phi+) = (1 + <XX> - <YY> + <ZZ>) / 4
```

XX uses H before measurement on each output; YY uses S-dagger followed by H;
ZZ measures directly. Raw two-bit counts and correlations are printed for
each basis. The ideal Bell state gives XX = +1, YY = -1, ZZ = +1, and fidelity
1. The optional drawings and gate summaries now cover all three measurement
circuits, including their basis rotations.

```sh
uv run qweave --shots 3072 --seed 42
```

`--shots` is the total budget **per algorithm per processor per noise setting**, shared evenly across XX, YY,
and ZZ; remainder shots go to XX and then YY. The default is 1,024 shots per
basis. Each basis uses seed + its index (0, 1, 2). The simulator uses Aer's
matrix product state method without a bond-dimension cap. A/B/C retain every shot. QMRP accepts only shots with all syndrome bits zero. The measured estimate is not clipped or
given the exact-state PASS threshold: general states have sampling variation.
Protected runs report accepted and discarded shots separately; a passed check does not imply an error-free state.

## Noisy baseline

Use `--noise none` (the default) for the ideal reference, or `--noise backend`
for matched ideal and noisy runs. Manual bit-flip probabilities are removed.
Both modes use the selected backend's native gates and fixed physical placement.

Each comparison arm receives the full requested shot budget: 3,072 shots means
6,144 total attempts per algorithm per processor with `--noise backend`. Both arms share the
same native circuits and seed schedule. Postselection applies only to protected QMRP execution.
`--show-circuit` displays executed native instructions; simulator noise is not
drawn as additional gates.

## Backend-derived noise on all graphs

`--noise backend` now selects a backend appropriate to each processor:

| Processor | Backend | Source of noise properties |
| --- | --- | --- |
| `five_node`, `five_node_multipath` | Separate `GenericBackendV2` instances on their respective graphs | Seeded synthetic properties |
| `ibm_heavy_hex` | `FakeSherbrooke` from the supplied notebook | Packaged calibration snapshot |
| `hyperbolic_inspired` | `GenericBackendV2` on the frozen HYPERTILING graph | Seeded synthetic properties |

```sh
uv run qweave --processor five_node --show-circuit --noise backend
uv run qweave --processor hyperbolic_inspired --noise backend
uv run qweave --noise backend --backend-seed 1234 --seed 42 --report backend-baselines.json
```

The custom backends explicitly receive the existing graph's edges, with CX
allowed in both directions, and basis `id, rz, sx, x, cx`. We set
`noise_info=True`, so Qiskit generates per-site relaxation/readout properties
and per-gate errors and durations. These are hardware-inspired random defaults,
not measured calibrations or proof of realistic noise for those geometries.
See the [GenericBackendV2 documentation](https://docs.quantum.ibm.com/api/qiskit/2.0/qiskit.providers.fake_provider.GenericBackendV2).

`--backend-seed` fixes the generated properties independently of `--seed`,
which controls compilation and sampling. Reuse the backend seed and locked
package versions across routing methods. Reports include the generation
configuration and a hash of the actual generated target properties, and label
them `generated_synthetic` with no calibration date. Sherbrooke is labeled
`calibration_snapshot`; its properties are unaffected by `--backend-seed`.
Each model's clean and noisy runs use the same native circuit and shot budget.

This combined suite has different noise properties and native gate sets across
models. Differences in results therefore cannot be attributed to topology
alone. Generic
backends supply noise properties; HYPERTILING supplies the third model's geometry.
Organizer confirmation of the chosen graph parameters and ports remains pending.

## Sherbrooke snapshot from the supplied notebooks

Use the **FakeSherbrooke** backend from `transpile-with-pass-managers.ipynb`:

```sh
uv run qweave --processor ibm_heavy_hex --noise backend --report sherbrooke-baseline.json
```

This runs matched noiseless and calibrated noisy experiments on the same native
circuits. The 127-site graph, native target, gate directions, per-gate errors
and durations, and readout calibration all come from the same offline snapshot.
The current locked snapshot is dated **2025-02-26**. The report includes its
SHA256 fingerprint, package versions, compiler settings, seeds, ports, route,
counts, fidelity intervals, and executed QASM 3 circuits. It requires no IBM
account or cloud execution. `--show-circuit` omits idle wires for readability.

The native basis includes ECR, RZ, SX, and X. Basis rotations and SWAPs are
translated before execution. Qiskit's
[NoiseModel.from_backend](https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.noise.NoiseModel.html#qiskit_aer.noise.NoiseModel.from_backend)
constructs approximate calibration-derived gate depolarization, thermal
relaxation during gates, and readout errors. This is a model of a historical
snapshot, not a complete reproduction of hardware noise. Unscheduled idle-time
relaxation is excluded; explicit delay instructions are rejected in this mode.

As in the supplied transpilation notebook, compilation uses
`generate_preset_pass_manager` with **maximum optimization (level 3)** by default.
`OptimizationLevel` provides named settings `NONE`, `LIGHT`, `MEDIUM`, and
`MAXIMUM`. The CLI exposes `--optimization none|light|medium|maximum`; use `none`
to reproduce the earlier translation-only baseline. All algorithms and both
measurement arms use the same selected setting.

The circuits are already routed, so fixed identity placement, trivial layout,
and `routing_method="none"` remain explicit. Maximum optimization may cancel or
resynthesize gates within the routed circuit; native gate counts and QASM are
the executed workload, whereas routing/restoration SWAP lists describe the input
to optimization. Target validation and placement checks remain active.
`approximation_degree=1.0` disallows approximate synthesis, and
`qubits_initially_zero=False` preserves operation semantics even when compiling
an isolated SWAP for cost estimation. This compiler flag does not change the
simulator's initial zero state. Level 3 is the highest preset, not a guarantee
of optimal gates, depth, or noisy fidelity.

Reports record the named and numeric level, approximation and layout settings.
Do not mix old level-0 and new level-3 results in one routing comparison.

The other supplied notebooks inform later work:

- `combine-error-mitigation-techniques.ipynb` and
  `error-mitigation-and-suppression-techniques.ipynb` demonstrate live-service
  mitigation options. This baseline enables no mitigation, twirling, or DD.
- `challenge_3_tutorial.ipynb` is the separate noiseless TFIM spin-chain example.

Sherbrooke's calibration values are used only on its own sites and edges.
The other graphs generate their own properties through `GenericBackendV2`.
All three use `NoiseModel.from_backend` with gate errors, gate-time relaxation,
and readout noise, retaining the same exclusions for idle delays and mitigation.

All later routing methods can share one test-bed instance and submit their
already routed physical circuits to the same compiler and simulator:

```python
from qweave import FakeBackendTestbed, build_bell_circuit, run_bell_measurements

testbed = FakeBackendTestbed.sherbrooke(compiler_seed=42)
built = build_bell_circuit(testbed.processor((0, 15)), measure=False)
clean = run_bell_measurements(built.circuit, (0, 15), testbed=testbed)
noisy = run_bell_measurements(
    built.circuit, (0, 15), testbed=testbed, backend_noise=True,
)
# Directed native gate error/duration data:
calibrations = testbed.gate_calibrations()
```

For a custom graph, substitute a seeded generic test bed:

```python
testbed = FakeBackendTestbed.for_processor("five_node", backend_seed=1234, compiler_seed=42)
processor = testbed.processor((0, 4), name="five_node")
built = build_bell_circuit(processor, measure=False)
noisy = run_bell_measurements(
    built.circuit, processor.output_ports, testbed=testbed, backend_noise=True,
)
```

## Frozen hyperbolic lattice

The radial placeholder has been replaced with a finite cell-adjacency graph
from [HYPERTILING](https://gitpages.physik.uni-wuerzburg.de/hypertiling/hyperweb/doc/examples/quickstart.html).
The construction is explicitly:

- Generator: HYPERTILING **1.5.1**, `HyperbolicTiling(7, 3, 4, kernel="SRS", center="cell")`.
- Geometry: regular `{7,3}` tiling (heptagons, three meeting at each vertex).
- Qubits: **polygon centers**, with edges from `get_nbrs_list()` (SRS default `RO` radius search).
- Size: **85 qubits, 196 undirected edges**; four library-defined layers, with no forced node count.
- Interior degree: **7**, with smaller degrees at the finite boundary. This is not a degree-3 polygon-vertex graph.
- Frozen output ports: **(5, 31)**, distance **6**; selected once as the lexicographically smallest pair attaining graph diameter.
- Backend: seeded GenericBackendV2 on these exact edges, with bidirectional CX.

The packaged artifact [hyperbolic_7_3_cells.json](src/qweave/data/hyperbolic_7_3_cells.json)
records the generator version, parameters, edge list, ports, degree distribution,
and Poincare disk cell-center coordinates. Experiments load this file without
regenerating it or reselecting ports. CLI output includes its SHA256; JSON reports
include the fingerprint and topology metadata alongside the full edge list.
The graph fingerprint is distinct from the backend noise-property fingerprint.

To intentionally regenerate the artifact using the locked environment:

```sh
uv sync --locked
uv run python scripts/generate_hyperbolic.py
```

Regeneration checks reciprocal adjacency, connectivity and maximum degree, and
then writes the graph and chosen ports. Review the artifact diff before using
new results. The construction is a **provisional project model**, not a claimed
organizer-provided graph. Confirm the required graph with the organizers before
finalizing the common benchmark. Historical 22-node radial results describe a
different model and must not be mixed with these results.

The 85-cell count need not match Sherbrooke's 127 sites. Degree, distance, native
gates and noise differ as well, so results do not isolate hyperbolic geometry.
Four layers provide a small lattice with multiple routes while keeping this Bell
experiment's active circuit small; arbitrary large uploaded circuits may still
exceed the exact-verification resource limit.

## Shortest path, SABRE, and noise-aware routing

```sh
# All four methods, same backend instance and properties for each processor:
uv run qweave --algorithm all --noise backend --report routing-comparison.json
# SABRE alone, including all three measurement circuit drawings:
uv run qweave --algorithm sabre --processor hyperbolic_inspired --noise backend --show-circuit
```

The CLI default is `--algorithm all`; the Python builder defaults to `shortest_path`. `qweave.routing` contains the
strategy registry and a common routing interface. Shortest path moves the second
CX operand towards the first using a deterministic shortest path. SABRE uses
Qiskit's [SabreSwap](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.transpiler.passes.SabreSwap)
with `heuristic="decay"`, `trials=1`, and `seed=--seed`. There is no SABRE layout
search. All methods receive the same all-zero input state and fixed output ports. The seed and
explicit trial count make the SABRE settings reproducible with locked versions.
All routers use the same physical adjacency; the common native
compiler then enforces the backend's actual gate directions.

All methods share the zero-input movement simplifier, backend-native
compilation at the selected optimization level, exact verification, XX/YY/ZZ basis changes, simulation,
noise, uncertainty, and reporting. Each processor's backend is constructed once
and reused across methods. Measurement circuits are compiled once per method
and reused unchanged in the noiseless and noisy arms. Shot budgets and sampling
seeds match between methods; their routed gate sequences can differ.

**Audited fixed-output policy:** only the physical Bell output ports must match.
Initial permutations of zero states need no physical gates. Shortest path uses
`d - 1` outward SWAPs for distance `d`. Noise-aware routing minimizes a local CX
plus one-way SWAP costs. SABRE still chooses the meeting sites, but initial
SWAPs are eliminated by moving its pending H to the meeting site. All remaining
SWAPs carry actual state toward the outputs; they are not deleted merely because
the older router called them restoration. QMRP receives the same simplification.

This benchmark is `zero-input-fixed-output-bell-v3`. It replaces the unnecessarily
strict wire-identity policy used by earlier Bell runs. It is valid for all-zero
state preparation, not arbitrary unknown inputs. The generic unitary router is
unchanged. Old `fixed-port-logical-bell-v2` results are not directly comparable.

JSON reports use schema version 4 and include the routing algorithm/settings,
initial/routed/final placements, routing and restoration SWAP lists, routing
runtime (including restoration), and routed preparation QASM. The displayed
shortest reference path is a graph diagnostic; SABRE's actual movement is its
SWAP trace. The current routing interface is limited to H/CX preparation inputs;
general circuit uploads remain future work. This small Bell workload alone does
not establish which routing method is better on larger circuits.

Python callers select the strategy without changing the measurement pipeline:

```python
from qweave import BackendOperationCosts, prepare_bell_measurements, sample_bell_measurements

costs = BackendOperationCosts(testbed)
for algorithm in ("shortest_path", "sabre", "noise_aware"):
    built = build_bell_circuit(processor, measure=False, algorithm=algorithm, seed=42, costs=costs)
    prepared = prepare_bell_measurements(built.circuit, processor.output_ports, testbed=testbed)
    clean = sample_bell_measurements(prepared, testbed=testbed, shots=3072, seed=42)
    noisy = sample_bell_measurements(
        prepared, testbed=testbed, backend_noise=True, shots=3072, seed=42,
    )
```

## Method C: noise-aware weighted routing

```sh
uv run qweave --processor hyperbolic_inspired --algorithm noise_aware --noise backend --report noise-aware.json
```

`BackendOperationCosts` reads the experiment's existing backend `Target`. It
compiles an isolated CX or SWAP using the same full-width, fixed-layout compiler and selected optimization level as execution, then sums `-log1p(-gate_error)` over its native gates,
including introduced single-qubit gates. Costs are cached per ordered operation
and qubit pair. These are classical compilations: route selection runs no quantum
shots and performs no noisy simulations. Keep the backend unchanged while using
a cost provider; create a new provider for a different calibration/configuration.

For Bell preparation at outputs R and D, C tries each neighbor N of R. It
charges `CX(R,N)` plus the cheapest directed SWAP path from N to D, excluding R.
Each outward SWAP is charged **once**. It prepares `H(R); CX(R,N)` locally and
transports the entangled partner to D. No zero-state prepositioning is emitted.
The generic unknown-input `route_circuit` API retains its original round-trip
routing costs; the Bell-specific builder uses the audited one-way objective.

Node/edge insertion and neighbor iteration are sorted for reproducible Dijkstra
ties. Candidate ties use cost, then SWAP count, then the returned transport node
sequence. No alternative native decomposition is selected only for C. Reported
costs are native-gate error heuristics, not predicted fidelity or exact operation
failure probabilities. Extra readout/duration penalties are excluded; fixed-port
Bell preparation/readout are common, and scheduled idle noise is not modeled.

Zero gate error contributes zero. Error 1 makes an operation unusable; missing,
nonfinite or out-of-range errors produce explicit diagnostics. No finite route
means failure rather than an unreported shortest-path fallback. An existing
provider must match the processor width and graph; pass the same test bed used
for measurements to preserve noise assumptions.

Reports label this method **C** and record model `native-negative-log-gate-error-v2`,
backend fingerprint and compiler settings, selected transport paths, CX/SWAP native-gate breakdowns,
any restoration costs, and estimated total routing cost. At higher optimization
levels the sum of isolated-operation costs generally differs from the full
optimized circuit cost because gates can cancel across operation boundaries.
Method C does not compile/simulate every candidate full circuit to rank paths. `runtime_seconds` excludes
new cost compilation; `cost_preparation_seconds` records that CPU work separately.
Repeated calls reuse cached costs. The final measured fidelity determines whether
the choice helped; neither a longer path nor a lower score guarantees improvement.
The five-node tree has no alternative simple path and may match A exactly.

Research motivation: Murali et al., [Noise-Adaptive Compiler Mappings for Noisy
Intermediate-Scale Quantum Computers](https://arxiv.org/abs/1901.11054). This is a
simpler weighted-routing baseline, not a reproduction of their compiler.

## Sampling uncertainty

The API and CLI report a conservative 95% interval based on Hoeffding's
inequality. For each basis, the even-parity frequency estimates probability p.
With N shots, use `epsilon = sqrt(log(6 / 0.05) / (2*N))` and bound p within
`[max(0, p-epsilon), min(1, p+epsilon)]`. Transform these bounds to correlations
with `2*p-1`, then propagate through the fidelity formula, reversing the YY
endpoints because its sign is negative. A union bound accounts for all three
bases. This avoids claiming zero uncertainty when all observed parities agree.

The bounds assume independent shots and cover sampling variation only. With
noisy measurement rotations or readout, the reported quantity is the observed
Bell-fidelity estimator; the interval does not correct measurement bias or
uncertainty in the chosen noise model. Neither the estimate nor its interval
is clipped to the physical fidelity range.

## Python API and verification

The exact-state check is an ideal simulation diagnostic without shots or noise. It verifies
both quantum coherence and output placement; Z-basis counts alone would not
establish Bell-state fidelity. Exact verification compacts the circuit to its
active sites plus the two outputs, and is capped at 22 such qubits. Unused
sites remain in an independent zero state, so omitting them is exact. This
avoids allocating a 127-qubit statevector. Native compilation and noisy
simulation retain the original physical indices so calibration errors stay
attached to the correct sites. The provisional topology definitions
still need confirmation independently of circuit correctness.

The same builders and verification function are available to notebooks:

```python
from qweave import (
    bell_fidelity, build_bell_circuit, build_ideal_bell_circuit,
    run_bell_measurements, FakeBackendTestbed,
)

testbed = FakeBackendTestbed.for_processor("ibm_heavy_hex")
built = build_bell_circuit(testbed.processor((0, 15)), measure=False)
physical_circuit = built.circuit
shortest_reference_path = built.route
routing_trace = built.routing
ideal_reference = build_ideal_bell_circuit(measure=False)
fidelity = bell_fidelity(physical_circuit, built.processor.output_ports)
print(f"Ideal Bell fidelity: {fidelity:.12f}")
result = run_bell_measurements(physical_circuit, built.processor.output_ports, testbed=testbed)
print(result.correlations, result.fidelity, result.counts)
noisy = run_bell_measurements(
    physical_circuit, built.processor.output_ports,
    testbed=testbed, backend_noise=True,
)
print(noisy.fidelity, noisy.fidelity_interval, noisy.noise)
# Exact executed circuits, including basis rotations and SWAP decomposition:
print(noisy.circuits["ZZ"])
```

Backend inputs live in `qweave.processors.PROCESSOR_CONFIGS`; the `PROCESSORS`
catalog lazily derives connectivity from the default seeded backends. These
configuration inputs still contain the provisional custom graph edges.
`FakeBackendTestbed.for_processor` constructs a backend with explicit seeds for
each experiment. Circuit construction lives in `qweave.circuits`; native
compilation and backend noise live in `qweave.backends`. Standalone ideal API
circuits without a test bed use gate translation in `qweave.compilation`. Other routing methods, protection, and additional noise
models remain on the project task list.
Exact ideal verification lives in `qweave.verification`; the measurement-based
Bell metric lives in `qweave.measurements`. Both cap preparation inputs at 22
active qubits plus outputs, while allowing larger hardware graphs.

Run the verification tests with:

```sh
uv run python -m unittest discover -s tests -v
```

## QMRP and the custom five-node graph

The current movement audit is in [qmrp-movement-audit.md](qmrp-movement-audit.md).
The current user-supplied log is summarized in [qmrp-results.md](qmrp-results.md).
The separate multi-seed experiment was not completed; its generated artifacts were removed at the user’s request.

```sh
uv run qweave --processor five_node_multipath --algorithm all --noise backend --report comparison.json
uv run qweave --processor five_node_multipath --algorithm qmrp --noise backend --show-circuit
uv run qweave --processor five_node --algorithm qmrp --noise backend
```

The custom edges are `(0,1), (1,2), (2,3), (3,4), (4,1)`, with Bell ports
`(0,4)`. This is a project-designed multipath example, **not a confirmed
organizer reference**. The original tree is unchanged. A backend seed freezes
properties within a topology; it does not make different graphs share identical
edge errors. Reports retain the actual edges and backend fingerprint.

For this custom graph the planner finds launches `(1,2)`, transport paths
`1→4` and `2→3`, and decoding `CX(4,3)`. It prepares `H(0); CX(0,1)`
and encodes with `CX(1,2)` directly. There is no initial `4→1` SWAP: both sites
start at zero. Both outward SWAPs and every preparation/decoding gate receive
noise. Paths are discovered, not hardcoded.

On every graph, the same planner searches distinct launch/arrival sites using
capacity-one node splitting and two-unit min-cost flow. It excludes the stationary
reference and uses cached directed native CX/SWAP costs, including a local
encoding CX and one-way transport of the ancilla component to its launch site. Flow costs are rounded to 1e-12, with hop count breaking ties;
endpoint candidates are compared deterministically by their unrounded total cost.
These are gate-error heuristics, not fidelity predictions. The initial H is common
and omitted from the routing score. No quantum runs are used to select routes.

The selected circuit is compiled at the same optimization setting as A/B/C.
Barriers preserve QMRP preparation, encoding, transport, and decoding phases.
All methods have a preparation-to-measurement barrier. Optimization is therefore
allowed within these boundaries; protected operations cannot cancel across them.
This intentional extra constraint for D is part of its reported overhead.

QMRP measures the syndrome in Z before Bell basis rotations and accepts zero.
Both accepted-only fidelity and the same execution without postselection are
computed from the **same raw samples**. Each basis reports accepted/discarded
counts and a 95% acceptance interval. Bell intervals use accepted sample sizes;
if any basis has zero accepted shots, conditional fidelity and its interval are
JSON `null` and printed as undefined. `without_postselection` still remains defined.

A single X on either encoded component before an ideal decoder is rejected.
Single Z and double X errors may pass; reference, preparation, decoding and
readout faults also matter. No recovery, erasure correction, or guaranteed
improvement is claimed. This is a literature-inspired on-chip adaptation, not a
reproduction of the quantum-network aggregation or parallel-spin-chain protocols.

When no pair is feasible, D reports `unprotected_fallback`, executes A, and has
zero multipath coverage. No additional experiment is run. The original tree
exercises this case only when explicitly selected.
Simulator resource limits have a separate status and do not trigger a routing fallback.

Schema 4 adds raw joint counts, acceptance rules, marginal results without
postselection, syndrome diagnostics, paths, cost breakdowns, phase boundaries,
wire-placement records, decoded logical placement, active qubit counts, and native two-qubit gate counts.
The placement records describe SWAP permutations; while encoded, neither rail
is an independent copy of the logical data. Multipath coverage counts protected
transport blocks, not the fraction of all circuit gates protected. Shot-level
playback and arbitrary uploaded circuits remain future work.

### Module responsibilities

- `routing.py`: general circuit routing and shared routing records.
- `bell_routing.py`: all-zero Bell preparation and common movement simplification.
- `protection.py`: QMRP planning, encoding, transport and decoding; used by the main CLI.
- `measurements.py`: shared sampling, postselection and Bell measurement analysis.
- `comparison.py`: confidence intervals for differences between methods.
- `scripts/compare_bell_routing.py`: optional reproducible multi-seed experiment; uses the same package implementation.

For a completed saved experiment, generate its table without running any simulation:

```sh
uv run python scripts/compare_bell_routing.py --summarize-only
```

This command requires a complete checkpoint. Ordinary CLI runs do not invoke the multi-seed script.
