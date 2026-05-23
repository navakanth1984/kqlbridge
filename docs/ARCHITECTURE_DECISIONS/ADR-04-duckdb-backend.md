# ADR-04: DuckDB Local Verification Backend

## Context
Validating compiler correctness in varied runtime environments requires active query execution validation. Rather than setting up complex, remote Spark and SQL Server testing nodes, we need a local, lightweight oracle.

## Decision
DuckDB is utilized strictly as an in-memory verification engine (`verify(kql, df) -> VerificationResult`). It is NOT exposed as a primary transpilation output target, protecting system modularity while providing extremely fast local schema and count validations.
