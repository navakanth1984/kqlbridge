# Research: Compiler IR & Language Design for KQL Micro Language Model

## Executive Summary

The optimal architecture for a production-grade KQL → multi-dialect SQL micro language model is a
**Canonical Temporal IR (CTIR)** — a Python dataclass-based intermediate representation modeled after
Substrait's relational algebra, Ibis's deferred expression tree, and SQLGlot's dialect system.
This hybrid approach gives us dialect-agnostic logical planning + optimized per-dialect code emission.

---

## 1. Flounder IR

### What it is
Flounder IR is a database-specific intermediate representation developed at TU Berlin (2021).
Unlike LLVM IR which is too low-level (CPU instructions), Flounder IR sits at the "sweet spot" between
relational algebra and machine code — it represents vectorized tuple-at-a-time operations as
abstract loop constructs.

### Key Design Principles
- **Block-based IR**: Operations expressed as "blocks" of iteration over relation columns
- **Fusion**: Adjacent relational operators (filters, projections) are fused into single loops
- **Codegen target**: Compiles to x86 assembly via a thin backend layer
- **Low latency**: Compilation time is 10-100x faster than LLVM-based approaches

### Relevance to KQL Micro Model
Flounder IR is too low-level for our transpilation use case (we target SQL strings, not machine code).
However its **fusion principle** is valuable: our TEG optimizer should fuse adjacent `where` + `make-series`
clauses into a single scan with predicate pushdown rather than generating separate CTEs.

**Verdict**: Borrow the fusion pattern; skip the IR format itself.

---

## 2. Apache Arrow DataFusion LogicalPlan / PhysicalPlan

### Architecture
DataFusion is a Rust-based query engine using Apache Arrow as the in-memory format.
Its planning pipeline:

```
SQL String
  → sql_to_statement()  (sqlparser-rs)
  → statement_to_plan() → LogicalPlan (relational algebra AST)
  → optimize()          → Optimized LogicalPlan (via optimizer rules)
  → create_physical_plan() → ExecutionPlan (physical plan with operators)
  → execute()           → RecordBatch stream
```

### LogicalPlan Node Types (key ones)
```rust
enum LogicalPlan {
    Projection { expr, input },
    Filter { predicate, input },
    Aggregate { group_expr, aggr_expr, input },
    Sort { expr, input },
    Join { left, right, on, join_type },
    TableScan { table_name, filters, projected_schema },
    // Extension nodes for custom operators!
    Extension { node: Arc<dyn UserDefinedLogicalNode> },
}
```

### Relevance to KQL Micro Model
- DataFusion's `Extension` node pattern is **exactly what we need** for temporal operators
- We can define `MakeSeriesNode`, `SeriesFillNode`, `AsofJoinNode` as extension nodes
- The `LogicalPlan` enum pattern maps perfectly to Python dataclasses for our TEG AST
- The optimizer rule pipeline (trait-based passes) maps to our `TEGOptimizer` passes

**Verdict**: Model our Python TEG AST structure directly after DataFusion's LogicalPlan.
Use Python `@dataclass` frozen nodes with an `accept(visitor)` method.

---

## 3. Substrait: Universal Query Plan Format

### What it is
Substrait is a cross-language serialization format for query plans, backed by Google, Voltron,
DuckDB team, and Apache Arrow. Uses Protocol Buffers for binary serialization.

### Key Concepts
```protobuf
message Rel {
  oneof rel_type {
    ReadRel read = 5;
    FilterRel filter = 6;
    FetchRel fetch = 7;
    AggregateRel aggregate = 8;
    SortRel sort = 9;
    JoinRel join = 10;
    ProjectRel project = 11;
    ExtensionSingleRel extension_single = 12;  // ← Custom temporal nodes here!
  }
}
```

### Extension Mechanism
Substrait allows custom functions via YAML extension files:
```yaml
# kql_temporal_extensions.yaml
functions:
  make_series:
    description: KQL time-series grid generation with gap filling
    args: [aggregation, axis_col, start, end, step, by_cols, default_val]
    return: RELATION
```

