from odoo import models


class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    def action_open_workorder_kanban(self):
        view_id = self.env["ir.model.data"]._xmlid_to_res_id(
            "plm.document_kanban_view"
        )
        ctx = self.env.context.copy()
        domain = [('is_plm', '=', True),
                  ('is_production_doc', '=', True),
                  ('id', 'in', self.production_doc_ids.ids)]
        ctx.update({
            "create": False,
            "delete": False,
            'default_res_ids': self.production_doc_ids.ids,
            'readonly': True
        })

        return {
            "type": "ir.actions.act_window",
            "view_type": "kanban",
            "view_mode": "kanban",
            'domain': domain,
            "res_model": "ir.attachment",
            "target": "new",
            "views": [[view_id, "kanban"]],
            "context": ctx,
        }
