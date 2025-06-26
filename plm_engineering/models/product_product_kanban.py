from odoo import _, models


class ProdProdKanbanExtension(models.Model):
    _inherit = 'product.product'

    def open_engine_bom(self):

        boms = self.get_related_boms()
        domain = [('id', 'in', boms.ids), ('type', '=', 'ebom')]
        return self.common_open(
            _('Related Boms'),
            'mrp.bom',
            'list,form',
            'form',
            boms.ids,
            self.env.context,
            domain
        )
