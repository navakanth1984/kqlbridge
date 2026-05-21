# Research: Neural & Learned Query Compiler Approaches

## Executive Summary

The optimal architecture for our KQL micro language model is a **deterministic rule-based compiler**,
NOT a neural network. However, neural techniques provide three valuable augmentations:
1. **Grammar-Constrained Decoding**: For accepting natural language KQL variants
2. **Few-Shot RAG**: For pattern-matching novel KQL constructs to known templates
3. **Execution-Guided Synthesis**: For validating generated SQL against a test database

---

## 1. Semantic Parsing Architectures for SQL (2024-2025)

### The Text-to-SQL Pipeline
Modern production Text-to-SQL systems use a **multi-stage pipeline**:

```
Natural Language Question
  → Schema Linking      (map NL tokens to table/column names)
  → Candidate Generation (beam search with multiple candidates)
  → Query Revision      (grammar check + execution feedback loop)
  → Final SQL
```

### Key Models (2024-2025)
- **DIN-SQL**: Decomposition + in-context learning, GPT-4 based
- **CodeS**: Code pre-trained small models (350M–15B params) for Text-to-SQL
- **DAIL-SQL**: Efficient prompting with question similarity + SQL demonstration
- **CHESS**: Contextual schema linking + hierarchical schema selection

### For KQL Translation (Not NL→SQL)
Our use case is **KQL→SQL** (formal-to-formal), NOT natural language to SQL.
This is fundamentally easier because:
- Source language is fully formal (no ambiguity)
- Grammar is known precisely
- We can parse source to AST deterministically

**Verdict**: Skip neural semantic parsing for the core engine. Use deterministic parsing.

---

## 2. Grammar-Constrained Decoding (PICARD, XGrammar)

### PICARD Architecture
PICARD wraps any autoregressive LM decoder and constrains output tokens to valid SQL:

```python
def picard_step(model, input_ids, grammar):
    # Get next token probabilities
    logits = model(input_ids)
    # Build list of valid next tokens based on current partial parse
    valid_tokens = grammar.valid_next_tokens(partial_sql=decode(input_ids))
    # Mask invalid tokens to -infinity
    masked_logits = mask_invalid(logits, valid_tokens)
    # Sample from valid distribution
    next_token = sample(masked_logits)
    return next_token
```

### XGrammar (2024) — The Modern Successor
XGrammar uses a finite-state machine (FSM) compiled from the target grammar:
- **Persistent Stack**: Tracks parse state without re-parsing entire prefix
- **Token Mask Cache**: Pre-computes valid token sets for common parse states
- **Pushdown Automaton**: Handles context-free grammars (SQL, JSON, etc.)

Performance: 5-20x faster than PICARD for constrained token generation.

### Application to KQL Micro Model
Grammar-constrained decoding is most useful if we add an **LLM-augmented mode**:

```python
class KQLAssistant:
    """LLM-powered KQL fix-up that produces valid KQL for our deterministic parser."""
    
    def repair(self, malformed_kql: str) -> str:
        """Use LLM with KQL grammar FSM to fix malformed KQL queries."""
        # Tokenize malformed KQL
        tokens = self.tokenizer(malformed_kql)
        # Run PICARD-style constrained decoding with KQL grammar
        valid_kql = self.constrained_decode(tokens, grammar=KQL_GRAMMAR)
        return valid_kql
```

---

## 3. NL2KQL Architecture (Schema Refiner + Few-Shot Selector + Query Refiner)

### Microsoft's NL2KQL Pipeline
```
User NL Question
  → Schema Refiner (selects relevant tables/columns from schema)
      Uses embedding similarity to find top-K relevant schema elements
  → Few-Shot Selector (retrieves top-N NL→KQL examples from corpus)
      Uses sentence-BERT to find semantically similar examples
  → KQL Generator (LLM with schema + examples as context)
      Typically GPT-4, Claude, or CodeLlama
  → Query Refiner (deterministic KQL parser validates & fixes)
      Uses official Kusto parser, retries if invalid
  → Final KQL Query
```

### RAG for KQL Translation Patterns
We can adapt this architecture for our **KQL→SQL translation**:

```python
# Retrieval-Augmented Generation for novel KQL patterns
class KQLTranslationRAG:
    def __init__(self, example_library: List[Tuple[str, Dict[str, str]]]):
        """
        example_library: List of (kql_pattern, {spark: sql1, tsql: sql2, ...})
        """
        self.embeddings = embed_all([kql for kql, _ in example_library])
        self.examples = example_library
    
    def retrieve_similar(self, kql: str, k: int = 3) -> List[Tuple[str, Dict]]:
        """Find k most similar KQL patterns and their translations."""
        query_emb = embed(kql)
        similarities = cosine_similarity(query_emb, self.embeddings)
        top_k = argsort(similarities)[-k:]
        return [self.examples[i] for i in top_k]
    
    def translate(self, kql: str, dialect: str) -> str:
        """
        If deterministic parser succeeds, use it.
        Otherwise, use RAG + LLM to generate translation.
        """
        try:
            return deterministic_translate(kql, dialect)
        except ParseError:
            examples = self.retrieve_similar(kql)
            return llm_translate(kql, dialect, examples)
```

---

## 4. Small Language Models (SLMs) for Code Translation

### Best SLMs for Code-to-Code Translation (2024-2025)
| Model | Params | Best Use | License |
|-------|--------|----------|---------|
| DeepSeek-Coder-V2-Lite | 2.4B | SQL generation | Open |
| Qwen2.5-Coder-3B | 3B | Multi-language code | Open |
| StarCoder2-3B | 3B | Code completion | Open |
| Phi-3.5-mini | 3.8B | Reasoning + code | Open |
| CodeGemma-2B | 2B | Code generation | Open |

