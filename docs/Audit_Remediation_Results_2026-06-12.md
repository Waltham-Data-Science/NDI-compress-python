# NDI-compress-python Audit Remediation — Results (2026-06-12)

> **Context for a reviewer / next agent.** One of **9 coordinated PRs** in the 2026-06 NDI
> ecosystem audit; **none are merged.** This repo's PR: **Waltham-Data-Science/NDI-compress-python#2**.
> Done here: subprocess timeout + LICENSE. **Deferred:** codec provenance/checksums + a
> cross-language round-trip test (needs the codec source + a paired MATLAB run) — see below.

Branch `audit/ndi-compress-python-2026-06`, off `origin/main`.

## Findings addressed (audit §6.2-7, §6.2-8)

| # | Status | Summary |
|---|--------|---------|
| 6.2-7 (subprocess timeout) | **Done** | `_call_c_exec` ran the C codec via `subprocess.run(...)` with no timeout, so a hung/looping codec process would block indefinitely. Added a generous default timeout (`_C_EXEC_TIMEOUT`, 300 s, overridable via the `NDI_COMPRESS_TIMEOUT` env var) and convert `TimeoutExpired` into a clear `RuntimeError`. |
| 6.2-8 (LICENSE) | **Done** | Added `LICENSE` (CC BY-NC-SA 4.0) matching the NDI-compress-matlabp counterpart. |

## FLAGGED — codec provenance + cross-language round-trip (not done here)

The audit's core §6.2-7 concern is that **NDI-compress is unauditable on both
sides**: the MATLAB side ships P-code and the Python side ships committed C
binaries, built at different times, so binary/format drift between the two codecs
cannot be ruled out. Resolving that requires either (a) vendoring the codec C
**source** in-repo and building it in CI, or (b) pinning a single versioned codec
build and committing a checksum manifest of the binaries — plus a cross-language
round-trip fixture test (compress with one language's codec, decompress with the
other, assert byte-identity). That work needs the codec build provenance / source
(not available in this environment) and a paired MATLAB run, so it is flagged for
a focused follow-up. Only the subprocess-timeout hardening and the LICENSE are
done here.
