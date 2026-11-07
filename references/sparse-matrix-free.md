# Sparse, Structured, and Matrix-Free Compute

Choose the representation from the operator, sparsity pattern, reuse, and target hardware. Include conversion, setup, preconditioning, and convergence in time-to-solution; a faster SpMV is not useful if format conversion or extra solver iterations dominate.

## Contents

- CSR and format selection
- oneMKL inspector-executor and threading
- Ginkgo executors and CSR strategy
- Kokkos Kernels sparse state
- TACO format/schedule separation
- libCEED and MFEM assembly levels
- Experiment checklist and official references

## CSR as a Baseline, Not a Default Answer

CSR stores row offsets, column indices, and values in separate arrays. Before timing, define and validate:

- row offsets are monotone, have length rows + 1, start at zero, and end at nnz;
- column indices are in range; state whether they are sorted and duplicates are merged;
- index width is large enough for rows and nnz without paying for 64-bit indices unnecessarily;
- structure and values have explicit ownership, executor/memory space, and mutation rules;
- conversion, sorting, duplicate merging, diagonal extraction, and upload are setup costs, not invisible work.

SpMV is usually constrained by value/index traffic, indirect vector reads, and row imbalance. Report bytes and time per nonzero, row-length distribution, useful bandwidth, cache behavior of the input vector, and load balance. Partition by nonzeros when row lengths are skewed, but account for split-row reductions, synchronization, and deterministic ordering.

Do not force every pattern into CSR:

- use CSC when column traversal or transpose operations dominate;
- consider BSR for repeated dense blocks and ELL/SELL-like formats for sufficiently regular row lengths;
- use COO for ingestion or assembly when append/sort is more important than repeated execution;
- keep CSR when conversion is not amortized or the pattern is irregular enough that padding wastes more than it saves.

Treat format selection as a bounded experiment over representative matrices. Include index conversion, padding, extra storage, preprocessing, and cold/warm reuse.

## oneMKL: Amortize Analysis and Own Threading

Transferable strategies from Intel oneMKL:

- prefer BLAS/Sparse BLAS and batch APIs before hand-written kernels when shapes cross the library's useful-size threshold;
- use inspector-executor sparse APIs when a sparsity pattern is reused: analyze and optimize once, execute many times;
- separate symbolic/structure work from numeric/value updates and invalidate analysis when the structure changes;
- match LP64/ILP64, scalar type, storage order, leading dimensions, and ABI at the integration boundary;
- set one application-level concurrency policy so MPI ranks, OpenMP regions, oneTBB, and oneMKL do not oversubscribe the node;
- benchmark direct-call or batched paths for small problems, including dispatch and packing overhead.

## Ginkgo: Separate Linear Algebra from Placement

Ginkgo's LinOp and Executor model suggests:

- expose apply-style operator semantics independently of matrix, solver, or preconditioner implementation;
- make data placement and execution location explicit and keep repeated operations on the same executor;
- choose CSR strategy from matrix shape and target, rather than embedding one row-to-thread mapping in the algorithm;
- preserve sorted-column and duplicate invariants for the operations that require them;
- reuse factories, generated solvers/preconditioners, workspaces, and sparsity metadata when their inputs remain valid;
- apply mixed precision only with an explicit convergence/error contract and include conversions plus extra iterations in the result.

Profile host-device cloning, synchronization, logging, and setup separately from steady-state applies.

## Kokkos Kernels: Keep Policy and Sparse State Explicit

Kokkos Kernels extends the Kokkos execution/memory-space model with dense, batched, sparse, and graph kernels. Reuse these patterns:

- represent CSR/BSR storage with memory spaces accessible to the selected execution space;
- pass an execution-space instance when stream or queue ownership matters;
- keep algorithm selection and reusable temporary/persistent state in a narrow kernel handle;
- split symbolic and numeric phases for repeated SpGEMM, triangular solve, or factorization structures;
- sort/merge sparse input only when required, and amortize that work;
- allow a maintained vendor backend when it wins, while preserving one observable contract.

Fence only where dependencies or measurement require completion. Hidden global fences can erase overlap.

## TACO: Separate Algebra, Format, and Schedule

TACO demonstrates that sparse tensor performance depends on three independent choices:

1. the tensor algebra expression;
2. per-dimension storage formats and their ordering/uniqueness properties;
3. a schedule controlling loop order, splitting, fusion, workspaces, parallelism, vectorization, and target.

Use this separation in hand-written systems too. Do not bake CSR traversal into the mathematical operator. Make format capabilities and schedule explicit, compare asymptotic work before constant-factor tuning, and materialize a workspace when it removes repeated searches or changes complexity. Charge reformatting, generated-code compilation, and tuning to the reuse window that amortizes them.

## libCEED and MFEM: Compare Assembly Levels

The project name is libCEED, not ibCEED. libCEED and MFEM show why a global sparse matrix can be the wrong representation for high-order finite elements:

- full assembly stores the global sparse operator;
- element assembly stores dense element operators;
- partial assembly stores quadrature-point data and applies basis/restriction actions on demand;
- matrix-free execution recomputes more of the operator action without substantial matrix storage.

Model the operator as factored restriction, basis, quadrature action, transpose basis, and transpose restriction. Keep the physics-facing quadrature function separate from backend specialization. Block or interlace elements when that improves SIMD or GPU mapping, and select backends at runtime behind one operator contract.

Judge assembly level by setup cost, apply cost, bytes moved, peak memory, polynomial order, number of repeated applies, preconditioner availability, iteration count, and total solve time. Matrix-free kernels can reduce memory traffic but make some assembled-matrix preconditioners unavailable; a kernel-only comparison is incomplete. Record backend determinism because optimized reduction paths may change reproducibility.

## Experiment Checklist

- Freeze matrix/tensor identity, dimensions, nnz, row distribution, block structure, ordering, and value/index types.
- Separate import/assembly, conversion, analysis, upload, first apply, steady-state apply, and complete solve.
- Compare formats on the same executor and include peak host/device memory.
- Verify sparse invariants and numerical residuals after every conversion.
- Sweep representative structures, not only one friendly matrix.
- Report break-even reuse count for setup, conversion, JIT, or tuning.

## Official References

- Intel oneMKL inspector-executor Sparse BLAS: https://www.intel.com/content/www/us/en/docs/onemkl/developer-reference-c/2024-0/inspector-executor-sparse-blas-routines.html
- Intel oneMKL BLAS and Sparse BLAS: https://www.intel.com/content/www/us/en/docs/onemkl/developer-reference-c/2024-1/blas-and-sparse-blas-routines.html
- Intel oneMKL threading: https://www.intel.com/content/www/us/en/docs/onemkl/developer-guide-linux/2026-0/working-with-openmp-threads.html
- Ginkgo Executors: https://ginkgo-project.github.io/ginkgo-generated-documentation/doc/develop/group__Executor.html
- Ginkgo CSR: https://ginkgo-project.github.io/ginkgo-generated-documentation/doc/develop/classgko_1_1matrix_1_1Csr.html
- Kokkos Kernels sparse API: https://kokkos.org/kokkos-kernels/docs/API/sparse-index.html
- Kokkos Kernels handle: https://kokkos.org/kokkos-kernels/docs/API/sparse/kokkoskernelshandle.html
- TACO documentation: https://tensor-compiler.org/docs
- TACO formats: https://tensor-compiler.org/docs/tensors.html
- libCEED interface concepts: https://libceed.org/en/latest/libCEEDapi/
- MFEM assembly levels: https://mfem.org/howto/assembly_levels/
