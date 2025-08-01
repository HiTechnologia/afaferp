import logging

from odoo import _, fields, models
from odoo.exceptions import UserError


class mrp_bom_data_compute(models.Model):
    _name = "plm.temporary_date_compute"
    _description = "Temporary model for computing dates"

    compute_type = fields.Selection(
        [
            (
                "update",
                _(
                    "Update Bom replacing obsoleted bom lines"
                    " with components at the latest revision."
                ),
            ),
            ("new_bom", _("Create new bom using last revision of all components.")),
        ],
        _("Compute Type"),
        required=True,
    )

    def scheduler_update_obsolete_bom(self, compute_type):
        logging.info(
            "Scheduler to update obsolete boms started with computation type"
            " %r" % (compute_type)
        )
        tmpObj = self.create({"compute_type": compute_type})
        if tmpObj:
            bomObj = tmpObj.env["mrp.bom"]
            bomBrwsList = bomObj.search([("obsolete_presents", "=", True)])
            tmpObj.env.context["active_ids"] = bomBrwsList.ids
            tmpObj.action_compute_bom()
        else:
            logging.info("Cannot create a new temporary object")
        logging.info("Scheduler to update obsolete boms ended")
        tmpObj.unlink()

    def action_compute_bom(self):
        """
        Divide due to choosen operation
        """
        # Surely one record a time arrive here because comes from xml
        bomIds = self.env.context.get("active_ids", [])
        if self.compute_type == "update":
            self.updateObsoleteBom(bomIds)
        elif self.compute_type == "new_bom":
            self.copyObsoleteBom(bomIds)
        else:
            raise _("You must select at least one option!")

    def updateObsoleteBom(self, bomIds=[], recursive=False):
        """
        Update all obsoleted bom lines with last released product
        """
        bomObj = self.env["mrp.bom"]
        prodProdObj = self.env["product.product"]
        for bomBrws in bomObj.browse(bomIds):
            if bomBrws.type != "normal":
                raise UserError(_("This functionality is avaible only for normal bom."))
            for bomLineBrws in bomBrws.bom_line_ids:
                templateBrws = bomLineBrws.product_id.product_tmpl_id
                if recursive:
                    bomIds = bomObj.getBomFromTemplate(templateBrws, "normal").ids
                    self.updateObsoleteBom(bomIds)
                if not templateBrws:
                    logging.warning(
                        "Product %s is not related to a product template."
                        % (bomLineBrws.product_id.id)
                    )
                    continue
                if templateBrws.engineering_state == "obsoleted":
                    eng_code = templateBrws.engineering_code
                    prodProdBrws = prodProdObj.search(
                        [("engineering_code", "=", eng_code)],
                        order="engineering_revision DESC",
                        limit=1,
                    )
                    for prodBrws in prodProdBrws:
                        bomLineBrws.product_id = prodBrws
                        bomLineBrws.bom_id._obsolete_compute()
                        # Not set before new product assignment
                        bomObj.updateWhereUsed(prodBrws)
                        if recursive:
                            # Check if new added product has boms
                            self.updateObsoleteBom(prodBrws.product_tmpl_id.bom_ids.ids)
            bomBrws._obsolete_compute()

        return {
            "type": "ir.actions.act_window",
            "name": _("Product Engineering"),
            "view_type": "form",
            "view_mode": "form",
            "res_model": "mrp.bom",
            "domain": [("id", "in", bomIds)],
        }

    def copyObsoleteBom(self, bomIds=[]):
        """
        Copy current bom containing obsoleted components and update the copy
        with the last product revisions.
        """
        bomObject = self.env["mrp.bom"]
        for bomId in bomIds:
            newBomBrws = bomObject.browse(bomId).copy()
            self.updateObsoleteBom(newBomBrws.ids)
        bomObject.browse(bomIds).write({"active": False})
        return {
            "type": "ir.actions.act_window",
            "name": _("Product Engineering"),
            "view_type": "form",
            "view_mode": "form",
            "res_model": "mrp.bom",
            "domain": [("id", "in", newBomBrws.id)],
        }
