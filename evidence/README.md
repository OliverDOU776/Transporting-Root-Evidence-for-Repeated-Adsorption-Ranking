# Published result summaries

These compact tables support the project page and README. They contain curated publication-level reductions, not execution logs.

- `published_results.csv`: all measured prefixes1,8,16,32,64 for Transport versus LeanCap and Incumbent in the original mechanism study, and versus WarmOnDemand in the separate near/far and operating-range studies. All relation/regime/k cells are retained, including losses.
- `published_results.json`:64-query rows, exact representative lifecycle times, source-file SHA-256 hashes, and numerical-kernel source hashes.

A ratio below1 favors Transport. The reported ratio is the median of three **paired within-block ratios**. Its minimum and maximum are observed technical-block ranges, not confidence intervals. Studies use separate clocks. Setup, full acquisition where applicable, output conversion and teardown are charged. Common input JSON loading, immutable pool preparation, binary compilation/loading and reference checks are excluded, as in the manuscript.

The CRAFTED relation contains16,010 CO₂/N₂ **configuration pairs** at298 K, not16,010 independent materials. Original NIST has353 CO₂/CH₄ curve pairs; the operating-range NIST relation has291 CO₂/N₂ pairs.

Recorded timings are descriptive host measurements, not performance guarantees. The operating grid and acquisition choices are specified workloads, not observed user sessions. Finite-support model ranking and finite numerical checks do not establish physical IAST accuracy or all-input floating-point soundness.
