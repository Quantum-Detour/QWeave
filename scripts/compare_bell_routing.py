"""Audit first, freeze native circuits, then compare C and QMRP across seeds.

Run with --prepare-only first. Re-running resumes missing batches without
recompilation. QPY and QASM hashes, native calibration properties and every raw
count are retained. The shot budget is fixed before sampling, not stopped based
on observed significance.
"""
import argparse
from collections import Counter
from dataclasses import asdict
from hashlib import sha256
import json
from math import isclose
from pathlib import Path
from time import perf_counter

import numpy as np
from qiskit import QuantumCircuit, qasm3, qpy

from qweave import BackendOperationCosts, FakeBackendTestbed, build_bell_circuit
from qweave.comparison import acceptance_summary, fidelity_difference
from qweave.measurements import BASES, prepare_bell_measurements, sample_bell_measurements, summarize_measurements
from qweave.processors import COMPARISON_PROCESSORS, PROCESSOR_CONFIGS
from qweave.verification import bell_fidelity, syndrome_zero_probability
from qweave.bell_routing import simplify_zero_input_movement

METHODS = ('noise_aware', 'qmrp')


def hyperbolic_route_audit(*, sample=False, batches=8, shots=24576):
    """Frozen old/new routes; no route search and no noise-model changes.

    Old ordered gate operands come from out(1).txt and qweave-qmrp-report-final.json;
    new ones come from out.log. Preserve operand order even for SWAP: the
    compiler can choose different directional decompositions for it.
    """
    bed = FakeBackendTestbed.for_processor('hyperbolic_inspired', backend_seed=1234, compiler_seed=42)
    expected = 'af013a8cd73da06768e75774e86f355895c5c3f559276a1bb7e2c277eb41864c'
    if bed.snapshot.snapshot_sha256 != expected:
        raise ValueError('Backend fingerprint changed; refusing comparison')
    costs = BackendOperationCosts(bed)
    definitions = {
        'C old': (2, None, [(1,2),(13,1),(26,13),(27,26),(31,27)]),
        'C new': (82, None, [(82,76),(76,73),(73,61),(61,0),(0,25),(25,27),(27,31)]),
        'D old': (2, (1, [(13,1),(26,13)]), [(2,1),(1,13),(13,25),(25,28),(26,27),(27,31)]),
        'D new': (82, (76, [(76,73),(73,61),(61,0),(0,25),(25,27)]), [(82,76),(76,73),(73,61),(61,0),(0,25),(25,28),(27,31)]),
    }
    prepared = {}
    records = {}
    print(f'Backend SHA256: {expected}', flush=True)
    print('| Route | CX/SWAP proxy | Compiled prep proxy (includes H) | SWAPs | ZZ native gates | ZZ depth |', flush=True)
    print('| --- | ---: | ---: | ---: | --- | ---: |', flush=True)
    for name, (launch, encoding, swaps) in definitions.items():
        circuit = QuantumCircuit(85)
        circuit.h(5); circuit.cx(5, launch)
        if encoding:
            circuit.barrier(label='bell_preparation')
            neighbor, moves = encoding
            circuit.cx(launch, neighbor)
            for u,v in moves:
                circuit.swap(u,v)
            circuit.barrier(label='encoding')
        for u,v in swaps:
            circuit.swap(u,v)
        if encoding:
            circuit.barrier(label='transport')
            circuit.cx(31,28)
            circuit.barrier(label='decoding')
        # Both old and new use local preparation plus outward-only movement.
        circuit, _ = simplify_zero_input_movement(circuit)
        if encoding:
            circuit.metadata = {'qweave_syndrome_sites': [28]}
        breakdown = {}
        phase = 'bell_preparation'
        for item in circuit.data:
            if item.operation.name == 'barrier':
                phase = {'bell_preparation':'encoding', 'encoding':'transport',
                         'transport':'decoding', 'decoding':'done'}[item.operation.label]
            elif item.operation.name in {'cx','swap'}:
                u,v = [circuit.find_bit(q).index for q in item.qubits]
                component = 'transport' if not encoding and item.operation.name == 'swap' else phase
                breakdown[component] = breakdown.get(component,0.) + costs.operation(item.operation.name,u,v).cost
        native = bed.compile(circuit)
        if sample:
            for candidate in (circuit, native):
                if not isclose(bell_fidelity(candidate,(5,31)),1.,abs_tol=1e-10,rel_tol=0):
                    raise ValueError(f'{name}: failed ideal Bell verification')
                if not isclose(syndrome_zero_probability(candidate,(5,31)),1.,abs_tol=1e-10,rel_tol=0):
                    raise ValueError(f'{name}: failed ideal syndrome verification')
        prepared[name] = prepare_bell_measurements(circuit,(5,31),testbed=bed)
        records[name] = dict(cost_breakdown=breakdown, estimated_cost=sum(breakdown.values()),
            preparation=costs.native_cost_record(native),
            measurements={b:costs.native_cost_record(c) for b,c in prepared[name].items()})
        zz = records[name]['measurements']['ZZ']
        print(f"| {name} | {sum(breakdown.values()):.8f} | {records[name]['preparation']['gate_cost']:.8f} | {circuit.count_ops().get('swap',0)} | {zz['gates']} | {zz['depth']} |", flush=True)
        print(f'Cost components {name}: {breakdown}', flush=True)
    if not sample:
        print('Compilation only. Fidelity differences require new samples of these simplified circuits.', flush=True)
        return
    print(f'Independent batches per route: {batches}; attempted shots per batch: {shots}; compiler seed: 42; backend seed: 1234; optimization: maximum',flush=True)
    for name, circuits in prepared.items():
        print(json.dumps(dict(route=name,native_circuit_hashes={b:native_record(c)['sha256'] for b,c in circuits.items()},
                              cost_audit=records[name])),flush=True)
    estimates = {}
    children = np.random.SeedSequence(20261014).spawn(len(prepared)*batches)
    seeds = [int(c.generate_state(1)[0]) % (2**32-3) for c in children]
    if len({s+i for s in seeds for i in range(3)}) != len(seeds)*3:
        raise ValueError('Overlapping simulator seeds')
    for index,(name,circuits) in enumerate(prepared.items()):
        raw = {b:Counter() for b in BASES}
        for batch in range(batches):
            seed = seeds[index*batches+batch]
            result = sample_bell_measurements(circuits,shots=shots,seed=seed,testbed=bed,backend_noise=True)
            print(json.dumps(dict(route=name,batch=batch,seed=seed,raw_counts=result.raw_counts)),flush=True)
            for b in BASES:
                raw[b].update(result.raw_counts[b])
        estimates[name] = summarize_measurements(raw,circuits,dict.fromkeys(BASES,batches*shots//3))
    for method in ('C','D'):
        old,new = estimates[f'{method} old'],estimates[f'{method} new']
        for selected in ((False,True) if method == 'D' else (False,)):
            attr = 'counts' if selected else 'unconditional_counts'
            print(json.dumps(dict(method=method,postselected=selected,
                difference_new_minus_old=fidelity_difference(getattr(old,attr),getattr(new,attr)),
                old_fidelity=old.fidelity if selected else old.unconditional_fidelity,
                new_fidelity=new.fidelity if selected else new.unconditional_fidelity,
                old_acceptance=acceptance_summary(sum(old.accepted_by_basis.values()),batches*shots),
                new_acceptance=acceptance_summary(sum(new.accepted_by_basis.values()),batches*shots))),flush=True)


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
    temporary.replace(path)


def native_record(circuit):
    text = qasm3.dumps(circuit)
    return dict(qasm3=text, sha256=sha256(text.encode()).hexdigest(),
                gates=dict(circuit.count_ops()), depth=circuit.depth(),
                two_qubit_gates=sum(len(item.qubits) == 2 and item.operation.name != 'barrier' for item in circuit.data),
                active_qubits=len({circuit.find_bit(q).index for item in circuit.data
                                   if item.operation.name != 'barrier' for q in item.qubits}))


def prepare(directory, batches, shots):
    manifest = dict(schema_version=1, benchmark='zero-input-fixed-output-bell-v3',
                    batches=batches, shots_per_batch=shots, backend_seed=1234, compiler_seed=42,
                    master_sampling_seed=20261013, processors={},
                    interval_method='six Bonferroni-adjusted exact Clopper-Pearson parity intervals; pointwise 95%')
    children = np.random.SeedSequence(manifest['master_sampling_seed']).spawn(len(COMPARISON_PROCESSORS)*len(METHODS)*batches)
    seeds = [int(child.generate_state(1)[0]) % (2**32-3) for child in children]
    assert len({seed+i for seed in seeds for i in range(3)}) == len(seeds)*3
    index = 0
    for name in COMPARISON_PROCESSORS:
        print(f'Auditing and freezing {name}', flush=True)
        bed = FakeBackendTestbed.for_processor(name, backend_seed=1234, compiler_seed=42)
        processor = bed.processor(PROCESSOR_CONFIGS[name].output_ports, name=name)
        costs = BackendOperationCosts(bed)
        entry = dict(snapshot=asdict(bed.snapshot), edges=processor.edges, ports=processor.output_ports,
                     provenance=processor.provenance,
                     gate_calibrations=[asdict(g) for g in bed.gate_calibrations()], audit={}, methods={})
        for method in ('shortest_path', 'sabre', *METHODS):
            built = build_bell_circuit(processor, measure=False, algorithm=method, seed=42, costs=costs)
            native = bed.compile(built.circuit)
            checks = dict(ideal_fidelity=bell_fidelity(built.circuit, processor.output_ports),
                          native_ideal_fidelity=bell_fidelity(native, processor.output_ports),
                          ideal_syndrome_zero=syndrome_zero_probability(built.circuit, processor.output_ports),
                          native_syndrome_zero=syndrome_zero_probability(native, processor.output_ports))
            assert all(isclose(value,1.,abs_tol=1e-10,rel_tol=0) for value in checks.values()), checks
            assert all(built.routing.final_layout[p] == p for p in processor.output_ports)
            entry['audit'][method] = dict(**checks, routing=asdict(built.routing),
                swaps=int(built.circuit.count_ops().get('swap',0)), native_preparation=native_record(native))
            print(f"  {method}: {entry['audit'][method]['swaps']} SWAPs; ideal/native checks PASS", flush=True)
            if method in METHODS:
                prepared = prepare_bell_measurements(built.circuit, processor.output_ports, testbed=bed)
                filename = f'{name}-{method}.qpy'
                with (directory/filename).open('wb') as stream:
                    qpy.dump([prepared[basis] for basis in BASES], stream)
                entry['methods'][method] = dict(qpy=filename,
                    qpy_sha256=sha256((directory/filename).read_bytes()).hexdigest(),
                    circuits={basis: native_record(c) for basis,c in prepared.items()},
                    simulator_seeds=seeds[index:index+batches])
                index += batches
        manifest['processors'][name] = entry
    save(directory/'manifest.json', manifest)
    return manifest


def run(directory, manifest):
    path = directory/'samples.json'
    samples = json.loads(path.read_text()) if path.exists() else {}
    for name, entry in manifest['processors'].items():
        bed = FakeBackendTestbed.for_processor(name, backend_seed=manifest['backend_seed'],
                                              compiler_seed=manifest['compiler_seed'])
        assert bed.snapshot.snapshot_sha256 == entry['snapshot']['snapshot_sha256']
        for method, frozen in entry['methods'].items():
            qpy_path = directory/frozen['qpy']
            assert sha256(qpy_path.read_bytes()).hexdigest() == frozen['qpy_sha256']
            with qpy_path.open('rb') as stream:
                circuits = dict(zip(BASES,qpy.load(stream)))
            assert all(native_record(circuits[b])['sha256'] == frozen['circuits'][b]['sha256'] for b in BASES)
            key = f'{name}/{method}'
            completed = samples.setdefault(key, [])
            assert [row['seed'] for row in completed] == frozen['simulator_seeds'][:len(completed)]
            for i in range(len(completed), manifest['batches']):
                started = perf_counter()
                result = sample_bell_measurements(circuits, shots=manifest['shots_per_batch'],
                    seed=frozen['simulator_seeds'][i], testbed=bed, backend_noise=True)
                completed.append(dict(seed=result.seed, raw_counts=result.raw_counts,
                    shots_by_basis=result.shots_by_basis, elapsed_seconds=perf_counter()-started))
                save(path, samples)
                print(f'{key}: batch {i+1}/{manifest["batches"]} saved ({perf_counter()-started:.1f}s)', flush=True)
    return samples


def summarize(directory, manifest, samples):
    # Do not label a partial checkpoint as a completed matched-budget study.
    for name, entry in manifest['processors'].items():
        for method, frozen in entry['methods'].items():
            key = f'{name}/{method}'
            batches = samples.get(key, [])
            if len(batches) != manifest['batches']:
                raise ValueError(f'{key}: {len(batches)}/{manifest["batches"]} batches saved; comparison incomplete')
            if [batch['seed'] for batch in batches] != frozen['simulator_seeds']:
                raise ValueError(f'{key}: saved seeds differ from the frozen manifest')
            expected_shots = manifest['shots_per_batch'] // len(BASES)
            if any(batch['shots_by_basis'] != dict.fromkeys(BASES, expected_shots) for batch in batches):
                raise ValueError(f'{key}: saved shot budgets differ from the frozen manifest')
    rows = []
    for name, entry in manifest['processors'].items():
        estimates = {}
        for method, frozen in entry['methods'].items():
            batches = samples[f'{name}/{method}']
            raw = {basis: dict(sum((Counter(batch['raw_counts'][basis]) for batch in batches), Counter())) for basis in BASES}
            shots = {basis: sum(batch['shots_by_basis'][basis] for batch in batches) for basis in BASES}
            with (directory/frozen['qpy']).open('rb') as stream:
                circuits = dict(zip(BASES, qpy.load(stream)))
            estimates[method] = summarize_measurements(raw,circuits,shots)
        c,d = (estimates[method] for method in METHODS)
        for method, result, postselected in (('C',c,False), ('D all shots',d,False), ('D postselected',d,True)):
            counts = result.counts if postselected else result.unconditional_counts
            fidelity = result.fidelity if postselected else result.unconditional_fidelity
            routing_method = 'noise_aware' if method == 'C' else 'qmrp'
            attempted = sum(result.shots_by_basis.values())
            retained = sum(result.accepted_by_basis.values()) if postselected else attempted
            rows.append(dict(processor=name, method=method, fidelity=fidelity,
                difference_vs_C=fidelity_difference(c.counts,counts) if method != 'C' else None,
                acceptance=acceptance_summary(retained,attempted),
                syndrome_acceptance_by_basis=result.accepted_by_basis,
                attempted_by_basis=result.shots_by_basis, counts=counts,
                overhead=dict(swaps=entry['audit'][routing_method]['swaps'],
                    **{basis:{k:v for k,v in entry['methods'][routing_method]['circuits'][basis].items()
                              if k not in {'qasm3','sha256'}} for basis in BASES})))
    save(directory/'summary.json', rows)
    lines = ['# Audited C versus QMRP', '',
        f"Each method/topology uses {manifest['batches']} independent seed batches × {manifest['shots_per_batch']:,} attempted shots, split equally among XX/YY/ZZ.", '',
        'Backend properties, compiler seed and native circuits are fixed in manifest.json and QPY files. D rows reuse the same joint samples. Confidence intervals cover sampling uncertainty only and are conservative pointwise 95% intervals (Bonferroni-adjusted Clopper–Pearson).', '',
        '| Processor | Method | Fidelity | F − F_C (95% CI) | Retained | SWAPs | Native 2q / depth (ZZ) |',
        '| --- | --- | ---: | --- | ---: | ---: | ---: |']
    for row in rows:
        diff = row['difference_vs_C']
        delta = (f"{diff['difference']:+.5f} [{diff['interval'][0]:+.5f}, {diff['interval'][1]:+.5f}]"
                 if diff and diff['difference'] is not None else ('undefined' if diff else '—'))
        fidelity_text = f"{row['fidelity']:.5f}" if row['fidelity'] is not None else 'undefined'
        overhead = row['overhead']
        lines.append(f"| {row['processor']} | {row['method']} | {fidelity_text} | {delta} | {row['acceptance']['fraction']:.2%} | {overhead['swaps']} | {overhead['ZZ']['two_qubit_gates']} / {overhead['ZZ']['depth']} |")
    (directory/'summary.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('results/bell-movement-audit'))
    parser.add_argument('--batches',type=int,default=8)
    parser.add_argument('--shots-per-batch',type=int,default=24576)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--prepare-only',action='store_true')
    mode.add_argument('--summarize-only', action='store_true',
                      help='Read completed saved batches; never compile or simulate')
    mode.add_argument('--hyperbolic-route-audit', action='store_true',
                      help='Compile frozen old/new hyperbolic routes; no files created')
    parser.add_argument('--sample', action='store_true', help='Also sample the hyperbolic route audit')
    args=parser.parse_args()
    if args.sample and not args.hyperbolic_route_audit:
        parser.error('--sample requires --hyperbolic-route-audit')
    if args.hyperbolic_route_audit:
        if args.batches < 2 or args.shots_per_batch < 3 or args.shots_per_batch % 3:
            parser.error('Use at least two batches and a positive shot budget divisible by three')
        hyperbolic_route_audit(sample=args.sample, batches=args.batches, shots=args.shots_per_batch)
        return
    if args.summarize_only:
        try:
            manifest = json.loads((args.output/'manifest.json').read_text())
            samples = json.loads((args.output/'samples.json').read_text())
            summarize(args.output, manifest, samples)
        except (OSError, ValueError, KeyError) as error:
            parser.error(str(error))
        return
    if args.batches < 2 or args.shots_per_batch < 3 or args.shots_per_batch % 3:
        parser.error('Use at least two batches and a positive shot budget divisible by three')
    args.output.mkdir(parents=True,exist_ok=True)
    path=args.output/'manifest.json'
    manifest=json.loads(path.read_text()) if path.exists() else prepare(args.output,args.batches,args.shots_per_batch)
    if manifest['batches'] != args.batches or manifest['shots_per_batch'] != args.shots_per_batch:
        parser.error('Existing manifest fixes the budget; choose a new output directory for a new experiment')
    if not args.prepare_only:
        summarize(args.output,manifest,run(args.output,manifest))


if __name__ == '__main__':
    main()
