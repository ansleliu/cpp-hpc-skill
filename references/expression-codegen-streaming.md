# Expression Evaluation, Code Generation, and Streaming

The word lazy is overloaded. Name the execution contract before optimizing it.

| Model | Work begins | Primary opportunity | Primary risk |
| --- | --- | --- | --- |
| Expression-template lazy evaluation | assignment or explicit evaluation | fuse loops and remove temporaries | aliasing, repeated subexpressions, register pressure |
| Deferred/asynchronous execution | explicit run, submit, or executor call | compose work and overlap queues | lifetime errors and hidden synchronization |
| Lazy loading | first access or cache miss | avoid unused I/O, decode, and residency | page-fault/miss latency and unbounded cache |
| Streaming | bounded tile/window enters a stage | cap memory and overlap I/O/compute | backpressure, ordering, and partial failure |

Do not use these terms interchangeably in a design or benchmark.

## Eigen: Fuse Selectively and Make Aliasing Truthful

Eigen's expression templates delay evaluation and can fuse elementwise expressions, but the library may materialize subexpressions when aliasing or reuse makes that safer or faster.

- Select row-major or column-major storage from the dominant traversal and external-library boundary; count reorder copies.
- Use eval only when a stable materialized value is required, an expensive subexpression would otherwise be repeated, or a measured fusion loses to a temporary.
- Use noalias only after proving destination and inputs do not overlap. It is a semantic assertion, not a generic speed switch.
- Check mapped-memory strides and alignment before expecting packet/SIMD access.
- Inspect allocation, compiler vectorization reports, and generated code for hot fixed and dynamic shapes.
- Benchmark complete expressions: fusion can remove memory traffic but can also increase live ranges, code size, or repeated computation.

## NVIDIA MatX: Separate Expressions, Transforms, and Executors

MatX uses deferred assignment and explicit execution. Transferable strategies:

- build elementwise expression graphs, then execute them with an explicit executor/stream so launch ownership is visible;
- fuse elementwise operations when it removes global-memory round trips without excessive register pressure;
- treat FFT, GEMM, reductions, and other transforms as stateful boundaries that may need temporaries or synchronization;
- isolate executor-specific implementations behind one transform interface;
- cache expensive plans/handles using a key that includes operation, shapes, strides, types, backend, device, and semantic options;
- bound cache memory, define invalidation, and separate first-run/JIT/plan cost from cache-warm throughput;
- keep operands, temporaries, and executor state alive until asynchronous work completes.

An expression that looks fused is not proof of one kernel. Confirm with profiler timelines and kernel counts.

## waLBerla and pystencils: Generate from Semantics

waLBerla plus pystencils demonstrates a build-integrated path from symbolic numerical rules to CPU/GPU kernels:

- keep the discretization or stencil rule as the source of truth and generate architecture-specific implementation;
- make field layout, index order, strides, blocking, vector width, alignment assumptions, non-temporal stores, OpenMP policy, and GPU indexing explicit inputs;
- use AoS when per-site fields are consumed together and SoA/AoSoA-like layouts when lane-wise field access is dominant;
- apply common-subexpression elimination and algebraic simplification with a register-pressure and code-size budget;
- derive communication packing from actual field accesses when possible, then verify halo extent, ordering, and message volume;
- generate CPU and GPU variants behind the same sweep/operator contract instead of scattering backend branches.

Generated code is part of the evidence identity. Record generator and dependency versions, symbolic specification hash, generation flags, emitted source hash, compiler command, and loaded binary. Test numerical equivalence and inspect vectorization/assembly; code generation does not guarantee good code.

## Lazy Loading and Streaming

Use lazy loading when only a subset may be consumed and the miss penalty is acceptable. Use streaming when the full dataset is consumed incrementally or peak residency must be bounded.

- Define chunk/tile identity, ownership, state transitions, eviction, retry, and cancellation.
- Bound queued work, cache capacity, staging buffers, and decoded objects before allocation.
- Prefetch only from a demonstrated access pattern and cap lookahead so it cannot evict the active working set.
- Overlap read, transfer, decode, compute, and write with explicit dependencies and backpressure.
- Materialize once when downstream stages reuse or reorder data enough to amortize storage.
- Fuse stages when each item is consumed once and fusion does not reduce SIMD efficiency, occupancy, or debuggability beyond the measured gain.
- For memory mapping, measure minor/major faults, random-access amplification, readahead behavior, and cold versus warm runs.
- Preserve failure atomicity: do not publish a partially decoded tile or release input storage before asynchronous consumers finish.

Report end-to-end throughput, time to first result, P95/P99 stall, queue depth, resident and peak memory, bytes read/written, cache hit rate, decode cost, and overlap efficiency. A warm-cache throughput number alone does not validate lazy loading.

## Materialize, Fuse, or Stream

- Materialize when a value is reused, reordered, required for alias safety, or cheaper to store than recompute.
- Fuse when operations share one traversal and eliminated traffic exceeds added register/code pressure.
- Stream when bounded residency or producer-consumer overlap is the dominant requirement.
- Lazy-load when demand is sparse or unpredictable and misses can be tolerated or hidden.
- Precompute/tune when setup is reusable and the break-even count is demonstrated.

## Official References

- Eigen lazy evaluation and aliasing: https://eigen.tuxfamily.org/dox/TopicLazyEvaluation.html
- Eigen storage orders: https://eigen.tuxfamily.org/dox/group__TopicStorageOrders.html
- Eigen expression/vectorization flags: https://eigen.tuxfamily.org/dox/group__flags.html
- MatX quick start and deferred execution: https://nvidia.github.io/MatX/quickstart.html
- MatX transform implementation and caches: https://nvidia.github.io/MatX/developer_guide/transforms.html
- pystencils documentation: https://pycodegen.pages.i10git.cs.fau.de/pystencils/
- pystencils memory layouts: https://pycodegen.pages.i10git.cs.fau.de/pystencils/api/symbolic/generated/pystencils.grids.tensor_field.MemoryLayout.html
- pystencils vectorization options: https://pycodegen.pages.i10git.cs.fau.de/pystencils/api/generated/pystencils.codegen.config.VectorizationOptions.html
- waLBerla code-generation tutorial: https://walberla.net/doxygen/tutorial_codegen01.html
- waLBerla field allocation/layout: https://www.walberla.net/doxygen/fieldPage.html
