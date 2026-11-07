# OpenMP Guidance

## Scheduling

- `static`: best for uniform work and low overhead.
- `dynamic`: useful for unpredictable work but adds scheduling overhead.
- `guided`: useful when early chunks are large and tail imbalance matters.

Justify schedule changes with workload variability or measurements.

## Reductions and Atomics

Prefer `reduction` clauses or per-thread scratch over shared atomics. If atomics are required, state the memory ordering and contention risk. Validate floating-point reduction tolerance because parallel order can change results.

## Affinity and Places

Record and, when needed, control:

- `OMP_NUM_THREADS`
- `OMP_PROC_BIND`
- `OMP_PLACES`
- runtime-specific affinity variables
- NUMA placement command

Thread binding without matching memory placement can make NUMA behavior worse.

Check the actual compiler/runtime support level before using recent OpenMP features. The OpenMP 6.0 specification is newer than many deployed compilers and runtimes; unsupported directives or allocator/affinity clauses must not silently become a portability assumption.

## Tasks

Use OpenMP tasks only when work units are large enough and dependencies are clear. Check task creation overhead, dependency graph size, work stealing, and nested parallelism.

## Common Problems

- hidden barriers at the end of worksharing constructs;
- nested parallel regions causing oversubscription;
- small loop bodies dominated by runtime overhead;
- shared allocators or containers in parallel regions;
- false sharing in arrays of structs or per-thread result arrays;
- using `collapse` without understanding locality and scheduling impact.
- nesting OpenMP over an internally threaded BLAS/oneTBB/library call without a concurrency budget.