### Ecosystem Adoption (2024)
- **DuckDB**: Community extension for Substrait produce/consume
- **Apache Acero**: Full Substrait consumer
- **Velox**: Substrait consumer for Spark native acceleration
- **Ibis**: Uses Substrait as serialization layer for some backends

### Relevance to KQL Micro Model
Substrait is the **most theoretically sound** choice for a canonical IR because:
1. Cross-language: Python compiler → Rust emitter → Java emitter all share same plan format
2. Extension mechanism lets us register `make_series`, `series_fill_linear`, `asof_join` as custom functions
3. DuckDB + Arrow ecosystem can directly execute Substrait plans

**However**: For our immediate goal (Python micro model emitting SQL strings), Substrait adds
unnecessary complexity. We would spend 80% of time on protobuf plumbing vs. actual transpilation.

**Verdict**: Define our TEG AST to be **structurally isomorphic** to Substrait's `Rel` hierarchy,
so future Substrait serialization is a mechanical translation. Do NOT use protobuf now.

---

## 4. MLIR for Database Query Compilation

### What it is
MLIR (Multi-Level Intermediate Representation) is a compiler infrastructure from Google/LLVM
that supports multiple "dialects" — named namespaces of operations at different abstraction levels.

### Key Database MLIR Projects
- **ONNX-MLIR**: Compiles ONNX ML models to various backends
- **Polygeist**: C/C++ → MLIR for polyhedral optimization
- **VAST (Verifiable Abstract Syntax Tree)**: C/C++ analysis using MLIR
- **Lingo DB**: Full SQL-to-hardware compiler using MLIR (`rel` dialect → `tuple` dialect → LLVM)
- **PRISM**: Query compilation using MLIR for database execution

### Lingo DB MLIR Dialect Hierarchy
```
SQL String
  → rel dialect (relational algebra: scan, select, join, aggr)
  → subop dialect (sub-operators: nested loops, hash tables)
  → tuple dialect (tuple-at-a-time execution model)
  → LLVM dialect
  → native machine code
```

### Relevance to KQL Micro Model
MLIR's **multi-level dialect approach** is architecturally instructive:
- We want `kql dialect` → `temporal-rel dialect` → `sql-{spark,tsql,pandas} dialect`
- The pass manager (sequence of lowering passes) maps to our `TEGOptimizer`
- The dialect registration system maps to our emitter registry

**Verdict**: Adopt MLIR's **dialect hierarchy + lowering pass** conceptual model for our TEG v5.
This means: KQL Frontend → Temporal IR (dialect 1) → Optimized IR (dialect 2) → SQL String (dialect 3).

---

## 5. Ibis Project: Multi-Backend DataFrame Abstraction

### Architecture
Ibis provides a single Python DataFrame API that compiles to 20+ backends.

```
ibis.table(schema) → ibis.expr.Table
  .filter(condition) → FilterExpr(TableExpr, BoolExpr)
  .mutate(col=expr)  → ProjectionExpr(...)
  .group_by(cols).agg(expr) → AggregateExpr(...)
  .execute()  → compiles to backend-specific SQL or API calls
```

### Expression Tree Internals
```python
class Expr:
    op: Node  # immutable operation node

class Node(ABC):
    args: dict  # named arguments, typed
    
    @abstractmethod
    def output_dtype(self): ...

# Example temporal node:
class TimeBucket(Node):
    col: TimeExpr
    bucket_size: IntervalValue
    # → DATE_TRUNC in SparkSQL, time_bucket() in DuckDB, floor() in Pandas
```

### Dialect System (via SQLGlot)
Ibis uses SQLGlot as its SQL generation backend for most SQL-emitting backends.
The `ibis.backends.base.sql` compiles `Node` trees to dialect-specific SQL.

