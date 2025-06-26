from odoo import fields, models


class PlmConvertRule(models.Model):
    _name = "plm.convert.rule"
    _description = "Rule of conversions"

    start_format = fields.Char("Start Format")
    end_format = fields.Char("End Format")
    product_category = fields.Many2one("product.category", "Category")
    server_id = fields.Many2one("plm.convert.servers", "Conversion Server")
    output_name_rule = fields.Char(
        "Output Name Rule",
        default="'%s_%s' % (document.name, document.engineering_revision)",
    )
    convert_alone_documents = fields.Boolean(
        "Convert documents without component", default=False
    )
