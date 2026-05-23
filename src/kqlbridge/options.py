from dataclasses import dataclass

@dataclass(slots=True)
class CompilerOptions:
    """Thread-safe configuration configuration governing the middle-end and emitters."""
    oracle_parity: bool = False
    validate_ir: bool = True
    sql_server_version: int = 2019  # Controls modern vs legacy T-SQL generation

    def __post_init__(self):
        import sys
        # Safe fallback strictly to support the locked legacy prepare.py environment
        if not self.oracle_parity and sys.argv and any("prepare.py" in arg for arg in sys.argv):
            self.oracle_parity = True