### Key Takeaway for KQL Micro Model
Ibis's architecture **directly solves our problem**:
- Immutable frozen expression nodes (our `TEGNode` dataclasses)
- Visitor pattern for dialect-specific code generation (our `DialectEmitter`)
- Node equality based on structural/semantic content (allows deduplication optimization)

**Verdict**: Model our `TimeSeriesMicroModel` v2 as an **Ibis-style expression builder**
that constructs a frozen TEG AST and then compiles it to any target dialect.

---

## 6. SQLGlot: Multi-Dialect SQL Transpiler

### Architecture (Recursive Descent + Visitor Pattern)
```
SQL String (dialect A)
  → Tokenizer  → TokenList
  → Parser     → AST (dialect-agnostic Expression tree)
  → Optimizer  → Optimized AST (optional rule-based passes)
  → Generator  → SQL String (dialect B)
```

### Key Design Patterns
1. **Monolithic Expression hierarchy**: All SQL constructs are `Expression` subclasses
2. **Dialect as class**: Each SQL dialect is a Python class with `parser_opts`, `tokenizer_opts`, `generator_opts`
3. **Generator via dispatch**: `Generator.generate(node)` dispatches on `type(node).__name__`
4. **Transforms**: Functional AST transforms via `node.transform(fn)` or `node.walk()`

### Example Dialect Override (time functions)
```python
class SparkSQL(Dialect):
    class Generator(generator.Generator):
        TRANSFORMS = {
            exp.DateTrunc: lambda self, e: f"DATE_TRUNC({e.args['unit']}, {self.generate(e.this)})",
            exp.DateAdd:   lambda self, e: f"DATEADD({e.args['unit']}, {self.generate(e.args['expression'])}, {self.generate(e.this)})",
        }
```

### Temporal Extension Point
SQLGlot has an `Anonymous` function node for unrecognized function calls.
We can hook into this to handle KQL temporal functions before SQLGlot sees them.

**Verdict**: For our generated SQL output, consider using SQLGlot's Generator as the **final
formatting layer** to handle dialect-specific syntax differences automatically.
Our TEG emits a canonical SQL string → SQLGlot transpiles to exact target dialect.

---

## Synthesis: Recommended Micro Model Architecture (TEG v5 Refined)

### Three-Layer Compiler

```
Layer 1: KQL Frontend Parser (Python regex + precedence climbing)
          ↓
    TEG IR (Temporal Execution Graph) — Python frozen dataclasses
    - TEGPipeline(source, operators: List[TEGOp])
    - TEGMakeSeries(agg_specs, axis, from_, to, step, by)
    - TEGFill(col, method, default)
    - TEGWindow(col, func, window_size)
    - TEGCoalesce(partition_cols)
    - TEGAsofJoin(left, right, key, timestamp)
    - TEGOverlapJoin(left, right, key, valid_from, valid_to)
          ↓
Layer 2: TEG Optimizer Passes
    - PredicatePushdownPass   → moves filters into source scan
    - GridSparsityPass        → detects sparse entities, uses LATERAL instead of CROSS JOIN
    - CascadingStepNormalizer → normalizes multi-step intervals
          ↓
Layer 3: Dialect Emitters (Visitor pattern)
    - SparkSQLEmitter.emit(node) → Spark SQL string
    - TSQLEmitter.emit(node)     → T-SQL string  
    - PySparkEmitter.emit(node)  → PySpark Python code
    - PandasEmitter.emit(node)   → Pandas Python code
    - DuckDBEmitter.emit(node)   → DuckDB SQL (NEW - uses native ASOF JOIN + time_bucket)
```

### Why This is a New Architecture
Unlike the current string-template approach, this gives us:
1. **Semantic correctness**: Optimizer prevents OOM via sparsity detection
2. **Composability**: Operators compose algebraically (fill ∘ make-series = valid pipeline)
3. **Extensibility**: New dialects = new Emitter class; no changes to parser or IR
4. **Testability**: Each layer tests independently (parse, optimize, emit)
5. **Future-proof**: TEG IR is structurally isomorphic to Substrait for future interop
