# Performance Experiment Design

## Evidence Levels

Label conclusions by the strongest evidence actually obtained:

- `E0 Static`: source/build inspection and a falsifiable hypothesis; no performance claim.
- `E1 Smoke`: one or a few runs proving the harness works; unsuitable for acceptance.
- `E2 Controlled`: repeated runs on fixed hardware/workload with recorded environment and dispersion.
- `E3 Comparative`: controlled, interleaved or same-process A/B with frozen correctness oracle, resource gates, raw results, and artifact identity.
- `E4 Production`: representative corpus, target platforms/topology, tail and failure behavior, end-to-end acceptance gates, and enough repetition to cover operational variance.

Do not describe `E1` or `E2` evidence as production validation.

## Freeze the Contract Before Optimizing

Record:

- primary metric and minimum worthwhile improvement;
- correctness oracle or tolerance;
- peak-memory, allocation, P95/P99, startup, portability, and build-size guardrails;
- representative inputs, distributions, thread/rank/device matrix, and cold/warm state;
- build command, compiler, flags, artifact hash, dependent-library versions, and dataset hash;
- stop and rollback conditions.

This prevents choosing acceptance criteria after seeing a result.

## Candidate Protocol

For each candidate:

1. Start from the accepted baseline.
2. Change one important mechanism.
3. Rebuild and verify the benchmark loads the current artifact.
4. Run the frozen correctness matrix before formal timing.
5. Run the same benchmark protocol and collect resource gates.
6. Accept only if the primary threshold and every hard gate pass.
7. Otherwise revert only that candidate completely, preserve unrelated work, and retain the negative result.

Do not stack candidates that individually produce noise-sized gains. A faster candidate may still fail because of peak memory, P99, determinism, portability, or maintenance cost.

## Measurement Isolation

Do not run formal benchmarks or profilers concurrently on shared CPU cores, caches, memory channels, GPUs, storage, or networks.
Static inspection, source reading, compilation, and independent correctness checks may run concurrently when they do not contend with a measured run.
Record unavoidable co-tenancy and downgrade the evidence level when isolation cannot be established.

## Paired and Interleaved A/B

Independent baseline and candidate batches are vulnerable to temperature, frequency, storage cache, background work, and machine drift. When both binaries can run on one machine:

- warm both according to the target state;
- run A and B once per pair;
- randomize which runs first in each pair using a recorded seed;
- compute the ratio per successful pair;
- report the median paired ratio and a bootstrap confidence interval;
- retain raw order, timing, output, and failure data.

Use same-process A/B when process startup, dynamic loading, allocator warm-up, or shared cache state would dominate the kernel. For sub-millisecond kernels, prefer an in-process harness.

## Correctness Oracle

Choose the strongest valid oracle:

- exact byte or hash identity when the contract is bitwise deterministic;
- value comparisons with absolute, relative, or ULP tolerances for floating-point changes;
- domain invariants, topology, ordering, counts, and conservation laws;
- a trusted independent implementation or legacy implementation when available.

Exercise relevant thread counts, ranks, devices, input shapes, tails/remainders, empty inputs, and failure paths. Hash the tested binary or loaded shared library to detect stale deployment copies.

## Measurement Matrix

Collect only dimensions relevant to the contract, but consider:

| Dimension | Typical evidence |
| --- | --- |
| Central tendency | median latency, throughput |
| Tail | P95/P99/max when operationally meaningful |
| Noise | standard deviation, MAD, coefficient of variation |
| Resources | peak RSS, device memory, allocations, temporary bytes |
| State | cold start, first touch, warm cache, steady state |
| Scaling | 1/N threads, ranks, GPUs; strong/weak efficiency |
| Correctness | oracle result for every tested configuration |
| Identity | commit/diff, binary hash, build and runtime configuration |

Do not delete outliers merely because they weaken the conclusion. Explain an exclusion rule before measurement or report both raw and filtered results with the rule.

## Artifact Freshness

Before trusting a result:

- confirm the source timestamp is older than the built object and linked artifact;
- hash the executable and copied DLL/shared object used by the test;
- inspect runtime module search paths and dispatch logs where possible;
- ensure Release and sanitizer binaries are not mixed;
- confirm the target ISA/backend is compiled and selected;
- preserve command output showing the exact loaded implementation when the library provides it.

Build and deployment configuration can dominate source-level optimization. A generic fallback or stale DLL invalidates the experiment.
