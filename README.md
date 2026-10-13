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
it does not use IBM native gate directions, calibrations, or noise. A SWAP is
still a Qiskit SWAP operation here, so the gate summary is not a native-gate
cost. The current circuit is a basic unprotected baseline, not QMRP.

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

`--shots` is the total budget **per processor**, shared evenly across XX, YY,
and ZZ; remainder shots go to XX and then YY. The default is 1,024 shots per
basis. Each basis uses seed + its index (0, 1, 2). The simulator uses Aer's
matrix product state method without noise or a bond-dimension cap. Every shot
is retained, with no postselection. The measured estimate is not clipped or
given the exact-state PASS threshold: general states have sampling variation.
Confidence intervals and noisy runs remain future work.

The exact-state check is an ideal simulation diagnostic without shots or noise. It verifies
both quantum coherence and output placement; Z-basis counts alone would not
establish Bell-state fidelity. Full statevector verification is capped at 22
qubits, covering the current models. The provisional topology definitions
still need confirmation independently of circuit correctness.

The same builders and verification function are available to notebooks:

```python
from qweave import (
    bell_fidelity, build_bell_circuit, build_ideal_bell_circuit,
    run_bell_measurements,
)

built = build_bell_circuit("ibm_heavy_hex", measure=False)
physical_circuit = built.circuit
physical_route = built.route
ideal_reference = build_ideal_bell_circuit(measure=False)
fidelity = bell_fidelity(physical_circuit, built.processor.output_ports)
print(f"Ideal Bell fidelity: {fidelity:.12f}")
result = run_bell_measurements(physical_circuit, built.processor.output_ports)
print(result.correlations, result.fidelity, result.counts)
```

The processor catalog and NetworkX graphs live in `qweave.processors`; circuit
construction lives in `qweave.circuits`. Routing methods, native compilation,
noise, protection, and noisy simulation remain on the project task list.
Exact ideal verification lives in `qweave.verification`; the measurement-based
Bell metric lives in `qweave.measurements`. Both currently cap inputs at 22 qubits.

Run the verification tests with:

```sh
uv run python -m unittest discover -s tests -v
```
