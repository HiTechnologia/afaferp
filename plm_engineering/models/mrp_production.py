from odoo import models


class MrpProductionExtension(models.Model):
    _name = 'mrp.production'
    _inherit = 'mrp.production'

    def product_id_change(self, product_id, product_qty=0):
        """ Finds UoM of changed product.
        @param product_id: Id of changed product.
        @param product_qty:
        @return: Dictionary of values.
        """
        result = super(MrpProductionExtension, self).product_id_change(
            product_id,
            product_qty
        )
        out_values = result.get('value', {})
        bom_id = out_values.get('bom_id', False)
        if bom_id:
            bom_brws = self.env['mrp.bom'].browse(bom_id)
            if bom_brws.type == 'ebom':
                return {'value': {
                    'product_uom_id': False,
                    'bom_id': False,
                    'routing_id': False,
                    'product_uos_qty': 0,
                    'product_uos': False
                }}
        return result
