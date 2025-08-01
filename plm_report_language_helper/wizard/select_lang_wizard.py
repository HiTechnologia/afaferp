import base64
import logging
from email.policy import default

from odoo import (_, 
                  fields, 
                  models)
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


#  ************************** SPARE REPORTS *****************
class plm_spareChoseLanguage(models.TransientModel):
    _name = "plm.sparechoselanguage"
    _description = ("Module for extending the functionality of printing"
                    "spare_bom reports in a multi language environment")


    def getInstalledLanguage(self):
        """
        get installed language
        """
        out = []
        modobj = self.env["res.lang"]
        for objBrowse in modobj.search([]):
            out.append((objBrowse.code, objBrowse.name))
        return out

    lang = fields.Selection(getInstalledLanguage, "Language", required=True)
    onelevel = fields.Boolean(
        string="One Level",
        default=False,
        help="If you check this box, the report will be made in one level"
    )
    datas = fields.Binary("Download", readonly=True)
    datas_name = fields.Char("Download file name ", size=255, readonly=True)

    def print_report(self):
        self.ensure_one()
        lang = self.lang
        if lang:
            modobj = self.env["ir.module.module"]
            mids = modobj.search([("state", "=", "installed")])
            if not mids:
                raise UserError("Language not Installed")
            reportName = "report.plm_spare.pdf_all"
            # 'plm_spare.report_product_product_spare_parts_pdf'
            if self.onelevel:
                reportName = "report.plm_spare.pdf_one"
                # 'plm_spare.report_product_product_spare_parts_pdf_one'
            productProductId = self.env.context.get("active_id")
            newContext = self.env.context.copy()
            newContext["lang"] = lang
            newContext["force_report_rendering"] = True

            tProductProduct = self.env["product.product"]
            brwProduct = tProductProduct.browse(productProductId)
            report_context = self.env[reportName].sudo().with_context(newContext)
            stream = report_context._create_spare_pdf(brwProduct)
            self.datas = base64.encodebytes(stream)
            fileName = brwProduct.name + "_" + lang + "_manual.pdf"
            self.datas_name = fileName
            return {
                "context": self.env.context,
                "view_type": "form",
                "view_mode": "form",
                "res_model": plm_spareChoseLanguage._name,
                "res_id": self.id,
                "view_id": False,
                "type": "ir.actions.act_window",
                "target": "new",
            }
        UserError(_("Select a language"))


#  ************************** BOM REPORTS *****************

AVAILABLE_REPORT = [
    ("plm.report_plm_bom_structure_all", "BOM All Levels"),
    ("plm.report_plm_bom_structure_one", "BOM One Level"),
    ("plm.report_plm_bom_structure_all_sum", "BOM All Levels Summarized"),
    ("plm.report_plm_bom_structure_one_sum", "BOM One Level Summarized"),
    ("plm.report_plm_bom_structure_leaves", "BOM Only Leaves Summarized"),
    ("plm.report_plm_bom_structure_flat", "BOM All Flat Summarized"),
]


class plm_bomChoseLanguage(models.TransientModel):
    _name = "plm.bomchoselanguage"
    _description = ("Module for extending the functionality of printing bom reports"
                    "in a multi language environment")

    def getInstalledLanguage(self):
        """
        get installed language
        """
        out = []
        modobj = self.env["res.lang"]
        for objBrowse in modobj.search([]):
            out.append((objBrowse.code, objBrowse.name))
        return out

    def print_report(self):
        self.ensure_one()
        lang = self.lang
        if lang:
            modobj = self.env["ir.module.module"]
            mids = modobj.search([("state", "=", "installed")])
            if not mids:
                raise UserError("Language not Installed")
            reportName = self.bom_type
            newContext = self.env.context.copy()  # Used to update and generate pdf
            newContext["lang"] = lang
            newContext["force_report_rendering"] = True
            bomId = self.env.context.get("active_id")
            stream, fileExtention = (
                self.env.ref(reportName)
                .sudo()
                .with_context(newContext)
                ._render_qweb_pdf(reportName, bomId)
            )
            self.datas = base64.b64encode(stream)
            tMrpBom = self.env["mrp.bom"]
            brwProduct = tMrpBom.browse(bomId)
            fileName = (
                brwProduct.product_tmpl_id.name + "_" + lang + "_bom." + fileExtention
            )
            self.datas_name = fileName
            return {
                "context": self.env.context,
                "view_type": "form",
                "view_mode": "form",
                "res_model": plm_bomChoseLanguage._name,
                "res_id": self.id,
                "view_id": False,
                "type": "ir.actions.act_window",
                "target": "new",
            }
        raise UserError(_("Select a language"))

    lang = fields.Selection(getInstalledLanguage, "Language", required=True)

    bom_type = fields.Selection(
        AVAILABLE_REPORT,
        _("Bom Report Type"),
        required=True,
        help=_("Chose the Bom report you would like to print"),
    )

    datas = fields.Binary("Download", readonly=True)

    datas_name = fields.Char("Download file name ", 
                             size=255, 
                             readonly=True)
    _defaults = {"bom_type": False}