### Fine-Tuning Strategy for KQL→SQL
```python
# Training data format for SLM fine-tuning
training_examples = [
    {
        "instruction": "Translate this KQL make-series to Spark SQL",
        "input": "T | make-series count() on TimeGenerated from ago(7d) to now() step 1d by Category",
        "output": """WITH grid AS (
    SELECT explode(sequence(
        current_timestamp() - INTERVAL 7 DAYS,
        current_timestamp(),
        INTERVAL 1 DAY
    )) AS TimeGenerated
), ..."""
    },
    # ... thousands more examples
]
```

### Our Approach: Deterministic First, SLM Fallback
```python
def translate_kql(kql: str, dialect: str) -> str:
    """
    Tier 1: Deterministic rule-based compiler (covers 95%+ of cases)
    Tier 2: RAG-augmented few-shot retrieval (covers novel patterns)  
    Tier 3: Fine-tuned SLM generation (covers edge cases, LLM hallucination risk)
    """
    try:
        return TEGv5Compiler().compile(kql, dialect)  # Tier 1
    except NotImplementedError:
        return rag_translate(kql, dialect)             # Tier 2
    except Exception:
        return slm_translate(kql, dialect)             # Tier 3
```

---

## 5. Tree-to-Tree Neural Translation

### Concept
Instead of string→string translation, encode source AST and decode to target AST:

```
KQL Parse Tree (source AST)
  → Graph Neural Network encoder (captures tree structure)
  → Latent representation
  → Tree-structured decoder (generates target AST token-by-token)
  → SQL AST (target)
  → SQL Generator → SQL String
```

### Key Papers
- **Tree-to-Tree Neural Networks for Program Translation** (Chen et al. 2018)
- **Structural Code Search with Code2Vec** (Alon et al. 2019)
- **TRANX: A Transition-based Neural XML Parser** (Yin & Neubig 2018)

### Why NOT for KQL Micro Model
Tree-to-tree models require:
1. Large labeled datasets of (KQL AST, SQL AST) pairs — we don't have this
2. Complex tree LSTM/GNN architectures — too heavy for "micro" model
3. Training infrastructure — defeats the purpose of a lightweight transpiler

**Verdict**: Tree-to-tree is architecturally interesting but impractical for our use case.

---

## 6. Execution-Guided Synthesis

### Concept
Generate multiple SQL candidates, execute them, select the one with correct output.

```python
class ExecutionGuidedSynthesizer:
    def translate(self, kql: str, dialect: str, test_db) -> str:
        # Generate 5 candidate translations
        candidates = [
            emitter.emit(plan) 
            for emitter in [emitter1, emitter2, emitter3, emitter4, emitter5]
        ]
        
        # Execute each candidate against test database
        results = []
        for sql in candidates:
            try:
                result = test_db.execute(sql)
                results.append((sql, result))
            except Exception:
                pass
        
        # Select candidate with best result (reference execution or majority vote)
        return select_best(results, reference=kql_execute(kql))
```

### Application for Our Stress Tests
We can use execution-guided synthesis for our **stress test validation**:
- Generate SQL translation
- Execute against in-memory DuckDB with sample data
- Compare result schema (column names, types, row counts) to expected

---

## 7. WASM-Based Micro Language Runtime

### Making Our Compiler Run Anywhere
The micro language model can be compiled to WebAssembly for:
- Browser-based KQL→SQL translation (no server needed)
- Edge deployment (Cloudflare Workers, Fastly Compute)
- Embedded in VS Code extension

### Tools
```bash
# Compile Python to WASM (experimental)
pip install py2wasm
py2wasm micro_model.py -o micro_model.wasm

# OR: Use Pyodide (Python in browser via WASM)
# Load pyodide + kqlbridge wheel in browser
```

### Alternative: Compile the Grammar/IR to Rust/Go
```
Python TEG compiler → generate Rust code → compile to WASM
This gives 100x performance improvement for browser use
```

---

## Final Architecture Recommendation

### Micro Language Model = TEG v5 Compiler + RAG Library + Optional SLM Fallback

```
┌─────────────────────────────────────────────────────────────────┐
│                    KQL Micro Language Model                      │
│                                                                   │
│  Input: KQL make-series / temporal join query                    │
│                    │                                              │
│         ┌──────────▼──────────┐                                  │
│         │  Tier 1: TEG v5     │  ← Deterministic compiler        │
│         │  Rule-based parser  │    handles 95%+ queries          │
│         │  + optimizer        │                                   │
│         │  + dialect emitters │                                   │
│         └──────────┬──────────┘                                   │
│           success  │  ParseError / NotImplementedError            │
│                    ▼                                              │
│         ┌──────────────────────┐                                  │
│         │  Tier 2: RAG Library │  ← Pattern matching against      │
│         │  (embedding + FAISS) │    translation example corpus   │
│         └──────────┬───────────┘                                  │
│           success  │  LowConfidence                               │
│                    ▼                                              │
│         ┌──────────────────────┐                                  │
│         │  Tier 3: SLM (opt.)  │  ← Phi-3.5-mini or Qwen-3B     │
│         │  Grammar-constrained │    with PICARD/XGrammar         │
│         └──────────────────────┘                                  │
│                                                                   │
│  Output: Spark SQL / T-SQL / PySpark / Pandas / DuckDB code     │
└─────────────────────────────────────────────────────────────────┘
```
