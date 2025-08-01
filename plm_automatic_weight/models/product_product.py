import logging

from odoo import _, api, fields, models
from odoo.addons.plm.models.plm_mixin import (
    RELEASED_STATUS, OBSOLATED_STATUS, START_STATUS, CONFIRMED_STATUS
)

_logger = logging.getLogger(__name__)


class PlmComponent(models.Model):
    _name = 'product.product'
    _inherit = 'product.product'

    automatic_compute_selection = fields.Selection(
        [('use_net', _('Use Net Weight')),
         ('use_cad', _('Use CAD Weight')),
         ('use_normal_bom', _('Use Normal Bom'))],
        _('Weight compute mode'),
        default='use_net',
        help=_(
            """Set "Use Net Weight" to use only gross weight. \n
               Set "Use CAD Weight" to use CAD weight + Additional Weight
               as gross weight. \n
               Set "Use Normal Bom" to use NBOM Weight Computed + Additional weight
               as gross weight.""")
    )
    weight_additional = fields.Float(_('Additional Weight'), digits='Stock Weight')
    weight_cad = fields.Float(_('CAD Weight'), readonly=True, digits='Stock Weight')
    weight_n_bom_computed = fields.Float(
        _('NBOM Weight Computed'),
         compute="compute_bom_weight",
         readonly=True,
         digits='Stock Weight', default=0
    )

    @api.model_create_multi
    def create(self, vals):
        """
            Creating a product weight is set equal to weight_net and vice-versa
        """
        if 'automatic_compute_selection' in vals:
            if vals['automatic_compute_selection'] == 'use_cad':
                vals['weight'] = vals.get('weight_cad', 0) + vals.get(
                    'weight_additional'
                )
            elif vals['automatic_compute_selection'] == 'use_normal_bom':
                vals['weight'] = vals.get('weight_additional')
        return super(PlmComponent, self).create(vals)

    @property
    def weight_allowed_state(self):
        return [START_STATUS, CONFIRMED_STATUS]

    def write(self, vals):
        for product_id in self:
            eng_state = product_id.engineering_state
            if eng_state not in self.weight_allowed_state and not self.env.context.get(
                'plm_force_weight', False):
                if 'weight' in vals:
                    del vals['weight']
                    logging.info(
                        "Modification in status %s not allowed"
                        "for the weight" % eng_state)
            weight_additional = product_id.weight_additional
            if 'weight_additional' in vals:
                weight_additional = vals['weight_additional']
            if product_id.automatic_compute_selection == 'use_cad':
                weight_cad = product_id.weight_cad
                if 'weight_cad' in vals:
                    weight_cad = vals['weight_cad']
                vals['weight'] = weight_cad + weight_additional
            elif product_id.automatic_compute_selection == 'use_normal_bom':
                vals['weight'] = weight_additional + product_id.weight_n_bom_computed
            if 'weight' in vals and product_id.weight==vals['weight']:
                del vals['weight']
        res = super(PlmComponent, self).write(vals)
        if 'weight' in vals:
            for product_product_id in self:
                product_product_id.fix_parent()
        return res

    def fix_parent(self):
        for product_product_id in self:
            bom_id = product_product_id.getParentBom()
            if bom_id:
                bom_id.product_tmpl_id.product_variant_id.on_change_automatic_compute()

    @api.onchange('automatic_compute_selection', 'weight_cad',
                  'weight_additional', 'weight_n_bom_computed')
    def on_change_automatic_compute(self):
        """
            Compute weight due to selection choice
        """
        if self.automatic_compute_selection == 'use_cad':
            self.weight = self.weight_cad + self.weight_additional
        elif self.automatic_compute_selection == 'use_normal_bom':
            self.compute_bom_weight()
            self.weight = self.weight_additional + self.weight_n_bom_computed

    def compute_bom_weight(self):
        """
            - Compute first founded Normal Bom weight
            - Compute and set weight for all products and boms during computation
        """
        bom_obj = self.env['mrp.bom']
        for product_product_id in self:
            product_product_id.weight_n_bom_computed = 0.0
            product_tmpl_id = product_product_id.product_tmpl_id._origin.id
            for bom_id in bom_obj.search([
                ('type', '=', 'normal'),
                ('product_tmpl_id', '=', product_tmpl_id)
            ]):
                product_product_id.weight_n_bom_computed = bom_id.get_bom_child_weight()

    def common_weight_compute(self, product_product_id, is_user_admin, to_add=0.0):
        """
            Common compute and set weight in single product
        """

        def common_set(product_product_id):
            common_weight = False
            weight_additional = product_product_id.weight_additional
            if product_product_id.automatic_compute_selection == 'use_cad':
                common_weight = product_product_id.weight_cad + weight_additional
            elif product_product_id.automatic_compute_selection == 'use_normal_bom':
                common_weight = weight_additional + to_add
            if common_weight != False:
                product_product_id.write({'weight': common_weight})

        if product_product_id.engineering_state in [RELEASED_STATUS, OBSOLATED_STATUS]:
            if is_user_admin:
                common_set(product_product_id)
        else:
            common_set(product_product_id)

    def is_user_weight_admin(self):
        """
            Verify if logged user is a weight admin
        """
        group_brws = self.env['res.groups'].search([
            ('name', '=', 'PLM / Weight Admin')
        ])  # Same name must be used in data record file
        if group_brws:
            if self.env.user in group_brws.users:
                return True
        return False

    def compute_bom_weight_action(self):
        """
            Function called form xml action to compute and set weight for all selected
            products and boms
        """
        for prod_brws in self:
            prod_brws.on_change_automatic_compute()
