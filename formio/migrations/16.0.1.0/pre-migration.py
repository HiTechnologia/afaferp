def migrate(cr, version):
    cr.execute("""
        DELETE FROM ir_model_data
        WHERE model = 'formio.version'
    """)
