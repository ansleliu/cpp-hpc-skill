# Strategies from High-Performance Libraries

Use these as design patterns, not as mandatory dependencies. Re-check upstream version, platform support, license, ABI, and maintenance status before adoption. Benchmark full integration cost, including layout conversion, packing, planning, transfers, and dispatch.

## Contents

- Proven kernels and integration thresholds
- Cross-library semantics, data, concurrency, and dispatch contracts
- Kokkos, RAJA, and oneTBB execution policy
- oneDAL analytics semantics and Intel IPP domain primitives
- BLIS, FFTW, and CUTLASS kernel structure
- AMReX memory ownership
- Google Benchmark measurement
- MPI repeated communication

## Prefer Proven Kernels Before Hand-Rolling

Before writing intrinsics or custom GPU kernels, evaluate a maintained domain library:

- dense linear algebra: BLIS/OpenBLAS or vendor BLAS; cuBLAS/rocBLAS on GPU;
- FFT: FFTW and platform GPU FFT libraries;
- sparse solvers: Ginkgo, PETSc, Trilinos, or domain-specific libraries;
- performance portability: Kokkos or RAJA when multiple backends are a real requirement;
- task parallelism and pipelines: oneTBB;
- data analytics: oneDAL when its algorithm, mode, and device support match the workload;
- image, signal, and compression primitives: Intel IPP on supported Intel CPUs;
- NVIDIA custom tensor kernels: CUTLASS/CuTe after library GEMM is insufficient.

A library call is not automatically faster. Small shapes, conversion/packing, thread startup, synchronization, and memory ownership can dominate. Benchmark the application boundary.

## Cross-Library Integration Contract

Apply the same boundary contract before selecting any tuned library:

- freeze numerical, analytics, layout, ordering, and error semantics before replacing an implementation;
- treat layout, table representation, ROI, strides, ownership, and memory space as part of the performance interface;
- assign one explicit parallelism owner and one concurrency budget per execution phase after identifying application and library thread pools;
- treat a tuned library as a measured candidate, not proof of an end-to-end speedup;
- include conversion, packing, planning, allocation, transfer, synchronization, and result materialization in the measured boundary;
- verify runtime ISA dispatch, device/backend selection, linked libraries, and the artifact loaded in production.

## Kokkos and RAJA: Separate Policy from Algorithm

Transferable pattern:

- represent execution space, memory space, layout, and execution policy explicitly;
- keep the mathematical kernel independent of backend selection;
- map hierarchical parallelism to teams, threads, and vector lanes;
- use team scratch/local memory to express locality;
- tune policy/layout at a narrow boundary instead of scattering backend branches.

Do not add a portability framework for a single fixed backend without a concrete migration or maintenance benefit.

Official references:

- https://kokkos.org/kokkos-core-wiki/ProgrammingGuide/ProgrammingModel.html
- https://kokkos.org/kokkos-core-wiki/ProgrammingGuide/HierarchicalParallelism.html
- https://raja.readthedocs.io/

## oneTBB: Own Concurrency and Bound Pipelines

Transferable pattern:

- classify the work as independent iteration, reduction, prefix, pipeline, dependency graph, fork/join, or shared-state access before selecting a construct;
- make mutation, ordering, cancellation, exception, and blocking behavior explicit;
- centralize concurrency ownership with an application policy or a scoped oneTBB arena where it actually applies;
- do not assume `task_arena` controls foreign runtimes or every nested library pool;
- cap nested concurrency and account for caller participation to avoid oversubscription;
- choose grainsize from useful work, scheduling overhead, balance, and cache locality instead of a fixed rule;
- use `parallel_pipeline` with a bounded token count so throughput does not create unbounded memory;
- partition by NUMA node only when ownership and first-touch align;
- prefer local accumulation and deterministic merge over fine-grained shared atomics.

Long blocking operations can occupy scheduler workers and invalidate expected progress. A concurrent container makes its documented operations safe; it does not make a multi-step compound transaction atomic.

Official references:

- https://uxlfoundation.github.io/oneTBB/main/specification/source/task_scheduler/task_arena/task_arena_cls.html
- https://uxlfoundation.github.io/oneTBB/main/specification/source/algorithms/functions/parallel_pipeline_func.html

## oneDAL: Preserve Analytics Semantics

Treat acceleration as a change of execution mechanism, not a change of the analytics contract:

- freeze preprocessing, feature/label orientation, train/test split, parameters, random seeds, requested outputs, metrics, and comparison tolerances;
- make row/column meaning, data type, dense or sparse representation, table ownership, and conversion lifetime explicit;
- choose batch, online, or distributed execution from data residency, scale, launch topology, and algorithm semantics, not from an assumption that more distribution is faster;
- re-check the current support matrix for the exact algorithm, method, parameters, interface, mode, target device, and deployed release;
- identify whether the application, oneTBB, oneDAL, or another runtime owns parallelism in each phase and enforce one concurrency budget;
- separate ingestion, table conversion, setup, training, inference, synchronization, and output extraction in measurements;
- compare against a reference using exact, tolerance-based, invariant-based, or metric-based checks chosen before timing.

