# Performance Pattern Cards

Use these cards to turn source observations or profiler signals into
falsifiable optimization candidates. They are retrieval aids, not a substitute
for bottleneck classification, correctness analysis, or measurement.

Never apply a pattern from a keyword alone. A loop accumulator, atomic,
mutex, adjacent field, or narrow instruction is a prompt to gather evidence,
not permission to rewrite the code.

## Contents

- Context routing
- Pattern card contract
- Serial dependency chain
- SIMD transition and width
- Alias and alignment contracts
- False sharing
- Shared-update contention
- Lock contention
- Applying a card
- Source note

## Context Routing

Load one route first and open only the relevant thematic references.

| Route | Available evidence | First action | Useful companion references |
| --- | --- | --- | --- |
| `from-source` | Source/build files without representative profile data | Identify plausible mechanisms and missing measurements; do not claim a bottleneck | `cpu-memory.md`, `simd-vectorization.md`, `threading-numa.md` |
| `from-profile` | Counters, samples, traces, scaling, or cache-line reports | Validate artifact/collection quality, then match signals and counter-evidence | `linux-perf-workflows.md`, `profiling-tools.md`, `experiment-design.md` |
| `new-code` | A design or implementation not yet benchmarked | Prevent expensive ownership, layout, allocation, and dispatch mistakes without speculative micro-tuning | `library-strategies.md`, `benchmarking.md`, `numerical-correctness.md` |

For mixed evidence, start at `from-profile` only when the profile matches the
current binary, workload, placement, and relevant execution region. Otherwise
treat it as `from-source` and request or collect a fresh profile.

## Pattern Card Contract

Every card records:

- **Signal:** what makes the pattern worth checking.
- **Evidence required:** observations that support the proposed mechanism.
- **Counter-evidence:** observations that weaken or falsify it.
- **Candidate:** the smallest owning-abstraction change worth testing.
- **Correctness risks:** semantic, concurrency, numerical, ABI, or lifetime
  hazards.
- **Verification:** oracle, generated-code check, controlled benchmark, and
  expected metric movement.

Do not fill missing evidence with generic thresholds. Hardware counters and
ratios are model-aware clues. Fixed cutoffs are calibration seeds, not hard
gates.

## Serial Dependency Chain

**Signal:** A hot recurrence, accumulator, prefix-like update, or horizontal
reduction appears in source or annotated instructions.

**Evidence required:** The loop is compute-relevant; the recurrence is on the
critical path; assembly shows dependent operations or limited independent
chains; trip counts and runtime share justify a change.

**Counter-evidence:** The loop is memory-bandwidth-bound, has tiny trip counts,
is not hot, or exposes enough independent work through surrounding iterations.
Low IPC alone is insufficient because front-end, branch, port, and memory
limits can produce the same symptom.

**Candidate:** Remove unnecessary recurrence, use multiple independent partial
accumulators, restructure the algorithm, or use a tuned reduction primitive.

**Correctness risks:** Reassociation changes floating-point rounding, NaN/Inf
behavior, exception behavior, determinism, and reproducibility. Prefix
semantics may prohibit decomposition.

**Verification:** Check the numerical contract, compiler report and assembly;
benchmark representative sizes; confirm the expected dependency/throughput
metric moves without memory, tail, or frequency regression.

## SIMD Transition and Width

**Signal:** Hot scalar or narrow-vector instructions, mixed legacy SSE/VEX/EVEX
code, transition assists, repeated horizontal operations, masks, or width
conversions appear in the loaded path.

**Evidence required:** The exact binary and dispatch path are verified;
annotation shows relevant instructions in a hot region; CPU-model-supported
events or assembly support the transition/width mechanism.

**Counter-evidence:** Time is dominated by memory, calls, gather/scatter,
remainders, or another library; wider vectors lower frequency or increase
spills/masking; the observed narrow path is cold cleanup code.

**Candidate:** Fix build/dispatch, keep one encoding convention at an ABI
boundary, let the compiler vectorize a restructured loop, or isolate a measured
ISA-specific kernel. Do not upconvert width mechanically.

**Correctness risks:** Wider operations can change reduction order, FP
contraction, exception behavior, tail handling, alignment assumptions, and
downclock behavior. A missing `vzeroupper` diagnosis must match the actual
calling convention and generated instructions.

**Verification:** Inspect optimization records and assembly, probe local event
names with `perf list`, measure end-to-end latency and frequency, and test
tails, NaN/Inf, alignment, and dispatch fallback behavior.

## Alias and Alignment Contracts

**Signal:** Vectorization reports cite possible aliasing or unknown alignment;
the source uses multiple pointer ranges or aligned allocation without conveying
facts to the optimizer.

