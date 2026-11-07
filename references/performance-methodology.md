# Performance Methodology

## Baseline Checklist

Use for measured performance work, selecting the project-relevant fields. Static reviews and documentation repairs use the task scope in `SKILL.md`.

- Build with `Release` or `RelWithDebInfo`; avoid debug builds for timing.
- Run correctness tests before performance tests.
- Record compiler, compiler version, flags, libraries, CPU/GPU model, memory, OS, kernel, thread/rank counts, affinity, NUMA policy, and input data.
- Use representative workloads. Separate toy, kernel, and production-scale inputs.
- Include warm-up and repeated runs. Report median plus dispersion, not only best time.
- Preserve benchmark artifacts: commands, JSON/CSV output, profiler summaries, and exact commit or diff.
- Preserve executable/shared-library hashes and confirm the runtime loads the rebuilt artifact.
- Separate cold, first-touch, warm, resident, and steady-state scenarios.
- Define hard gates and a minimum worthwhile improvement before testing candidates.

## Bottleneck Taxonomy

Classify the bottleneck before changing code:

- `algorithm-bound`: asymptotic complexity or unnecessary work dominates.
- `compute-bound`: arithmetic throughput, ports, instruction mix, or FMA utilization dominates.
- `memory-bandwidth-bound`: streaming data rate approaches sustainable bandwidth.
- `memory-latency-bound`: pointer chasing, low memory-level parallelism, or cache misses dominate.
- `cache/TLB-bound`: working set, conflict misses, poor locality, or page walks dominate.
- `front-end/instruction-bound`: decode, instruction cache, micro-op cache, or branch target limits dominate.
- `branch-bound`: mispredictions or unpredictable control flow dominate.
- `synchronization-bound`: locks, atomics, barriers, or critical sections dominate.
- `false-sharing-bound`: independent thread updates bounce the same cache line.
- `load-imbalance-bound`: workers finish at different times.
- `NUMA-bound`: remote memory or bad first-touch dominates.
- `communication-bound`: MPI/network latency, bandwidth, collectives, or synchronization dominates.
- `host-device-transfer-bound`: CPU/GPU transfers or migrations dominate.
- `I/O-bound`: storage or file parsing dominates.

## Hypothesis Template

For a candidate experiment, record the following in the project ledger when useful; a small static suggestion can state the hypothesis and required evidence inline:

```text
Hypothesis:
Evidence:
Expected hardware mechanism:
Metric expected to improve:
Correctness risk:
Portability risk:
Experiment:
Success threshold:
Rollback condition:
```

## Optimization Priority

1. Remove work or improve algorithmic complexity.
2. Use or compare against a maintained tuned library.
3. Fix build configuration, runtime dispatch, or stale deployment artifacts.
4. Reduce data movement, lifetime, and improve layout.
5. Improve cache, TLB, and NUMA locality.
6. Improve parallel granularity, concurrency ownership, and load balance.
7. Overlap or reduce pipeline, MPI, or GPU communication.
8. Improve SIMD, ILP, and register reuse.
9. Apply micro-optimizations such as prefetch, intrinsics, and unrolling only after evidence supports them.

Run candidates independently. Set a minimum useful gain, verify all resource/correctness gates, and fully revert rejected candidates rather than retaining noise-sized complexity.

## Reporting

Lead with the answer or acceptance decision, followed by decisive evidence, validation, and material limitations. For reviews, lead with actionable findings and source locations. Use concise paragraphs unless a comparison or sequence is clearer as a table or list; do not fill in irrelevant report sections.

For a measured optimization, retain the reproducible record in project artifacts: source/build and loaded-library identity, hardware and placement, inputs, commands, baseline and candidate observations, dispersion, correctness results, and resource gates. Link the record from the final response. Include enough before/after context to assess the claim without copying the whole record into chat.

For static work, state what the code establishes, what remains a hypothesis, and the target checks needed to resolve it. Missing timing is a limit on the claim, not a reason to invent results or block independent authorized work. Keep experimental data and mock test metrics clearly distinguished from application performance.
