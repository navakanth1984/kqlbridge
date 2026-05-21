from __future__ import annotations
import os
import json
import re
from typing import Dict, List, Optional, Any

class MLMAgent:
    """
    KQLBridge Micro Language Model (MLM) Agent.
    
    A self-contained telemetry and self-correcting dynamic translator that:
    1. Tracks compilation and parse failures.
    2. Stores and fuzzy-recalls exact query overrides.
    3. Interprets the Bridge Meta-Language (BML) to map and bind custom query patterns.
    """
    
    def __init__(self, memory_path: Optional[str] = None):
        if memory_path is None:
            # Place in user's home directory to persist across project rebuilds
            self.memory_path = os.path.join(os.path.expanduser("~"), ".kqlbridge_memory.json")
        else:
            self.memory_path = memory_path
            
        self.memory: Dict[str, Any] = {
            "overrides": {},
            "rules": [],
            "telemetry": {
                "failures": {},
                "success_count": 0,
                "total_translations": 0
            }
        }
        self.load_memory()

    def load_memory(self) -> None:
        """Load telemetry and overrides from local JSON store."""
        if os.path.exists(self.memory_path):
            try:
                with open(self.memory_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Merge loaded data into baseline structures defensively
                    self.memory["overrides"].update(data.get("overrides", {}))
                    self.memory["rules"] = data.get("rules", [])
                    
                    loaded_tel = data.get("telemetry", {})
                    self.memory["telemetry"]["failures"].update(loaded_tel.get("failures", {}))
                    self.memory["telemetry"]["success_count"] = loaded_tel.get("success_count", 0)
                    self.memory["telemetry"]["total_translations"] = loaded_tel.get("total_translations", 0)
            except Exception as e:
                import logging
                logging.warning("[kqlbridge] MLM Agent failed to load memory database from %s: %s", self.memory_path, e)

    def save_memory(self) -> None:
        """Commit memory database to the local JSON file."""
        try:
            with open(self.memory_path, "w", encoding="utf-8") as f:
                json.dump(self.memory, f, indent=4, ensure_ascii=False)
        except Exception as e:
            import logging
            logging.warning("[kqlbridge] MLM Agent failed to save memory database to %s: %s", self.memory_path, e)

    def clear(self) -> None:
        """Reset MLM memory database and telemetries."""
        self.memory = {
            "overrides": {},
            "rules": [],
            "telemetry": {
                "failures": {},
                "success_count": 0,
                "total_translations": 0
            }
        }
        self.save_memory()

    def learn(self, kql: str, error: Optional[str] = None, fix_sql: Optional[str] = None) -> None:
        """
        Record translation telemetries and learn override solutions.
        
        Args:
            kql: The source KQL query.
            error: Compiler error message string if translation failed.
            fix_sql: Target override SQL string to associate with the KQL query.
        """
        norm_kql = " ".join(kql.strip().split())
        
        if fix_sql:
            # Register explicit static override mapping (administrative setup, not translation invocation)
            self.memory["overrides"][norm_kql] = fix_sql
            self.save_memory()
            return
            
        self.memory["telemetry"]["total_translations"] += 1
        
        if error:
            # Record compilation error details
            failures = self.memory["telemetry"]["failures"]
            if norm_kql not in failures:
                failures[norm_kql] = {"error": error, "count": 0}
            failures[norm_kql]["count"] += 1
            # Persist failure telemetry immediately to disk to diagnose parser gaps
            self.save_memory()
        else:
            self.memory["telemetry"]["success_count"] += 1
            # Optimization: Do NOT write to disk on standard successful translation calls
            # to prevent high disk I/O latency under highly concurrent production workloads.

    def register_rule(self, pattern: str, mapping: str) -> None:
        """
        Register a custom Bridge Meta-Language (BML) translation rule.
        
        Example:
            pattern = "AppLogs | custom_regex({col}, {pat})"
            mapping = "SELECT * FROM AppLogs WHERE {col} RLIKE {pat}"
        """
        rule = {
            "pattern": " ".join(pattern.strip().split()),
            "mapping": mapping.strip()
        }
        if rule not in self.memory["rules"]:
            self.memory["rules"].append(rule)
            self.save_memory()

    def recall(self, kql: str) -> Optional[str]:
        """
        Search memory for an exact override or a matching Bridge Meta-Language rule.
        
        Returns:
            Mapped SQL translation string if matched, otherwise None.
        """
        norm_kql = " ".join(kql.strip().split())
        
        # 1. Check exact overrides first
        if norm_kql in self.memory["overrides"]:
            return self.memory["overrides"][norm_kql]
            
        # 2. Check dynamic Bridge Meta-Language (BML) pattern matches
        for rule in self.memory["rules"]:
            resolved = self._match_and_bind(rule["pattern"], rule["mapping"], norm_kql)
            if resolved:
                return resolved
                
        return None

    def _match_and_bind(self, pattern: str, mapping: str, query: str) -> Optional[str]:
        """
        Parse and bind template parameters using the Bridge Meta-Language regex engine.
        
        CRITICAL CONSTRAINT: BML is a regex-based template mapper. It does not parse
        nested recursive brackets (e.g. `prev(touppercase(col))`) as distinct AST parameters.
        For advanced nested structures, use core Lark compiler rules.
        
        Example:
            pattern: "T | custom({col})"
            query:   "T | custom(Message)"
            yields:  col = "Message"
        """
        # Find all placeholders like {placeholder_name}
        placeholders = re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", pattern)
        if not placeholders:
            # Static rule fallback
            return mapping if pattern.lower() == query.lower() else None

        # Build regular expression from pattern template
        # Escape special regex characters except for the braces of placeholders
        regex_parts = []
        last_end = 0
        for m in re.finditer(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", pattern):
            prefix = pattern[last_end:m.start()]
            regex_parts.append(re.escape(prefix))
            # Replace placeholder with named capturing group
            var_name = m.group(1)
            regex_parts.append(f"(?P<{var_name}>.+?)")
            last_end = m.end()
        regex_parts.append(re.escape(pattern[last_end:]))
        
        # Assemble complete anchored regular expression (ignoring minor whitespace variations)
        regex_str = "".join(regex_parts)
        # Allow flexible spacing around pipe characters and operators
        regex_str = re.sub(r"\\\s", r"\\s+", regex_str)
        regex_str = re.sub(r"\\\|", r"\\s*\\|\\s*", regex_str)
        regex_str = re.sub(r"\\\(", r"\\s*\\(\\s*", regex_str)
        regex_str = re.sub(r"\\\)", r"\\s*\\)\\s*", regex_str)
        regex_str = re.sub(r"\\,", r"\\s*,\\s*", regex_str)
        
        try:
            regex = re.compile(f"^{regex_str}$", re.IGNORECASE)
            match = regex.match(query)
            if match:
                bindings = match.groupdict()
                # Interpolate placeholders in the mapping template
                resolved_sql = mapping
                for var, val in bindings.items():
                    # Strip quotes or redundant spacing inside values defensively
                    clean_val = val.strip()
                    resolved_sql = resolved_sql.replace(f"{{{var}}}", clean_val)
                return resolved_sql
        except re.error:
            pass
            
        return None

    def suggest_fix_via_ai(self, kql: str, error: str) -> Optional[str]:
        """
        Analyze transpilation failure and generate a self-correcting SQL override using Sarvam AI.
        
        This dynamically leverages our AI capabilities to diagnose compiler gaps.
        """
        # Read the Sarvam AI Key from the memory registry
        api_key = "sk_gv5b8wyc_4OCnebfWVHGJsGMr7Pp7IGr2"
        if not api_key:
            return None
            
        import urllib.request
        import urllib.error
        
        url = "https://api.sarvam.ai/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # Structured system prompt instructing the model to return ONLY SQL code
        system_prompt = (
            "You are the KQLBridge AI Agent. Your job is to analyze KQL parsing/compilation errors "
            "and suggest the exact target SQL (Spark SQL dialect) translation. "
            "Return ONLY the raw SQL string without markdown formatting, backticks, or other text."
        )
        
        prompt_content = (
            f"KQL Input Query:\n{kql}\n\n"
            f"Compiler Error:\n{error}\n\n"
            f"Generate the exact equivalent SQL translation query:"
        )
        
        data = {
            "model": "sarvam-chat",  # or compatible sarvam model endpoint
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt_content}
            ],
            "temperature": 0.1
        }
        
        try:
            req = urllib.request.Request(
                url, 
                data=json.dumps(data).encode("utf-8"), 
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                res_body = response.read().decode("utf-8")
                res_json = json.loads(res_body)
                choices = res_json.get("choices", [])
                if choices:
                    sql_ans = choices[0].get("message", {}).get("content", "").strip()
                    # Clean out markdown code boundaries if any leaked
                    sql_ans = re.sub(r"^```sql\s*", "", sql_ans, flags=re.IGNORECASE)
                    sql_ans = re.sub(r"^```\s*", "", sql_ans)
                    sql_ans = re.sub(r"\s*```$", "", sql_ans)
                    return sql_ans.strip()
        except Exception:
            # Fall back to None if API call times out or encounters authorization issues
            pass
            
        return None
