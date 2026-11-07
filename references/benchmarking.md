# Benchmarking

## Controls

Control or record:

- release build type;
- dead-code elimination protection;
- CPU affinity;
- NUMA placement;
- warm-up;
- input initialization;
- cache-hot vs cache-cold scenario;
- turbo, frequency scaling, and thermal throttling;
- background noise;
- allocator behavior;
- thread count;
- rank count;
- GPU clocks and persistence mode when relevant;
- representative data size;
- repeated runs;
- result statistics;
- end-to-end timing.

## Benchmark Types

- Microbenchmark: isolates a small operation. Useful for mechanisms but easy to mislead.
- Kernel benchmark: times a meaningful computational kernel with realistic data.
- Application benchmark: end-to-end timing that validates real impact.
- Strong scaling: fixed total work as resources increase.
- Weak scaling: fixed work per resource as resources increase.

Report which type is being used.

## Statistics

Report median as the default summary. Also report min/max and a robust or conventional dispersion measure. Add P95/P99 only when the sample count and production contract make tails meaningful. Do not claim statistical significance from too few samples. If variance is high, diagnose noise before drawing conclusions.

For A/B work on the same machine, prefer randomized interleaved pairs over two long independent batches. Preserve the pair order and random seed. Report the paired ratio distribution and a bootstrap confidence interval as uncertainty, not as proof that all future workloads improve.

Predeclare outlier handling. Never discard a result only because it weakens the conclusion.

## Dead-Code Elimination

Ensure the compiler cannot remove the measured work. Use observable outputs, checksum validation, benchmark frameworks, or volatile sink patterns only for benchmark harnesses, not production synchronization.

For operations whose useful time is comparable to process startup, dynamic loading, or timer overhead, use an in-process harness. If the application already reports an internal kernel metric, parse and preserve that metric instead of treating process wall time as the kernel time.

## State and Identity

Separate cold start, first touch, cache-warm, resident, and steady-state measurements. Do not warm a cold-path acceptance test or report a cold run as steady state.

Record the hash of the executable and copied shared libraries when stale artifacts are plausible. Confirm that runtime dispatch selects the intended ISA/backend. A valid source diff with the wrong loaded DLL is not a valid experiment.

## Multi-Objective Gates

Performance acceptance may include primary latency/throughput, P95/P99, peak RSS or device memory, allocation/copy budgets, deterministic output, portability, code size, compile time, and startup. A candidate must pass every declared hard gate. Record and fully revert rejected candidates.

## Reproducibility

Every benchmark result should include enough information for another engineer to rerun it:

- build command;
- run command;
- input data;
- environment variables;
- hardware and OS;
- thread/rank/GPU settings;
- raw timing output;
- commit or diff.
