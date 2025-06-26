from odoo import api, models


class MrpBomLine(models.Model):
    _inherit = "mrp.bom.line"

    @api.onchange("state")
    def onchange_line_state(self):
        """
        Force update flag every time bom line state changes
        """
        for bomLineObj in self:
            bomBrws = bomLineObj.bom_id
            bomBrws._obsolete_compute()
