# GPU Optimization

Applies to CUDA, HIP, and SYCL unless a project is specific to one stack.

## First Checks

- global-memory coalescing;
- host-device transfer volume;
- page-locked memory;
- unified memory migration;
- warp/wavefront divergence;
- occupancy;
- register pressure and spills;
- shared/local memory use;
- bank conflicts;
- synchronization;
- block or work-group size;
- launch overhead;
- streams or queues;
- asynchronous copy;
- kernel fusion;
- arithmetic intensity;
- tensor or matrix units;
- CPU-GPU overlap.

## Occupancy Is Not the Goal

Do not optimize for occupancy alone. Judge changes with:

- achieved memory bandwidth;
- compute utilization;
- stall reasons;
- register usage;
- shared memory use;
- instruction mix;
- end-to-end execution time.

Lower occupancy can be faster if it improves cache reuse, register reuse, or instruction efficiency.

## Tiling, Pipelines, and Fusion

Map tiles to the hardware and memory hierarchy. Stage data to overlap transfer with computation only when synchronization and extra buffering are cheaper than the hidden latency. Consider epilogue or adjacent-kernel fusion when it removes global-memory round trips, but reject fusion that causes excessive registers, shared memory, code size, or tail latency.

Use persistent kernels when repeated work amortizes launch/prologue cost and a scheduler can balance tiles across SMs. They are not a default replacement for ordinary kernels.

For shape-dependent choices, bounded autotuning can select tile, stage, or launch policy. Key cached tuning results by device architecture, driver/runtime, build/library version, shape, datatype, and semantic mode; retain a deterministic fallback.

## Transfers and Unified Memory

Check end-to-end time. A faster kernel can be irrelevant if transfers dominate. For unified memory, inspect page migration and prefetch behavior. For host staging, consider pinned memory only when transfer size and lifetime justify it.

## Kernel Changes

Keep kernel rewrites focused:

- isolate indexing changes;
- verify bounds and race freedom;
- keep CPU reference or correctness oracle;
- compare numerical output with explicit tolerance;
- record launch parameters and hardware.
- preserve an unfused reference path for correctness testing when numerical semantics or indexing are complex.

## Profiling Tools

Use Nsight Systems for timeline and overlap. Use Nsight Compute for kernel-level memory, occupancy, register, and stall analysis. Use rocprof/rocprofv3 and vendor tools for HIP. Use SYCL implementation tools where available.
