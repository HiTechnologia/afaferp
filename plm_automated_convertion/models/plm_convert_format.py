from odoo import fields, models


class PlmConvertFormat(models.Model):
    _name = "plm.convert.format"
    _description = "Convert Format"
    _order = "sequence ASC"

    sequence = fields.Integer("Sequence", default="1")
    name = fields.Char("Format Name", compute="_compute_name")
    available = fields.Boolean("Available for conversion")
    start_format = fields.Char("Start Format", required=True)
    end_format = fields.Char("End Format", required=True)
    cad_name = fields.Char("Cad Name", required=True)
    server_id = fields.Many2one("plm.convert.servers", string="Server", required=True)

    def _compute_name(self):
        for plm_convert_format in self:
            plm_convert_format.name = "%s %s %s %s" % (
                plm_convert_format.server_id.name or "",
                plm_convert_format.cad_name,
                plm_convert_format.name,
                plm_convert_format.end_format,
            )
