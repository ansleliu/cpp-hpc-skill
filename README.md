# C++ HPC Performance Engineering

English | [简体中文](README.zh-CN.md)

A Codex skill for modern C++ high-performance computing. Its workflow covers defining the performance contract, recording artifact identity, establishing a correctness baseline, locating bottlenecks, testing one falsifiable hypothesis at a time, and reporting reproducible results.

Performance conclusions must account for the target workload and hardware, the binary actually loaded, statistical uncertainty, numerical correctness, and resource constraints. Microbenchmark results alone do not establish production speedup.

## Model Compatibility

The skill is model-independent. It retains existing authorization within the same scope and selects evidence appropriate for static review, documentation or tooling changes, performance optimization, or formal acceptance. Verification scales with risk and expands when changes, failures, or unresolved concerns warrant it. Formal performance protocols still require repeated measurements.

Independent checks can run in parallel or be delegated where useful. Formal benchmarks and profilers need isolation from competing work on shared resources. Reports summarize conclusions, key evidence, and limitations; project artifacts retain the full experiment record. Automated checks cover packaging, references, and tool behavior. See the [Astra trial record](evaluation/astra-2026-09-08.md) for a separate behavioral evaluation and its limitations.

## Capabilities

- **Measurement and experiments:** cold and warm paths, repeated runs, P95/P99, randomized interleaved paired A/B, bootstrap intervals, regression gates, and candidate rollback.
- **CPU and memory hierarchy:** AoS, SoA, AoSoA, alignment, cache lines, TLBs, NUMA, blocking and tiling, prefetching, streaming stores, and working-set management.
- **Vectorization and parallelism:** SIMD, compiler vectorization reports, OpenMP, MPI, thread affinity, false sharing, and load balancing.
- **Library integration:** oneTBB concurrency ownership, oneDAL analytical contracts, Intel IPP primitives, data boundaries, and runtime dispatch verification.
- **GPU and heterogeneous computing:** CUDA, HIP, SYCL, hierarchical tiling, software pipelines, fusion, occupancy, transfers, persistent kernels, and autotuning.
- **Sparse and matrix-free computing:** CSR/CSC/BSR/ELL, amortized format conversion, inspector-executor patterns, partial assembly, and time to solution.
- **Expressions and data pipelines:** expression-template lazy evaluation, deferred and asynchronous execution, lazy loading, bounded streaming, JIT and plan caches, and generated-code identity.
- **Numerical behavior and reproducibility:** error budgets, ULP and relative or absolute error, reduction order, mixed precision, deterministic modes, and numerical regression tests.
- **Linux CPU diagnostics:** question-driven selection of `perf stat`, sampling, source annotation, `perf c2c`, and scaling comparisons, with structured evidence for hotspots.
- **Performance pattern cards:** `from-source`, `from-profile`, and `new-code` routes, with counter-evidence, correctness risks, and validation steps.

## Design References

The skill draws on transferable engineering practices from these projects. Projects do not need to adopt these libraries to use the skill.

| Area | Reference projects | Practices |
| --- | --- | --- |
| Expressions and tensors | Eigen, NVIDIA MatX | Selective fusion, aliasing contracts, explicit executors, asynchronous lifetimes, plan caching |
| Dense and sparse algebra | Intel oneMKL, Ginkgo, Kokkos Kernels | Tuned kernels, inspector-executor patterns, execution and memory spaces, reusable sparse state |
| Sparse tensor compilation | TACO | Separate algebraic expressions, storage formats, and schedules |
| Generated stencils | waLBerla, pystencils | Generate CPU and GPU kernels from numerical semantics; specify layout, vector width, blocking, and communication packing |
| High-order finite elements | libCEED, MFEM | Operator decomposition, partial assembly, matrix-free methods, backend separation |
| Parallel execution and communication | Kokkos, RAJA, MPI | Separate policy from algorithms, hierarchical parallelism, concurrency budgets, persistent communication |
| Tasks, analytics, and domain primitives | oneTBB, oneDAL, Intel IPP | Scheduling ownership, analytical semantics, data representation, domain kernels, runtime ISA dispatch |
| Kernel structure | BLIS, FFTW, CUTLASS, AMReX | Multilevel blocking, packing, plan caching, software pipelining, memory pools |
| Linux CPU diagnostics | intel/intel-performance-skills | Question-driven `perf` workflows, cache-line attribution, context-specific pattern cards |

Load the relevant references as needed:

- [Library and framework strategies](references/library-strategies.md)
- [Sparse, structured, and matrix-free computing](references/sparse-matrix-free.md)
- [Expressions, code generation, and streaming](references/expression-codegen-streaming.md)
- [CPU and memory optimization](references/cpu-memory.md)
- [SIMD and vectorization](references/simd-vectorization.md)
- [GPU optimization](references/gpu.md)
- [Linux perf workflows](references/linux-perf-workflows.md)
- [Performance pattern cards](references/performance-patterns.md)

