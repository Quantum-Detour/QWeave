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
| `ibm_heavy_hex` | 16 | 0, 15 | Coupling edges copied from `FakeGuadalupeV2` in `qiskit-ibm-runtime` 0.50.0 |
| `hyperbolic_inspired` | 22 | 8, 18 | Three-layer radial expansion scaffold (1 + 7 + 14 vertices) |

These graph and port choices are **provisional** until the organizer definitions
are available. The radial graph is not yet a verified hyperbolic tiling. This
first suite uses a synthetic bidirectional CX assumption on every graph edge;
it does not use IBM native gate directions or calibrations. The builder retains
explicit SWAPs, while executed measurement circuits translate each SWAP into
three CX gates. The reported gate costs use a common synthetic basis, not an
IBM native target. The current circuit is an unprotected baseline.

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

Compare noiseless and noisy results on all three graphs:

```sh
uv run qweave --noise bit-flip
uv run qweave --processor five_node --noise bit-flip --p1 0.001 --p2 0.01 --readout-error 0.01 --shots 3072 --seed 42
```

These flags configure independent, uniform synthetic errors:

| Parameter | Default | Meaning |
| --- | ---: | --- |
| `--p1` | 0.001 | Probability of X after each one-qubit gate, including H/S-dagger measurement rotations |
| `--p2` | 0.01 | Probability of X independently on each participant after each CX, including all SWAP-decomposition CXs |
| `--readout-error` | 0.01 | Probability of flipping each reported measurement bit, symmetric for 0 and 1 |

For a CX, the four error probabilities are II: `(1-p2)^2`, IX and XI:
`p2*(1-p2)` each, and XX: `p2^2`. Thus p2 is not the probability of any error
on the entire two-qubit gate. Rates must be finite and between 0 and 1.
Setting all three rates to zero recovers the noiseless baseline.

Both comparison arms use identical circuits translated at optimization level
0 into `h, sdg, rz, sx, x, id, cx`, without layout changes or rerouting. Noise
is applied after these gates using Aer's [Pauli error channels](https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.noise.pauli_error.html)
and [readout errors](https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.noise.ReadoutError.html).
`--show-circuit` displays the executed gate sequence after SWAP decomposition;
the stochastic errors are simulator settings, not extra drawn gates.

Each comparison arm receives the full requested shot budget, so 3,072 shots
means 6,144 total attempts per processor when noise is enabled. The same seed
schedule is recorded for both arms. No protection or postselection is applied.
These settings are provisional and independent of hardware calibrations or
organizer assumptions. Idle-time noise, depolarizing noise, and relaxation
remain future work.

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
establish Bell-state fidelity. Full statevector verification is capped at 22
qubits, covering the current models. The provisional topology definitions
still need confirmation independently of circuit correctness.

The same builders and verification function are available to notebooks:

```python
from qweave import (
    bell_fidelity, build_bell_circuit, build_ideal_bell_circuit,
    run_bell_measurements, BitFlipNoise,
)

built = build_bell_circuit("ibm_heavy_hex", measure=False)
physical_circuit = built.circuit
physical_route = built.route
ideal_reference = build_ideal_bell_circuit(measure=False)
fidelity = bell_fidelity(physical_circuit, built.processor.output_ports)
print(f"Ideal Bell fidelity: {fidelity:.12f}")
result = run_bell_measurements(physical_circuit, built.processor.output_ports)
print(result.correlations, result.fidelity, result.counts)
noisy = run_bell_measurements(
    physical_circuit, built.processor.output_ports,
    noise=BitFlipNoise(single_qubit=0.001, two_qubit=0.01, readout=0.01),
)
print(noisy.fidelity, noisy.fidelity_interval, noisy.noise)
# Exact executed circuits, including basis rotations and SWAP decomposition:
print(noisy.circuits["ZZ"])
```

The processor catalog and NetworkX graphs live in `qweave.processors`; circuit
construction lives in `qweave.circuits`. Noise and synthetic gate translation
live in `qweave.noise`. Other routing methods, backend-native compilation,
protection, and additional noise models remain on the project task list.
Exact ideal verification lives in `qweave.verification`; the measurement-based
Bell metric lives in `qweave.measurements`. Both currently cap inputs at 22 qubits.

Run the verification tests with:

```sh
uv run python -m unittest discover -s tests -v
```
