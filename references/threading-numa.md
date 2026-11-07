# Threading and NUMA

## Threading Checks

Inspect:

- race conditions;
- false sharing;
- atomic contention;
- mutex contention;
- barrier count and placement;
- reduction strategy;
- scheduling policy;
- task granularity;
- oversubscription;
- nested parallelism;
- thread affinity;
- per-thread scratch or TLS;
- allocator contention;
- memory bandwidth saturation.

Prefer local accumulation with a final reduction over shared atomics when correctness allows. Confirm that atomics use the weakest correct memory order, not the default by habit.

## Concurrency Ownership

Identify which layer owns parallelism. Avoid multiplying OpenMP, oneTBB, BLAS, MPI progress, codec, and application thread pools. Limit nested libraries or place work in an explicit arena when oversubscription is possible.

For pipelines, bound tokens/in-flight items from both throughput and memory budgets. Parallelizing a stage without bounding its queue can improve a microbenchmark while making peak memory or tail latency unacceptable.

## Scaling Diagnosis

Separate:

- physical cores vs SMT threads;
- serial fraction vs memory bandwidth saturation;
- load imbalance vs synchronization wait;
- compute saturation vs memory saturation;
- per-thread overhead vs useful work.
- useful concurrency vs oversubscription from nested runtimes.

Use strong scaling for fixed total work and weak scaling for fixed work per worker. Report efficiency, not only runtime.

## NUMA Checks

Inspect:

- socket and NUMA-node topology;
- CCD/CCX or tile topology when relevant;
- first-touch initialization;
- remote memory access;
- thread and rank binding;
- interleave vs local allocation;
- whether initialization and compute use the same placement;
- per-socket bandwidth saturation.

Do not recommend `numactl` by itself. Explain how memory placement and thread binding interact, then provide a command.

## False Sharing Pattern

Typical symptoms:

- performance gets worse as threads increase;
- high cache-line invalidation or HITM-style events where available;
- per-thread counters or scratch slots are adjacent;
- replacing shared updates with padded/private data improves scaling.

Fixes:

- privatize updates;
- pad hot per-thread slots to cache-line size;
- change data ownership by block;
- reduce write frequency.

Always remeasure because padding can increase memory footprint.
