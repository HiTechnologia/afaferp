# -*- coding: utf-8 -*-
from odoo import fields, models, _


class AssetDepreciationConfirmationWizard(models.TransientModel):
    _name = "asset.depreciation.confirmation"
    _description = "Asset Depreciation Confirmation"

    date = fields.Date('Account Date', required=True,
                       help="Choose the period for which you want to automatically "
                            "post the depreciation lines of running assets",
                       default=fields.Date.context_today)

    def asset_compute(self):
        self.ensure_one()
        context = self._context
        created_move_ids = self.env['account.asset.asset'].sudo().compute_generated_entries(self.date, asset_type=context.get('asset_type'))
        return {
            'name': _('Created Asset Moves') if context.get('asset_type') == 'purchase' else _('Created Revenue Moves'),
            'view_mode': 'list,form',
            'res_model': 'account.move',
            'view_id': False,
            'domain': "[('id','in',[" + ','.join(str(id) for id in created_move_ids) + "])]",
            'type': 'ir.actions.act_window',
        }
