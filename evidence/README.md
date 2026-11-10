# Published result summaries

These compact tables support the project page and README. They contain curated publication-level reductions, not execution logs.

- `published_results.csv`: all measured prefixes 1, 8, 16, 32, 64 for Transport versus LeanCap and Incumbent in the original cold-pool mechanism study, and versus WarmOnDemand in the separate near/far continuation and operating-range studies. All relation/regime/k cells are retained, including losses.
- `published_results.json`: 64-query rows, exact representative lifecycle times, source-file SHA-256 hashes, and numerical-kernel source hashes.

A ratio below 1 favors Transport. The reported ratio is the median of three **paired within-block ratios**. Its minimum and maximum are observed technical-block ranges, not confidence intervals. Studies use separate clocks. Setup, full acquisition where applicable, output conversion and teardown are charged. Common input JSON loading, immutable pool preparation, binary compilation/loading and reference checks are excluded, as in the manuscript.

The 64-query Transport/LeanCap rows of the mechanism study are the ratios plotted in Fig. 3a of the paper. The WarmOnDemand and operating-range rows, including their five-horizon faster/mixed/slower sequences, are the Transport entries of Table IV. The paper's headline ranges against LeanCap (0.46×–0.63× on CRAFTED) and Incumbent (0.50×–0.74×) are ratios of the median paid times in Table I, so they can differ slightly from the medians of paired ratios listed here.

The CRAFTED relation contains 16,010 CO₂/N₂ **configuration pairs** (290–310 K), not 16,010 independent materials. NIST-N₂ (`nist_n2`) has 353 CO₂/N₂ pairs (293–303 K) and is used in the mechanism study and the operating-range sweep. NIST-CH₄ (`nist_ch4`) has 373 CO₂/CH₄ pairs (293–303 K) and is used in the WarmOnDemand continuation study.

Recorded timings are descriptive host measurements, not performance guarantees. The operating grid and acquisition choices are specified workloads, not observed user sessions. Finite-support model ranking and finite numerical checks do not establish physical IAST accuracy or all-input floating-point soundness.
