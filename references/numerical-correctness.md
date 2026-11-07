# Numerical Correctness

## Explicitly Report Semantic Changes

Report any change involving:

- reassociation;
- FMA contraction;
- parallel reduction order;
- `fast-math`;
- flush-to-zero;
- denormal handling;
- mixed precision;
- approximate math;
- non-deterministic atomics;
- changed transcendental functions;
- changed iteration order.

## Fast Math Policy

Default to no `fast-math` or `-Ofast`. If enabling it is proposed, require:

- explicit user or project approval;
- documented error budget;
- numerical regression tests;
- NaN/Inf behavior review;
- reproducibility impact review;
- before/after performance data.

## Tolerances

Use a tolerance that matches the domain:

- absolute tolerance for values near zero;
- relative tolerance for scale-dependent values;
- ULP tolerance for low-level floating-point comparisons;
- bitwise equality only when the project requires determinism.

State whether results must be deterministic across runs, thread counts, ranks, GPU models, and compiler versions.

## Reductions

Parallel reductions change order. Check:

- acceptable error accumulation;
- deterministic reduction tree requirements;
- use of compensated summation;
- FMA contraction differences;
- atomics and non-deterministic update order.

## Testing

Keep numerical tests separate from performance timing when possible. Include edge cases for zeros, very large values, denormals if relevant, NaN/Inf behavior, and representative production inputs.

Use byte/hash oracles only when bitwise identity is part of the contract. Otherwise store the input and reference output identity, compare values under the declared tolerance, and also check domain invariants. Run the oracle across relevant thread/rank/device counts because reduction order and scheduling can change results.
