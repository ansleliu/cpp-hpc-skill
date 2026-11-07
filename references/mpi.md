# MPI Guidance

## Decomposition

Evaluate:

- domain decomposition shape;
- surface-to-volume ratio;
- halo width and frequency;
- rank count vs local problem size;
- topology awareness;
- rank placement and process binding;
- load balance and per-rank work.

## Communication

Inspect:

- message count and size distribution;
- small-message latency;
- aggregation opportunities;
- collective communication frequency;
- global synchronization points;
- wait time;
- nonblocking communication correctness;
- persistent communication opportunities;
- computation/communication overlap.

Nonblocking MPI only helps when useful work occurs between start and wait, and the MPI implementation can make progress.

For repeated patterns, evaluate neighborhood collectives, persistent collectives, and partitioned communication. Persistent setup is useful only when communicator, datatype, counts, and operation recur enough to amortize initialization. Partitioned communication is useful only when producers can expose independently ready partitions. Verify implementation support and progress behavior on the target MPI stack.

MPI 5.0 is the current standard, but feature availability still depends on the deployed implementation. Record the MPI library/version and do not infer overlap or GPU-awareness from API shape alone.

## Reporting Requirements

For MPI optimization, report:

- per-rank workload;
- bytes communicated;
- message count;
- wait time or communication fraction;
- imbalance;
- strong or weak scaling efficiency;
- rank/thread/GPU placement;
- network/interconnect assumption when known.

## GPU-Aware MPI

When GPUs are involved, distinguish:

- GPU-aware direct communication;
- host staging;
- pinned host buffers;
- stream synchronization;
- device-to-device topology;
- overlap between kernels, copies, and MPI calls.
- stream-awareness and synchronization semantics of the deployed MPI implementation.
