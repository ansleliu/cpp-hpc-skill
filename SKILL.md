---
name: cpp-hpc-performance-engineering
description: C++ HPC 性能诊断、优化与基准验证。Use for performance-critical C++ reviews, profiling, memory/cache/NUMA, SIMD, parallelism, CPU/GPU scaling, and numerical regressions; including oneTBB, oneDAL, Intel IPP/oneIPP, OpenMP, MPI, CUDA/HIP/SYCL, and Linux perf. Not for unrelated library setup or general C++ style reviews.
---

# C++ HPC Performance Engineering

## Core Principle

Optimize the whole execution path from evidence: source, build, loaded artifact, data movement, runtime placement, and end-to-end workload. Accept a performance change only when it preserves the required correctness contract, improves an agreed metric, and respects resource and tail-latency guardrails.

No measurement means no speedup claim. If the target workload, hardware, profiler, or benchmark cannot be run, provide a static diagnosis, expected mechanism, uncertainty, and exact reproduction commands. Never invent timings, counters, profiler output, or statistical confidence.

## Action Boundary

- Interpret the current request with the conversation's existing scope, constraints, and authorization. Read-only reviews stay read-only; an authorized implementation continues through relevant validation and delivery.
- Reuse authorization already given for the same scope, including named commit, install, or push actions, within the host's permissions. Confirm only consequential actions not already authorized or material scope changes.
- Infer routine details from the project. Ask when a missing answer could materially change correctness, numerical guarantees, or delivery and cannot be established from available evidence; continue independent work while awaiting it.
- Treat follow-up questions and corrections as steering for active work unless the user pauses, cancels, or replaces it. Apply this skill as task guidance, not as an additional approval process overriding user intent.

## Task Scope

Select the evidence needed for the requested outcome:

| Request | Required work |
| --- | --- |
| Explanation, static diagnosis, or review | Inspect relevant code and evidence; report findings, uncertainty, and checks needed to substantiate performance claims. |
| Documentation or tooling repair | Make the scoped correction and validate the affected artifact or tool behavior. A document-only edit does not require a C++ build or hardware benchmark. |
| Kernel or runtime optimization | Establish correctness and a baseline, implement a falsifiable candidate, and measure it under the same contract. If target execution is unavailable, deliver only the authorized work and identify the unverified gates. |
| Performance acceptance | Complete the agreed representative workload and platform checks, including repeated measurements, artifact identity, numerical correctness, and material resource gates. |

Read only the references that can change the decision. Delegate independent inspection or review when available and useful; keep formal measurements isolated from other work on shared resources. See `references/experiment-design.md`.

## Non-Negotiables

- Treat correctness, determinism, peak memory, tail latency, startup/cold behavior, portability, and build size as possible hard gates, not secondary notes.
- For `-ffast-math`, `-Ofast`, reassociation, mixed precision, approximate math, or changed reduction order, require an approved numerical contract and regression checks. Reuse an existing approval and error budget that cover the candidate; never silently relax the tolerance, determinism, or supported-input requirements.
- Do not use `volatile` as synchronization or introduce unproven aliasing, alignment, lifetime, bounds, atomic, or race assumptions.
- Do not assume wider SIMD, more threads, more ranks, more streams, or higher occupancy is better.
- Do not preserve a faster candidate when it violates any agreed guardrail. Revert only that candidate completely, retain the evidence, and never disturb unrelated user changes.
- Do not trust source changes alone. Verify compiler flags, optimization reports or assembly when relevant, executable/shared-library identity, runtime dispatch, and the artifact actually loaded by the test.
- Do not optimize a microbenchmark while ignoring application-level conversion, packing, launch, transfer, allocation, I/O, or synchronization costs.

## Performance Workflow

Use these steps for measured optimization; apply only relevant steps to the other task types above.

