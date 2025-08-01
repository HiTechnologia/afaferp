import logging

from odoo import _, api, fields, models


class mrp_bom_extension_data(models.Model):
    _name = "mrp.bom"
    _inherit = "mrp.bom"

    # If store = True is set you need to provide @api.depends because odoo has to know
    # when to compute that field.
    # If you decide to compute that field each time without store you have always to put
    # it in the view or the field will not be computed
    obsolete_presents_computed = fields.Boolean(
        string=_("Obsolete presents computed"), compute="_obsolete_compute"
    )
    obsolete_presents = fields.Boolean(_("Obsolete presents"))

    # This fields has not to be computed fields because
    # bom may be very big and the time too
    obsolete_presents_recursive = fields.Boolean(
        _("Obsolete presents Recursive"), default=False
    )

    def _obsolete_compute(self):
        """
        Verify if obsolete lines are present in current bom
        """
        logging.info("_obsolete_compute started")
        for bomObj in self:
            if bomObj.type == "ebom":
                # Engineering BOM cannot have this flag computed because every time
                # the user save by the CAD
                # The BOM will change. Is not correct to change Engineering BOM
                # by Odoo user...
                bomObj.obsolete_presents = False
                bomObj.obsolete_presents_computed = False
                continue
            obsoleteFlag = False
            for bomLine in bomObj.bom_line_ids:
                if bomLine.product_id.engineering_state == "obsoleted":
                    obsoleteFlag = True
                    break
            bomObj.sudo().obsolete_presents = obsoleteFlag
            bomObj.sudo().obsolete_presents_computed = obsoleteFlag
            bomObj.sudo().write(
                {"obsolete_presents": obsoleteFlag}
            )  # don't remove this force write or
            # when form is opened the value is not updated

    @api.onchange("bom_line_ids")
    def onchangeBomLine(self):
        self._obsolete_compute()

    def action_wizard_compute_bom(self):
        return {
            "domain": [],
            "name": _("Bom Computation Type"),
            "view_type": "form",
            "view_mode": "form",
            "res_model": "plm.temporary_date_compute",
            "type": "ir.actions.act_window",
            "target": "new",
        }

    def showAllBomsToCompute(self):
        outLines = self._showAllBomsToCompute()
        return {
            "type": "ir.actions.act_window",
            "name": _("Product Engineering"),
            "view_type": "form",
            "view_mode": "list,form",
            "res_model": "mrp.bom",
            "domain": [("id", "in", outLines)],
        }

    def _showAllBomsToCompute(self):
        outLines = []

        def recursion(mrp_bom_ids):
            for bomBrws in mrp_bom_ids:
                for bomLineBrws in bomBrws.bom_line_ids:
                    templateBrws = bomLineBrws.product_id.product_tmpl_id
                    bomIds = self.getBomFromTemplate(templateBrws, "normal")
                    recursion(bomIds)
                    if not templateBrws:
                        logging.warning(
                            "Product %s is not related to a product template."
                            % (bomLineBrws.product_id.id)
                        )
                        continue
                    if templateBrws.engineering_state == "obsoleted":
                        outLines.append(bomBrws.id)

        recursion(self)
        return list(set(outLines))

    def getBomFromTemplate(self, prodTmplBrws, bomType):
        """
        Return bom object from product template and bom type
        """
        return self.search(
            [("product_tmpl_id", "=", prodTmplBrws.id), ("type", "=", bomType)]
        )

    @api.model_create_multi
    def create(self, vals):
        """
        This overload of create is needed to setup obsolete_presents_recursive flag
        """

        def recursion(bomBrws):
            for lineBrws in bomBrws.bom_line_ids:
                prodBrws = lineBrws.product_id
                for bomBrwsChild in prodBrws.product_tmpl_id.bom_ids:
                    if bomBrwsChild.type == bomType:
                        if bomBrwsChild.obsolete_presents:
                            return True
                        if recursion(bomBrwsChild):
                            return True

        res = super(mrp_bom_extension_data, self).create(vals)
        for r in res:
            bomType = r.type
            if bomType != "ebom":
                if recursion(r):
                    r.obsolete_presents_recursive = True
                r._obsolete_compute()
        return res

    def write(self, vals):
        res = super(mrp_bom_extension_data, self).write(vals)
        bom_line_ids = vals.get("bom_line_ids", [])
        for bom_id in self:
            if bom_id.type != "ebom":
                if bom_line_ids:
                    beforeObsolete = bom_id.obsolete_presents
                    beforeObsoleteRecursive = bom_id.obsolete_presents_recursive

                    obsoleteRecursive = False
                    for lineBrws in bom_id.bom_line_ids:
                        prodBrws = lineBrws.product_id
                        for bomBrws in prodBrws.product_tmpl_id.bom_ids:
                            obs_p_recs = bomBrws.obsolete_presents_recursive
                            obs_pres = bomBrws.obsolete_presents
                            if bomBrws.type == bom_id.type:
                                obsoleteRecursive = obs_p_recs or obs_pres
                                break
                        if obsoleteRecursive:
                            break
                    bom_id.obsolete_presents_recursive = obsoleteRecursive
                    bom_id._obsolete_compute()

                    productBrws = bom_id.product_tmpl_id.product_variant_ids[0]
                    bom_abs_p_recs = bom_id.obsolete_presents_recursive

                    if (not beforeObsolete and bom_id.obsolete_presents) or (
                        not beforeObsoleteRecursive and bom_abs_p_recs
                    ):
                        # I added obsoleted at first level or added a line containing
                        # recursive obsoleted --> Need to update where used
                        self.updateWhereUsed(productBrws, True)
                    elif (beforeObsolete and not bom_id.obsolete_presents) or (
                        beforeObsoleteRecursive and not bom_abs_p_recs
                    ):
                        # I removed all obsoleted at first or other
                        # sublevels --> Need to update where used
                        bom_id.updateWhereUsed(productBrws, False)
        return res

    def updateWhereUsed(self, prodBrws, defaultUpdate=False):
        bomTmpl = self.env["mrp.bom"]
        struct = prodBrws.getParentBomStructure()

        def recursion(struct2, cleanObsoleteRecursive=True):
            for vals, parentsList in struct2:
                bom_id = vals.get("bom_id", False)
                if bom_id:
                    bomBrws = bomTmpl.browse(bom_id)
                    bomBrws._obsolete_compute()
                    if cleanObsoleteRecursive:
                        bomBrws.obsolete_presents_recursive = defaultUpdate
                    if bomBrws.obsolete_presents:
                        # I cannot change obsolete_recursive flag if there are other
                        # obsolete products in the parent BOM
                        cleanObsoleteRecursive = False
                recursion(parentsList, cleanObsoleteRecursive)

        recursion(struct)