The MIT-licensed `intel/intel-performance-skills` repository is an optional reference. This skill independently extracts transferable methods and adds cross-vendor, correctness, permission, and evidence requirements. It has no runtime dependency on that repository.

`uxlfoundation/skills` is an optional research reference for oneTBB workload classification and oneDAL semantic validation. Those entries were marked `incubating` when reviewed on 2026-09-02. Check upstream status and official project documentation for specific APIs, devices, and algorithms. This repository is not a runtime dependency either.

## Installation

Clone into your personal Codex skills directory on Windows:

~~~powershell
git clone https://github.com/ansleliu/cpp-hpc-skill.git "$HOME\.codex\skills\cpp-hpc-performance-engineering"
~~~

On Linux or macOS:

~~~bash
git clone \
  https://github.com/ansleliu/cpp-hpc-skill.git \
  ~/.codex/skills/cpp-hpc-performance-engineering
~~~

Restart Codex or start a new task to reload skill metadata.

## Using the Skill

Select `cpp-hpc-performance-engineering` in Codex, or let Codex select it based on the task scope. See [SKILL.md](SKILL.md) for the workflow, scope, and reference index.

## Tools

The repository includes standalone helper scripts:

| Script | Purpose |
| --- | --- |
| **collect_system_info.py** | Collect system, affinity, compiler, GPU, and profiler information |
| **run_benchmark.py** | Repeat a single candidate and record reproducibility metadata |
| **run_ab_benchmark.py** | Run randomized interleaved paired A/B experiments with bootstrap intervals |
| **compare_benchmarks.py** | Compare saved results and estimate statistical uncertainty |
| **perf_stat.sh** | Probe and record available Linux perf stat counters |
| **check_vectorization.sh** | Generate vectorization reports for GCC, Clang, Intel, or MSVC |

The vectorization script prints recommended flags for each compiler family when run without a command. Use `--compiler` when detection cannot identify the compiler. The system information shell entry point tests that Python can start before using it, so an unusable `python3` stub does not block fallback.

The benchmark runner resolves explicit relative executable paths and relative `PATH` entries against `--cwd`. Identity records use the same path. If a lock or permission issue prevents hashing, the runner records `identity_error`, keeps the raw observations, and marks the identity unverified. Launch failures are saved as `launch_error` and return 126 (cannot execute) or 127 (not found). `--allow-failure` continues collecting failure records; check the number of successful samples before comparing results. Speedup comparisons require finite positive samples on both sides. A/B runs with no valid complete pairs return 65 and retain the raw observations.

Executable paths preserve symlinks so a virtual-environment interpreter is invoked through its original path. Output is decoded as UTF-8 with replacement for invalid bytes. An empty regex capture records a metric error. If a configured internal metric is missing, comparison fails; use `--field elapsed_seconds` to explicitly compare process time. Timing options must be finite, and timeouts must be positive.

Shell tools return 74 when they cannot save required reports, unless the compiler or perf already failed, in which case they retain that exit status. `perf_stat.sh` returns 127 if perf is unavailable or 69 if no events can be collected. Neither case runs the target command. The minimal system collector without Python checks write errors and escapes file paths in JSON.

Check arguments before running the tools:

~~~powershell
python scripts/run_benchmark.py --help
python scripts/run_ab_benchmark.py --help
~~~

Prefer a project-native benchmark that measures the actual kernel. These helpers support experiment orchestration and evidence collection.

## Repository Layout

~~~text
.
|-- SKILL.md                  # Trigger, constraints, and workflow
|-- agents/openai.yaml        # Codex UI metadata
|-- references/               # Performance engineering references by topic
|-- scripts/                  # Benchmark, A/B, system, and compiler report tools
|-- evaluation/               # Behavioral trials, scope, and limitations
|-- .gitignore
|-- README.md                 # Default English documentation
|-- README.zh-CN.md           # Simplified Chinese documentation
~~~

## Validation

~~~powershell
$env:PYTHONUTF8 = "1"
python "$HOME\.codex\skills\.system\skill-creator\scripts\quick_validate.py" .
python -m unittest discover -s scripts/tests -p "test_*.py" -v
ruff check scripts
~~~

Validation covers skill metadata, reference reachability, benchmark tool behavior, and Python static checks. Synthetic speedups in test output exercise script logic. Reproduce performance conclusions on the target hardware with representative inputs, and evaluate model behavior using actual tasks.

## Engineering Principles

1. Claim speedup only when supported by measurement.
2. Treat correctness, peak memory, tail latency, and portability as possible acceptance gates.
3. Reduce work and data movement before reaching for intrinsics or custom GPU kernels.
4. Test one key candidate at a time and fully revert candidates that fail acceptance gates.
5. Distinguish static diagnosis, smoke tests, controlled benchmarks, and production acceptance.

See [SKILL.md](SKILL.md) for the full workflow.
