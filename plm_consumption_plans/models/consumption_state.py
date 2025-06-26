from odoo import models, fields


class ConsumptionState(models.Model):
    _name = "consumption.state"
    _description = "Consumption State"
    _rec_name = "name"

    name = fields.Char(string="Consumption State", required=True)

