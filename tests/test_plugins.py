from __future__ import annotations
from kqlbridge.plugins import register_renderer, register_optimizer, get_renderer, get_optimizers
from kqlbridge.ast_nodes import WhereOp
from kqlbridge import translate
import kqlbridge.plugins

def test_renderer_plugin_registration():
    # Setup custom renderer for WhereOp in spark dialect
    @register_renderer(node_type=WhereOp, dialect="spark")
    def custom_where_spark(generator, node):
        return "GENERATOR_PLUGINS_RULE"
        
    assert get_renderer(WhereOp, "spark") is custom_where_spark
    
    # Verify translation overrides using the registered plugin
    try:
        sql = translate("Logs | where x == 1", target="spark")
        assert "GENERATOR_PLUGINS_RULE" in sql
    finally:
        # Clean up global registry state to prevent state leaking
        kqlbridge.plugins._RENDERERS.pop((WhereOp, "spark"), None)

def test_renderer_plugin_pyspark():
    # Setup custom renderer for WhereOp in pyspark dialect
    @register_renderer(node_type=WhereOp, dialect="pyspark")
    def custom_where_pyspark(generator, node, df_name):
        return "filter('CUSTOM_PYSPARK_WHERE')"
        
    try:
        py_code = translate("Logs | where x == 1", target="pyspark")
        assert "CUSTOM_PYSPARK_WHERE" in py_code
    finally:
        kqlbridge.plugins._RENDERERS.pop((WhereOp, "pyspark"), None)

def test_optimizer_plugin_registration():
    # Register custom optimizer pass
    @register_optimizer
    def my_custom_opt(query):
        query.table = "optimised_table"
        return query
        
    assert my_custom_opt in get_optimizers()
    
    try:
        sql = translate("Logs | where x == 1", target="spark")
        assert "FROM optimised_table" in sql
    finally:
        kqlbridge.plugins._OPTIMIZERS.remove(my_custom_opt)
