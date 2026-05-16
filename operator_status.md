# Operator Status — KQLBridge v0.1

> Updated by human after each BIT Integrate phase.
> Never auto-updated by the agent mid-session.

---

## Current Eval Score

| Version | Score | Cases Passing | Updated |
|---|---|---|---|
| scaffold | 0.0% | 0/100 | 2026-05-16 |

---

## Operator Coverage

| # | Operator | Status | Eval Cases | Notes |
|---|---|---|---|---|
| 01 | `where` | ⬜ Not started | std_001, std_002, std_010, edge_001 | |
| 02 | `project` | ⬜ Not started | std_003, std_005 | |
| 03 | `summarize count()` | ⬜ Not started | std_001, std_004, std_008 | Jagged risk: GROUP BY restructure |
| 04 | `summarize sum/avg/min/max` | ⬜ Not started | std_006, std_007, edge_002 | Human review required |
| 05 | `bin()` | ⬜ Not started | std_009, edge_003 | 5m bin edge case — see skill |
| 06 | `ago()` | ⬜ Not started | std_002, std_011 | INTERVAL unit mapping |
| 07 | `extend` | ⬜ Not started | std_012, std_013 | |
| 08 | `order by` / `sort by` | ⬜ Not started | std_014, std_015 | both keywords accepted |
| 09 | `take` / `limit` | ⬜ Not started | std_016 | both keywords accepted |
| 10 | `distinct` | ⬜ Not started | std_017 | |
| 11 | `join` (inner) | ⬜ Not started | std_018, edge_004 | ON key extraction from `by` |
| 12 | `union` | ⬜ Not started | std_019 | → UNION ALL |
| 13 | `let` variables | ⬜ Not started | edge_005, edge_006 | CTE hoisting — most complex |
| 14 | `count()` | ⬜ Not started | std_020 | scalar COUNT(*) |

**Legend**: ⬜ Not started · 🔄 In progress · ✅ Green · ❌ Failing

---

## Session Log

### 2026-05-16 — Session 0: Repo scaffold
- Created repo structure, locked files, eval harness
- Benchmark: 100 cases seeded
- Score: 0.0% (expected — no generator logic yet)
- Next: Wk 3 — implement where + project + take + distinct

---

## Bloat Audit History

*(No audit runs yet — first audit after operators 1–4 are green)*
