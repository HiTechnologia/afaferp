import logging
import datetime
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
from odoo.exceptions import UserError
from datetime import timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class ProductTemporaryNormalBom(models.TransientModel):
    _inherit = "plm.temporary"


    def action_create_normalBom(self):
        """
            Create a new Normal Bom if doesn't exist (action callable from views)
        """
        for obj_brws in self:
            migrate_custom_lines = obj_brws.migrate_custom_lines
            selected_ids = obj_brws.env.context.get('active_ids', [])
            obj_type = obj_brws.env.context.get('active_model', '')
            if obj_type != 'product.product':
                raise UserError(_("The creation of the normalBom works only on product_product object"))
            if not selected_ids:
                raise UserError(_("Select a product before to continue"))
            obj_type = obj_brws.env.context.get('active_model', False)
            product_product_type_object = obj_brws.env[obj_type]
            for product_browse in product_product_type_object.browse(selected_ids):
                id_template = product_browse.product_tmpl_id.id
                obj_boms = obj_brws.env['mrp.bom'].search([('product_tmpl_id', '=', id_template),
                                                           ('type', '=', 'normal')])
                if obj_boms:
                    raise UserError(_("Normal BoM for Part '%s' and revision '%s' already exists." % (obj_boms.product_tmpl_id.engineering_code, obj_boms.product_tmpl_id.engineering_revision)))
                line_messages_list = product_product_type_object.create_bom_from_ebom(
                    product_browse, 'normal',
                    obj_brws.summarize,
                    migrate_custom_lines
                )
                if line_messages_list:
                    out_mess = ''
                    for mess in line_messages_list:
                        out_mess = out_mess + '\n' + mess
                    t_mess_obj = obj_brws.env["plm.temporary.message"]
                    t_mess_id = t_mess_obj.create({'name': out_mess})
                    return {
                        'name': _('Result'),
                        'view_type': 'form',
                        "view_mode": 'form',
                        'res_model': "plm.temporary.message",
                        'res_id': t_mess_id.id,
                        'type': 'ir.actions.act_window',
                        'target': 'new',
                    }
        return {}