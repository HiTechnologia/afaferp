
def migrate(cr, version):
    # Fix upgrade error
    cr.execute("""
        UPDATE ir_model_fields
        SET tracking = NULL
        WHERE model = 'formio.extra.asset'
    """)
