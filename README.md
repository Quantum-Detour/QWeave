# QWeave

QWeave is a work in progress for the QMRP routing study described in
[qmrp-project-overview.md](qmrp-project-overview.md). The implementation plan is
in [qmrp-todo.md](qmrp-todo.md).

## First circuit scaffold

The `src/qweave` package currently builds a Bell pair at two physical output
ports on each of three processor graphs. It prepares the pair on adjacent
sites, then uses explicit SWAPs along a deterministic shortest path to move
one Bell partner to port B. The untouched reference qubit remains at port A.
The circuit builder can include terminal measurements or return an unmeasured
circuit for later analysis.

| Processor ID | Sites | Provisional ports | Graph source |
| --- | ---: | --- | --- |
| `five_node` | 5 | 0, 4 | Branching-tree interpretation of the challenge overview |
| `ibm_heavy_hex` | 127 | 0, 15 | `FakeSherbrooke`, matching the supplied transpilation notebook |
| `hyperbolic_inspired` | 22 | 8, 18 | Three-layer radial expansion scaffold (1 + 7 + 14 vertices) |

These graph and port choices are **provisional** until the organizer definitions
are available. The radial graph is not yet a verified hyperbolic tiling. This
custom backends use bidirectional CX on every configured graph edge. The IBM
backend supplies its own native gate directions and calibrations. Both noiseless
and noisy CLI runs compile to the selected backend's native target. The builder
retains explicit SWAPs; executed circuits contain their native decomposition.
The current circuit is an unprotected baseline.

The IBM model previously used the 16-site Guadalupe graph. It now uses the
127-site Sherbrooke graph; earlier results represent a different hardware model.

Install the locked environment and inspect all three circuits:

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

`--shots` is the total budget **per processor per noise setting**, shared evenly across XX, YY,
and ZZ; remainder shots go to XX and then YY. The default is 1,024 shots per
basis. Each basis uses seed + its index (0, 1, 2). The simulator uses Aer's
matrix product state method without a bond-dimension cap. Every shot
is retained, with no postselection. The measured estimate is not clipped or
given the exact-state PASS threshold: general states have sampling variation.
Noisy runs also retain all shots and report 100% acceptance with zero discards.

## Noisy baseline

Use `--noise none` (the default) for the ideal reference, or `--noise backend`
for matched ideal and noisy runs. Manual bit-flip probabilities are removed.
Both modes use the selected backend's native gates and fixed physical placement.

Each comparison arm receives the full requested shot budget: 3,072 shots means
6,144 total attempts per processor with `--noise backend`. Both arms share the
same native circuits and seed schedule. There is no protection or postselection.
`--show-circuit` displays executed native instructions; simulator noise is not
drawn as additional gates.

## Backend-derived noise on all three graphs

`--noise backend` now selects a backend appropriate to each processor:

| Processor | Backend | Source of noise properties |
| --- | --- | --- |
| `five_node` | `GenericBackendV2` on the current five-node graph | Seeded synthetic properties |
| `ibm_heavy_hex` | `FakeSherbrooke` from the supplied notebook | Packaged calibration snapshot |
| `hyperbolic_inspired` | `GenericBackendV2` on the current radial graph | Seeded synthetic properties |

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
backends also do not resolve the pending organizer graph/port definitions or
replace the radial placeholder with a verified hyperbolic lattice.

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
`generate_preset_pass_manager`. For the current pre-routed A baseline, we use
optimization level **0**, fixed identity placement, and `routing_method="none"`
so translation preserves the chosen route and output ports. The notebook's
level-3 example optimizes and routes general logical circuits; copying those
settings here could change the routing method being compared. Native operations
are checked against the target, and the native preparation receives its own
exact ideal-fidelity check. SABRE integration remains a separate task.

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
# Directed native gate error/duration data for future noise-aware route costs:
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
physical_route = built.route
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