**Evidence required:** Object lifetime and range analysis prove non-overlap or
alignment for every call; the compiler report or assembly shows the missing
fact blocks useful code generation.

**Counter-evidence:** Buffers may overlap, subviews share backing storage,
alignment is lost through offsets, runtime checks already version the loop, or
the loop is not performance-relevant.

**Candidate:** Encode a proven no-alias/alignment contract at the narrowest API
boundary, change the data model to make ownership explicit, or use safe runtime
loop versioning where supported.

**Correctness risks:** False `restrict` or alignment assertions create undefined
behavior, miscompilation, or faults. Allocation alignment does not imply every
derived pointer has the same alignment.

**Verification:** Add overlap/offset tests, sanitizers where useful, compiler
reports and assembly checks, then benchmark both aligned and unaligned
production cases.

## False Sharing

**Signal:** Scaling degrades as writers increase; independent thread-owned
fields occupy one cache line; `perf c2c` or vendor tooling reports suspicious
coherence traffic.

**Evidence required:** Map the hot line to its allocation, fields, writers,
source locations, sockets, and object lifetime. Confirm concurrent writes and a
coherence mechanism through profile or a controlled layout experiment.

**Counter-evidence:** Writers update the same logical value (true sharing), the
line is cold, the workload is bandwidth-saturated elsewhere, or padding does
not change coherence/scaling under controlled placement.

**Candidate:** Privatize and reduce, assign block ownership, split read-mostly
and write-hot fields, reduce update frequency, or pad only the hot per-worker
state.

**Correctness risks:** Layout changes can affect ABI, serialization, allocator
pressure, memory footprint, cache capacity, and NUMA placement.

**Verification:** Rerun cache-line and scaling measurements with the same
placement; report memory growth and check that ownership semantics remain
correct.

## Shared-Update Contention

**Signal:** A shared atomic counter, statistics structure, reference count, or
global progress field is updated on a hot path; scaling flattens with high
coherence or atomic cost.

**Evidence required:** The update is frequent and contended; profiles locate
the atomic or reduction path; consumers do not require every intermediate value
globally visible.

**Counter-evidence:** Updates are rare, uncontended, required for synchronization
or linearizability, or the final reduction cost dominates any local-update
saving.

**Candidate:** Use per-thread/per-core/per-shard accumulation with a bounded
merge cadence, remove redundant statistics, or weaken memory order only after a
formal synchronization analysis.

**Correctness risks:** Lost updates, stale reads, overflow, changed sampling
semantics, lifetime errors, excessive shard memory, and incorrect memory order.

**Verification:** Test invariants and overflow, run TSan separately when
applicable, measure atomic/coherence cost and scaling, and include merge and
memory overhead in end-to-end results.

## Lock Contention

**Signal:** Lock wait or futex time is hot, convoying appears, wakeups scale
poorly, or a critical section serializes otherwise independent work.

**Evidence required:** Trace wait/hold duration, owner, queueing, read/write mix,
wakeup behavior, and protected-state ownership. Separate lock contention from
work imbalance and oversubscription.

**Counter-evidence:** The lock is uncontended, critical sections are negligible,
the workload is bandwidth-bound, or the proposed lock increases reader/writer
coordination cost.

**Candidate:** Remove work inside the critical section, shard ownership, batch
operations, use immutable snapshots, or select a proven synchronization
primitive that matches the measured contention pattern.

**Correctness risks:** Deadlock, starvation, priority inversion, lost wakeups,
invalidated iterators, changed memory visibility, and unbounded queueing. A
mutex-to-reader-writer-lock replacement is not a generic optimization.

**Verification:** Run concurrency correctness tests and race/deadlock tooling;
measure hold/wait distributions, throughput, P99, fairness, CPU use, and scaling
under the production read/write mix.

## Applying a Card

1. Select the route matching available evidence.
2. Choose one card whose signal and evidence required are both present.
3. Search actively for its counter-evidence and correctness risks.
4. Write a falsifiable hypothesis using `performance-methodology.md`.
5. Change the owning abstraction, not every symptom site.
6. Verify the oracle and generated artifact before paired A/B measurement.
7. Reject and fully revert the candidate when its expected metric does not move
   or any hard gate fails.

## Source Note

The context routes and pattern-card organization were informed by the
MIT-licensed
[intel/intel-performance-skills](https://github.com/intel/intel-performance-skills),
especially its `performance-patterns` skill. The cards here are independently
adapted for cross-vendor C++ HPC work and require counter-evidence, correctness
analysis, portability boundaries, and controlled verification. The upstream
repository is an optional reference, not a runtime dependency.
