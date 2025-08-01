
from odoo import models
from odoo import fields
from odoo import api
from odoo import _


class PlmConfigSettings(models.TransientModel):
    _name = 'res.config.settings'
    _inherit = 'res.config.settings'

    module_plm_automate_normal_bom = fields.Boolean(
        _("Allow to create normal BOM if not exists and product are released."))
    module_plm_automatic_weight = fields.Boolean(_("Automatic weight calculation"))
    module_plm_compare_bom = fields.Boolean(_("Compare two BOM tool"))
    module_plm_cutted_parts = fields.Boolean(_("Manage BOM explosion for cut parts"))
    module_plm_date_bom = fields.Boolean(_("Manage BOM due to date"))
    module_plm_engineering = fields.Boolean(_("Allow to use engineering BOM"))
    module_plm_pack_and_go = fields.Boolean(_("Pack and go"))
    module_plm_product_description_language_helper = fields.Boolean(_("Product Description Language Helper"))
    module_plm_report_language_helper = fields.Boolean(_("Manage more Language PLM reports"))
    module_plm_spare = fields.Boolean(_("Manage spare BOM and Spare Parts Manual"))
    module_plm_web_revision = fields.Boolean(_("Create new revision from WEB"))
    module_plm_auto_internalref = fields.Boolean("Populate internal reference with engineering part number")
    module_plm_automated_convertion = fields.Boolean("Activate the server conversion tool")
    module_plm_project = fields.Boolean("Activate the PLM Project connection")
    module_plm_client_customprocedure = fields.Boolean("Activate the PLM Client mapping")
    module_plm_box = fields.Boolean("PLM Box")
    module_plm_suspended = fields.Boolean("Manage Product suspend code")
    module_plm_auto_engcode = fields.Boolean("Enable Automatic Engineering Code")
    module_plm_bom_summarize = fields.Boolean("Enable B.O.M. summarisation during the client upload")
    module_activity_validation = fields.Boolean("Enable Eco /Ecr")
    module_plm_web_3d = fields.Boolean("Enable 3D WebGl")
    module_plm_web_3d_sale = fields.Boolean("Enable 3D WebGl for e-commerce and sale")
    module_plm_breakages = fields.Boolean("Enable breakages management")
    module_plm_ent_breakages_helpdesk = fields.Boolean("Enable breakages management on Helpdesk (Enterprise only)")
    module_plm_pdf_workorder = fields.Boolean("Enable Plm PDF document inside workorder")
    module_plm_sale_fix = fields.Boolean("Add plm groups permission to sale")
    module_plm_document_multi_site = fields.Boolean("Multi server storage system")
    module_plm_mrp_bom_update = fields.Boolean("MRP B.O.M Update")
    module_plm_product_only_latest = fields.Boolean("Force last version on Manufacturing")
    module_plm_purchase_only_latest = fields.Boolean("Force last version on purchase")
    module_plm_sale_only_latest = fields.Boolean("Force last version on Sale")
    module_plm_workflow_custom_action = fields.Boolean("Automatic workFlow actions")

    install_consumption_plan_feature = fields.Boolean(
        string="Enable Consumption Plan Feature",
        config_parameter="plm.install_consumption_plan_feature"
    )

    @api.model
    def get_values(self):
        res = super().get_values()
        module_installed = self.env['ir.module.module'].sudo().search([
            ('name', '=', 'plm_consumption_plans'),
            ('state', '=', 'installed')
        ], limit=1)
        res.update({
            'install_consumption_plan_feature': bool(module_installed),
        })
        return res

    def set_values(self):
        super().set_values()
        module_model = self.env['ir.module.module'].sudo()
        module_record = module_model.search([('name', '=', 'plm_consumption_plans')], limit=1)

        if self.install_consumption_plan_feature:
            if module_record.state != 'installed':
                module_record.button_immediate_install()
        else:
            if module_record.state == 'installed':
                module_record.button_immediate_uninstall()