1. **Establish the contract and owner.** Trace the affected data flow, build, and runtime path. Define the primary metric, representative inputs, topology, numerical oracle, portability requirements, hard gates, and minimum worthwhile gain before evaluating candidates. Keep project-specific values in the project's existing instructions or benchmark manifest.
2. **Establish the baseline.** Run correctness checks before optimized timing. Record source/build/artifact and dataset identity, runtime dispatch, placement, and library versions. Separate cold, warm, resident, and end-to-end results; use repetitions and dispersion, with paired A/B when drift can bias the result. Use counters with checked event semantics and collection overhead.
3. **Test a falsifiable candidate.** State the evidence, limiting mechanism, expected change, risks, acceptance threshold, and rollback condition. Change one important mechanism at its owning abstraction; bound allocations and in-flight work, preserve failure behavior, and remove obsolete paths. Prefer removing work and data movement or using a proven kernel before intrinsics and manual tuning. Use `references/performance-methodology.md` for detailed diagnosis and prioritization.
4. **Validate the affected behavior.** Choose unit/integration, sanitizer, and numerical checks by the change's risk; run diagnostic builds separately from timing. Compare against baseline under the same protocol, including material memory, tail, startup, and scaling gates. Failed correctness or resource gates reject the candidate; stale artifacts or unexplained variance leave performance acceptance unproven.
5. **Deliver the evidence.** Report the conclusion, decisive measurements or static findings, checks performed, remaining limits, and reproduction commands or artifact links. Match detail to the request; see `references/performance-methodology.md`. Distinguish static, smoke, comparative, and production evidence.

Complete required checks, then broaden or repeat verification only for new changes, failures, or unresolved concerns. This does not reduce repetitions required by the performance protocol. Test observable tool or runtime behavior; use structural checks for documentation and realistic task trials for instruction behavior, rather than asserting prose or headings.

## Reference Map

Load only what the current task needs:

- `references/experiment-design.md`: evidence levels, paired A/B, hard gates, artifact freshness, candidate rollback.
- `references/performance-methodology.md`: bottleneck taxonomy, hypothesis template, optimization priority, reporting.
- `references/library-strategies.md`: transferable integration patterns from Kokkos, RAJA, oneTBB, oneDAL, Intel IPP, BLIS, FFTW, CUTLASS, AMReX, Google Benchmark, and MPI.
- `references/sparse-matrix-free.md`: CSR and alternative sparse formats, oneMKL, Ginkgo, Kokkos Kernels, TACO, libCEED, MFEM, and matrix-free/partial assembly.
- `references/expression-codegen-streaming.md`: Eigen, NVIDIA MatX, waLBerla/pystencils, expression-template lazy evaluation, deferred execution, lazy loading, and bounded streaming.
- `references/benchmarking.md`: harness design, warm-up, repetitions, percentiles, memory, and end-to-end timing.
- `references/cpu-memory.md`: cache, TLB, layout, locality, streaming, compression, prefetch, allocation, loop transforms.
- `references/simd-vectorization.md`: compiler reports, build/dispatch verification, alias/alignment, reductions, intrinsics.
- `references/threading-numa.md`: concurrency ownership, atomics, false sharing, affinity, NUMA placement.
- `references/openmp.md`: scheduling, reductions, tasks, affinity, allocator and implementation support.
- `references/mpi.md`: decomposition, collectives, persistent/partitioned communication, progress, scaling.
- `references/gpu.md`: tiling, pipelines, fusion, persistent kernels, occupancy, transfers, profiling, autotuning.
- `references/numerical-correctness.md`: floating-point semantics, tolerances, reproducibility, oracle design.
- `references/profiling-tools.md`: tool selection, counters, compiler optimization records, command patterns.
- `references/linux-perf-workflows.md`: question-driven Linux `perf stat`, sampling, annotation, cache-line, and scaling workflows.
- `references/performance-patterns.md`: context-routed source/profile/new-code pattern cards with counter-evidence and verification.

## Helper Scripts

Read `--help` before use and prefer a project-native harness when it measures the real kernel more accurately.

- `scripts/collect_system_info.py`: preferred cross-platform system, affinity, environment, compiler, GPU, and profiler inventory.
- `scripts/collect_system_info.sh`: Linux shell alternative.
- `scripts/run_benchmark.py`: repeated single-command benchmark with optional internal-metric extraction and reproducibility metadata.
- `scripts/run_ab_benchmark.py`: randomized interleaved paired A/B benchmark with bootstrap confidence interval.
- `scripts/compare_benchmarks.py`: compare saved runs with descriptive statistics and bootstrap uncertainty.
- `scripts/perf_stat.sh`: probe supported Linux `perf stat` events, record available counters, and preserve diagnostics.
- `scripts/check_vectorization.sh`: GCC, Clang/clang-cl, Intel, or MSVC vectorization reports.
