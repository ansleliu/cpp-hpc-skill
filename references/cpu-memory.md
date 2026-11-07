# CPU and Memory Optimization

## Data Layout

Choose layout from access patterns, not preference:

- `AoS`: useful when most fields of each object are consumed together.
- `SoA`: useful for vectorization and streaming one or a few fields.
- `AoSoA`: useful when vector-width chunks improve SIMD while preserving locality for small object groups.

Check object size, padding, alignment, field order, and whether hot and cold fields should be split. Do not assume `alignas` alone makes dynamically allocated arrays satisfy a complete layout contract.

## Locality and Working Set

Evaluate:

- cache line utilization and wasted bytes;
- spatial and temporal locality;
- row-major vs column-major traversal;
- stride length and prefetcher friendliness;
- working set size per loop nest;
- cache set conflicts;
- TLB pressure and page size;
- allocator behavior and memory pool effects.

Loop transforms to consider:

- interchange to make the innermost loop contiguous;
- fusion when it improves reuse without increasing register pressure too much;
- fission when it reduces working set or improves vectorization;
- tiling/blocking for cache, TLB, or NUMA locality;
- register blocking and multiple accumulators for ILP.

## Cache Lines and False Sharing

For shared data touched by multiple threads:

- identify which thread writes which address range;
- check if independent counters or scratch values share a cache line;
- pad or privatize hot per-thread data only when evidence points to false sharing;
- measure before and after because padding can increase footprint and hurt locality.

## Prefetch and Non-Temporal Stores

Use hardware prefetch friendliness first: contiguous, predictable access and simpler control flow. Manual prefetch is a last resort and should be benchmarked carefully.

Use non-temporal stores only when data is streamed, not read soon, and the store volume is large enough to matter. Validate on target hardware.

## Streaming, Compression, and Lifetime

Reducing bytes moved can outweigh added computation. Compression, compact encodings, tiling, or recomputation may beat raw-memory traversal when memory bandwidth, I/O, cache capacity, or peak memory is limiting. Measure decode/encode cost, cold and warm paths, cache policy, peak memory, and end-to-end throughput; do not assume compressed or uncompressed is universally faster.

Prefer bounded segment/window pipelines and materialize each destination once. Treat retained arenas, caches, staging buffers, and in-flight work as owned memory with explicit admission and lifetime. Admission must occur before scalable allocation and failure must not partially publish reservations.

## Branches and Front-End

Check whether a branch is actually expensive before removing it. Branchless code can increase instruction count, register pressure, or memory traffic. Prefer data partitioning, table restructuring, or hoisting invariants when it reduces work clearly.

## Red Flags

- Adding `restrict` or noalias annotations without proving non-aliasing.
- Assuming all hot loops are compute-bound.
- Optimizing cache for tiny inputs while production inputs are bandwidth-bound.
- Using single-thread speedups to imply multi-thread scaling.
- Counting pooled or cached memory as free merely because it is reusable.
- Fully materializing intermediates that downstream stages consume only by tile/window.
