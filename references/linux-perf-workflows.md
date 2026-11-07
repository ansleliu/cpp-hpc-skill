# Linux perf Workflows

Use this reference for Linux CPU diagnosis after the performance contract,
artifact identity, representative workload, and correctness baseline are
known. Choose the smallest flow that can answer the current question. Do not
run every profiler by default.

## Contents

- Scope and boundaries
- Question-driven flow selection
- Preparation
- Counting question
- Hotspot question
- Source-line question
- Cache-line question
- Scaling question
- Structured hotspot report
- Interpretation guardrails
- Source note

## Scope and Boundaries

These workflows apply to Linux `perf`. PMU events, privilege requirements,
sampling support, call-graph modes, and `perf c2c` capabilities depend on the
kernel, `perf` build, CPU model, hypervisor, and system policy.

Do not change `kernel.perf_event_paranoid`, `kptr_restrict`, tracing policy, or
system-wide sampling settings automatically. A `perf_event_paranoid` change requires explicit approval from the system owner and must be restored under
the owner's policy. Prefer unprivileged counters or a documented administrator
configuration.

Use `perf list` and `perf help <command>` on the target machine. Treat command
lines below as starting points, not proof that an event exists.

## Question-Driven Flow Selection

| Question | Start with | Escalate when |
| --- | --- | --- |
| Counting question: what broad mechanism changed? | `perf stat` | Aggregate counters cannot localize the change |
| Hotspot question: which functions consume CPU time? | `perf record` and `perf report` | Symbols or source ownership remain unclear |
| Source-line question: which instructions or lines dominate? | `perf annotate`, `objdump`, compiler reports | Samples lack source or generated-code identity |
| Cache-line question: is coherence contention or false sharing present? | `perf c2c` | HITM-style data is unavailable or ownership is ambiguous |
| Scaling question: why did another thread count regress? | Paired profiles at two placements | Work, affinity, frequency, or input identity differs |

Stop when the current evidence discriminates among the competing hypotheses.
Escalating adds overhead and interpretive risk.

## Preparation

1. Record `uname -a`, CPU model, topology, microcode where material, `perf
   --version`, compiler and flags, executable hash, libraries, affinity, NUMA
   policy, workload identity, and repetitions.
2. Build optimized code with usable symbols. Prefer frame pointers when their
   cost is acceptable; otherwise use a supported DWARF call-graph mode and
   validate stack quality.
3. Confirm the process loads the rebuilt executable and shared libraries.
4. Pin or otherwise record placement. Separate physical-core scaling from SMT.
5. Run correctness separately from profiling. Profile a representative region
   long enough to collect useful samples without changing production behavior.
6. Check permissions without mutating them:

```bash
cat /proc/sys/kernel/perf_event_paranoid
perf list
perf stat -- true
```

## Counting Question

Use aggregate counters to classify the next question, not to declare the root
cause from one ratio.

```bash
perf stat -r 5 \
  -e task-clock,context-switches,cpu-migrations,page-faults,cycles,instructions,branches,branch-misses \
  -- ./app args
```

Prefer `scripts/perf_stat.sh` when a portable probe-and-record wrapper is
useful. It tests requested events, preserves unsupported-event diagnostics,
and does not change system settings.

Normalize to useful work: items, cells, nonzeros, bytes, iterations, or
requests. Record multiplexing and `<not supported>`/`<not counted>` output.
Do not infer cache hierarchy behavior from generic `cache-misses` alone.

Escalate to a model-aware event set only after checking `perf list` and the
processor vendor's event documentation. Keep raw event encodings and their
CPU-model scope with the result.

## Hotspot Question

Use sampling when aggregate counters show that on-CPU work matters but do not
identify the owner.

```bash
perf record -g --call-graph dwarf -o perf.data -- ./app args
perf report -i perf.data --stdio --sort comm,dso,symbol
```

Check:

- lost samples, event count, frequency, and runtime;
- unknown symbols, JIT/generated code registration, split debug information;
- stack truncation or implausible call chains;
- shared-library and runtime-dispatch identity;
- whether the selected event measures on-CPU time or another mechanism.

Prefer separate formal runs for timing and profiling. Sampling overhead can
change scheduling, frequency, cache behavior, and lock timing.

## Source-Line Question

Use annotation after a function is hot or when generated instructions must be
verified.

