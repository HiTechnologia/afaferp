from odoo import _, api, fields, models


class MrpBomLineTemplateCuttedParts(models.Model):
    _inherit = "mrp.bom.line"

    x_length = fields.Float(
        compute="compute_x_length", string=_("X Length"), default=0.0
    )
    y_length = fields.Float(
        compute="compute_y_length", string=_("Y Length"), default=0.0
    )
    client_x_length = fields.Float("X Cutted Qty", default=0)
    client_y_length = fields.Float("Y Cutted Qty", default=0)
    cutted_qty = fields.Float("Cutted Qty", default=0)

    def compute_x_length(self):
        for bom_line_id in self:
            if bom_line_id.cutted_type == "server":
                product = bom_line_id.bom_id.product_id
                if not product:
                    product = bom_line_id.bom_id.product_tmpl_id.product_variant_id
                bom_line_id.x_length = self.computeXLenghtByProduct(product)
            elif bom_line_id.cutted_type == "client":
                bom_line_id.x_length = bom_line_id.client_x_length
            else:
                bom_line_id.x_length = 0

    def compute_y_length(self):
        for bom_line_id in self:
            if bom_line_id.cutted_type == "server":
                product = bom_line_id.bom_id.product_id
                if not product:
                    product = bom_line_id.bom_id.product_tmpl_id.product_variant_id
                bom_line_id.y_length = self.computeYLenghtByProduct(product)
            elif bom_line_id.cutted_type == "client":
                bom_line_id.y_length = bom_line_id.client_y_length
            else:
                bom_line_id.y_length = 0

    @api.model
    def computeYLenghtByProduct(self, product_id):
        wastage_percent_y = product_id.wastage_percent_y or 1
        material_added_y = product_id.material_added_y
        new_qty = (
            product_id.row_material_y_length * wastage_percent_y
        ) + material_added_y
        return new_qty

    def computeXLenghtByProduct(self, product_id):
        material_percentage = product_id.wastage_percent or 1
        material_added = product_id.material_added
        new_qty = (
            product_id.row_material_x_length * material_percentage
        ) + material_added
        return new_qty

    def write(self, vals):
        res = super(MrpBomLineTemplateCuttedParts, self).write(vals)
        if not self.env.context.get("skip_cutted_recompute"):
            self.recomputeCuttedQty()
        return res

    @api.model_create_multi
    def create(self, vals):
        res = super(MrpBomLineTemplateCuttedParts, self).create(vals)
        res.recomputeCuttedQty()
        return res

    def recomputeCuttedQty(self):
        ctx = self.env.context.copy()
        ctx["skip_cutted_recompute"] = True
        for bom_line_id in self:
            bom_line_id.with_context(
                ctx
            ).product_qty = bom_line_id.computeCuttedTotalQty()

    def computeCuttedTotalQty(self):
        for bom_line_id in self:
            if bom_line_id.cutted_type in ("server", "client"):
                if bom_line_id.x_length or bom_line_id.y_length:
                    x_length = bom_line_id.x_length or 1
                    y_length = bom_line_id.y_length or 1
                    ret = x_length * y_length
                    cutted_qty = bom_line_id.cutted_qty or 1
                    ret = ret * cutted_qty
                    return ret or 1
            return bom_line_id.product_qty

    def computeTotalQty(self, xLenght, yLenght, cutted_qty):
        ret = xLenght * yLenght
        cutted_qty = cutted_qty or 1
        ret = ret * cutted_qty
        return ret or 1
