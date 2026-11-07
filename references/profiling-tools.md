# Profiling Tools

For Linux CPU work, use `linux-perf-workflows.md` when the task needs an
end-to-end decision between counting, sampling, source annotation, cache-line
contention, or scaling comparison. Keep this file for cross-platform tool
selection and counter interpretation.

## Tool Selection

- Linux `perf`: CPU counters, cycles, instructions, cache/TLB, branches, context switches.
- Intel VTune: CPU hotspots, threading, memory access, vectorization, microarchitecture.
- LIKWID: topology, pinning, and performance groups on supported systems.
- PAPI: portable hardware counter access in benchmark harnesses.
- Compiler vectorization reports: missed and successful vectorization explanations.
- Compiler optimization records: serialized inlining/vectorization/loop remarks that can be diffed between builds.
- Nsight Systems: GPU/CPU timeline, transfers, synchronization, overlap.
- Nsight Compute: CUDA kernel memory, occupancy, registers, stalls, instruction mix.
- rocprof/rocprofv3: HIP/ROCm profiling.
- MPI tools: rank communication, wait time, collectives, imbalance.

## CPU Command Patterns

Examples to adapt, not blindly paste:

```bash
perf stat -d -r 10 -- ./app args
perf record -g -- ./app args
perf report
```

Use project scripts when available. Record permissions or unavailable events instead of hiding them.

## Vectorization Report Flags

```bash
# GCC
g++ -O3 -fopt-info-vec-optimized -fopt-info-vec-missed ...

# Clang
clang++ -O3 -Rpass=loop-vectorize -Rpass-missed=loop-vectorize -Rpass-analysis=loop-vectorize ...
```

## GPU Command Patterns

```bash
nsys profile --stats=true ./app args
ncu --set full ./app args
rocprof --stats ./app args
```

Tool availability and syntax vary by installation. Prefer existing project documentation or CI commands.

## Counter Interpretation

Hardware counters are clues, not absolute truth. Validate counter availability, multiplexing, privilege restrictions, skid, sampling overhead, and whether the measured region matches the target workload.

Prefer model-aware events and normalize counters to useful work, bytes, instructions, or elapsed time. Generic `cache-misses` is not a complete cache diagnosis. Preserve unsupported-event and permission diagnostics instead of silently dropping them.