```bash
perf annotate -i perf.data --stdio --symbol hot_symbol
objdump -drwC ./app
addr2line -e ./app -f -C DSO_RELATIVE_ADDRESS
```

For x86-only Intel syntax, use `objdump -drwC -Mintel ./app`. The `-M`
argument is target-specific; do not carry it to Arm, Power, or other targets.

For PIE/ASLR, use the DSO-relative address from `perf`'s recorded DSO mapping or subtract a verified load bias; never pass an unadjusted runtime address to
`addr2line`. Match the DSO and build ID to the sampled mapping. Prefer
`perf annotate` when it can perform that mapping directly.

Cross-check samples with compiler optimization records and assembly. Inspect
dependency chains, load/store addressing, vector width, masking, remainder
paths, conversions, spills, branches, and calls. Sampling skid means the
displayed line may be near the responsible instruction rather than exactly on
it.

Do not apply a source pattern merely because a loop contains an accumulator,
pointer, mutex, or atomic. Route candidate patterns through
`performance-patterns.md` and collect the required counter-evidence.

## Cache-Line Question

Use `perf c2c` only when coherence contention is plausible: scaling degrades,
writers share state, or HITM/coherence evidence is available.

```bash
perf c2c record -- -g -o perf-c2c.data -- ./app args
perf c2c report -i perf-c2c.data --stdio
```

For each hot line, map addresses to allocation, field, owning object, writer,
socket, and source line. Distinguish true sharing from false sharing. Validate
with an ownership/layout candidate such as privatization, blocked ownership,
reduced update frequency, or measured padding.

HITM percentages and report cutoffs are triage aids. Thresholds are calibration seeds, not hard gates. A fixed percentage is not portable across
CPU models, event definitions, workloads, sample counts, or socket topologies.
When `perf c2c` is unavailable, use vendor tools or a controlled layout
experiment and report the lower evidence level.

## Scaling Question

Compare two controlled placements or thread counts using the same binary,
input, warm state, and measurement protocol.

```bash
perf record -g -o perf-t1.data -- taskset -c 0 ./app args
perf record -g -o perf-tn.data -- taskset -c 0-7 ./app args
perf report -i perf-t1.data --stdio --sort dso,symbol
perf report -i perf-tn.data --stdio --sort dso,symbol
```

Also record wall time, CPU time, useful work, frequency, migrations, affinity,
NUMA placement, bandwidth, and synchronization evidence. Compare absolute
sample counts only when collection parameters and runtime exposure make that
valid; otherwise compare normalized shares alongside timing and counter data.

Classify the loss among serial fraction, bandwidth saturation, remote memory,
load imbalance, lock/atomic contention, barriers, false sharing,
oversubscription, or frequency changes. A changed hotspot share alone is not a
causal explanation.

## Structured Hotspot Report

Report a compact evidence chain:

```text
Question and competing hypotheses:
Artifact/workload/placement identity:
Collection command and perf version:
Counter availability, multiplexing, and sample quality:
Top functions with inclusive/self cost:
Top annotated instructions or source lines:
Cache-line owners/accessors when applicable:
Matched pattern cards and counter-evidence:
Proposed experiment and rollback condition:
Correctness, resource, and portability risks:
Reproduction commands and raw artifact paths:
```

Keep raw `perf.data`, text/CSV reports, executable hashes, and symbol files
together. Do not upgrade a static pattern match into a measured diagnosis.

## Interpretation Guardrails

- IPC is microarchitecture- and workload-dependent; no universal IPC cutoff
  proves a dependency chain, front-end issue, or memory bottleneck.
- Event names and semantics vary. Intel model-specific events must not become
  generic x86 or cross-vendor rules.
- Wide SIMD may lower frequency, increase masking or spills, or violate the
  numerical contract. Benchmark the complete path.
- A low cache-miss count does not exclude branch, front-end, port, dependency,
  synchronization, or frequency limits.
- `perf c2c` output identifies suspicious cache lines, not the correct ownership
  redesign.
- Preserve unsupported, permission, lost-sample, and symbol-quality failures as
  evidence. Never silently replace missing counters with assumptions.

## Source Note

The question-driven flow selection and structured hotspot reporting were
informed by the MIT-licensed
[intel/intel-performance-skills](https://github.com/intel/intel-performance-skills),
especially its `linux-perf` skill. This document generalizes the concepts and
adds portability, evidence-level, permission, correctness, and hard-gate
constraints. The upstream repository is an optional reference, not a runtime
dependency.
