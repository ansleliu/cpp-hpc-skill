# SIMD and Vectorization

## First Checks

Before adding intrinsics, inspect:

- contiguous memory access;
- aliasing assumptions;
- loop-carried dependencies;
- reductions and reassociation requirements;
- alignment;
- trip count and remainder handling;
- gather/scatter cost;
- masked operations;
- data layout;
- FP contraction and numerical semantics;
- register pressure and spills;
- frequency downclocking for wide vectors.

## Preferred Path

1. Restructure loops and data layout.
2. Express true alias and alignment facts with project-approved mechanisms.
3. Inspect compiler vectorization reports.
4. Use portable SIMD abstractions when they fit the project.
5. Use architecture-specific intrinsics only when reports and benchmarks show the compiler cannot generate adequate code.

## Compiler Reports

Typical flags:

- GCC: `-fopt-info-vec-optimized -fopt-info-vec-missed`
- Clang: `-Rpass=loop-vectorize -Rpass-missed=loop-vectorize -Rpass-analysis=loop-vectorize`
- Intel/ICX: `-qopt-report=5 -qopt-report-phase=vec`
- MSVC: `/Qvec-report:2`

Treat reports as evidence, not proof. Confirm with assembly or profiler data when the result matters. Save structured optimization records when the compiler supports them, and compare records across candidates rather than relying only on console text.

## Build and Dispatch Verification

Verify the optimized path exists and is used:

- inspect target ISA flags and feature macros;
- check generated assembly or compiler optimization records;
- verify runtime CPU-feature/backend dispatch;
- hash the executable and deployed DLL/shared object;
- confirm shared-library search paths do not load a stale or generic build;
- include conversion, alignment-fixup, and dispatch overhead in end-to-end timing.

## Intrinsics Rules

- Keep intrinsics isolated behind small functions or dispatch layers.
- Provide a portable fallback only when the target-platform contract requires one; do not retain parallel implementations for compatibility alone.
- Name ISA assumptions: AVX2, AVX-512, NEON, SVE, etc.
- Verify alignment, tail processing, NaN/Inf behavior, and reduction ordering.
- Measure end-to-end impact, not only the intrinsic kernel.

## Common Causes of Missed Vectorization

- possible pointer aliasing;
- unknown trip count;
- non-contiguous loads;
- hidden function calls in the loop;
- loop-carried dependencies;
- complex control flow;
- reductions without allowed reassociation;
- mixed types causing conversions;
- stores that may overlap loads.
- build configuration omitted the intended ISA or runtime selected a fallback.
