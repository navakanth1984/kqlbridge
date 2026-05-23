# ADR-06: CompilerOptions Implementation

## Context
KQLBridge v0.11.5 sniffed `sys.argv` to toggle oracle-parity formatting, which violated the thread-safety and side-effect isolation requirements of multi-user enterprise servers.

## Decision
All compiler behavior switches are configured exclusively via the `CompilerOptions` slot-optimized dataclass. Standalone global variable toggles are eliminated from `translate()`, making all transpilation paths pure, thread-safe, and deterministic.
