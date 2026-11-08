# RUPTURA-derived finite-PWL baseline

The bundled `ruptura_finite_pwl.hpp` adapts the pressure-space Newton algorithm
from [iRASPA/RUPTURA](https://github.com/iRASPA/RUPTURA), immutable revision
`96ed683f593bf832f2871d86f67272a97e74b3ce`,
[`src/mixture_prediction.cpp`, lines 187–346](https://github.com/iRASPA/RUPTURA/blob/96ed683f593bf832f2871d86f67272a97e74b3ce/src/mixture_prediction.cpp#L187-L346).
The full upstream MIT copyright and permission notice is retained in
`RUPTURA_LICENSE.md`. Local adaptation and integration: Zijia Wang.

The adapter specializes the equations to two positive components and preserves
the upstream Newton elimination, positive-pressure safeguard, residual stopping
criteria and 50-iteration cap. It uses the project's common positive
piecewise-linear curve representation, linear origin rule and finite support
in place of upstream analytic isotherms. Arithmetic uses long double;
finite-support safeguards, score-accuracy validation and a robust scalar
fallback are added. Near-support boundary cases use the common binary128
backend. This is an adapted algorithm, not an unmodified upstream executable
or a bitwise replica.

Accepted calls may cache a pressure pair for warm initialization. Cache identity
is an ordered candidate pair in one immutable curve pool. Invalid or
unconverged Newton calls fall back to the shared scalar solver; both work and
fallback costs are counted. Numerical failures propagate rather than becoming
ranked outputs. Shared ranking and tie handling occur outside this adapter.

For the mathematical contract and evaluation scope, consult the paper included
in `docs/assets/paper.pdf`. Finite tests do not establish global floating-point
containment or unchanged-upstream performance.