Do not infer GPU support or equivalent numerical behavior from a common API shape. Report unsupported or unverified combinations rather than silently changing method, mode, precision, or device.

Official references:

- https://uxlfoundation.github.io/oneDAL/
- https://uxlfoundation.github.io/oneDAL/onedal/gpu_support.html
- https://uxlfoundation.github.io/oneDAL/system-requirements.html

## Intel IPP: Measure Domain Primitives End to End

Intel Integrated Performance Primitives (Intel IPP) is the official product name; `oneIPP` is only a discovery alias. Transferable pattern:

- evaluate maintained image, signal, transform, statistics, and compression primitives before committing to custom SIMD on supported Intel CPUs;
- freeze data type, ROI, stride, border, overlap, in-place behavior, scaling, rounding, saturation, and error semantics;
- separate specification, state, plan, and scratch initialization from steady-state calls, then report the reuse needed to amortize setup;
- Intel IPP internal threading is deprecated; partition externally only when tiles or chunks preserve borders, halos, state independence, and output ownership;
- verify runtime ISA dispatch, linkage model, deployed library identity, and any architecture fallback;
- measure repacking, alignment fixups, copies, state allocation, and pipeline integration rather than timing only the primitive.

Do not present Intel IPP as a GPU or cross-vendor portability layer. Reject it when conversion cost, unsupported semantics, small problem size, or deployment constraints erase the measured benefit.

Official reference:

- https://www.intel.com/content/www/us/en/developer/tools/oneapi/ipp.html

## BLIS: Pack, Block, and Isolate the Microkernel

BLIS demonstrates a durable CPU design:

- pack data into layouts suited to the microkernel when reuse amortizes packing;
- block at several memory-hierarchy levels;
- isolate architecture-specific microkernels behind stable higher-level control;
- distribute parallelism across suitable dimensions rather than only the outermost loop;
- specialize small/skinny problems because the best strategy changes with shape.

Apply the pattern only after counting packing bytes and checking whether the operation is reused enough to amortize them.

Official reference: https://github.com/flame/blis

## FFTW: Measure Plans and Cache Tuning Safely

FFTW's planner/wisdom pattern is useful beyond FFTs:

- search a bounded configuration space on representative shapes;
- keep planning outside the timed production path;
- cache the selected plan with a key that includes hardware, build, library version, shape, precision, and semantic mode;
- invalidate or ignore stale tuning records when the environment changes;
- keep a deterministic fallback and report whether tuning was reused or regenerated.

Official reference: https://www.fftw.org/doc/Wisdom.html

## CUTLASS: Hierarchical Tiling, Software Pipelines, and Fusion

CUTLASS illustrates modern GPU kernel structure:

- tile work at grid/thread-block, warp, instruction, shared-memory, and register levels;
- double-buffer or stage data to overlap transfer and computation;
- use specialized producer/consumer roles only when synchronization and register costs are justified;
- fuse epilogues or adjacent elementwise work to eliminate global-memory round trips;
- use persistent kernels only when repeated tiles amortize launch/prologue costs and scheduling remains balanced;
- autotune tile and pipeline choices over a bounded, reproducible search space.

Reject fusion or persistent designs that increase register/shared-memory pressure, reduce occupancy below the useful level, or worsen end-to-end tails.

Official references:

- https://docs.nvidia.com/cutlass/latest/media/docs/cpp/efficient_gemm.html
- https://docs.nvidia.com/cutlass/latest/media/docs/cpp/cutlass_3x_design.html

## AMReX: Pools, Lifetime, and GPU Saturation

AMReX demonstrates:

- arenas/pools to amortize expensive allocation and control fragmentation;
- distinct device, managed, and pinned memory ownership;
- explicit attention to one-rank-per-GPU placement and work size large enough to saturate the device;
- inlining small device functions when call overhead and register allocation justify it.

Pool capacity is retained memory, not free memory. Include it in admission, peak-memory reporting, and teardown expectations.

Official reference: https://amrex-codes.github.io/amrex/docs_html/GPU.html

## Google Benchmark: Measure Kernels In Process

Use an in-process harness when process launch is not part of the contract:

- keep setup outside the timed loop or pause timing explicitly;
- use observable outputs plus `DoNotOptimize`/`ClobberMemory` correctly;
- configure warm-up and repetitions;
- emit JSON/CSV and custom counters such as bytes/s, items/s, or allocations;
- register a memory manager when allocation behavior matters.

Official reference: https://google.github.io/benchmark/user_guide.html

## MPI 5.0: Optimize Repeated Communication Patterns

Current MPI standard work includes the MPI 5.0 ABI, while persistent collectives and partitioned communication originated in MPI 4.x. Transferable strategies:

- use neighborhood collectives for stable topology-shaped exchange;
- use persistent collectives when communicator, counts, datatypes, and operation recur enough to amortize setup;
- use partitioned communication when producers can expose independently ready partitions;
- verify progress semantics and actual overlap instead of assuming nonblocking calls overlap;
- report message count, bytes, waits, imbalance, and scaling efficiency.

Official reference: https://www.mpi-forum.org/docs/
