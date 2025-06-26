import logging

from odoo import api, models
from odoo.addons.plm.models.plm_mixin import RELEASED_STATUS


class ProdProdExtension(models.Model):
    _inherit = 'product.product'

    @api.model
    def generateAutomatedNBoms(self, force_products=False):
        '''
            Generate all normal boms starting from released components.
        '''
        errors = []
        mrpBomObj = self.env['mrp.bom']
        releasedComponents = self.env['product.product']
        if force_products:
            releasedComponents = force_products
        else:
            releasedComponents = self.search([
                ('engineering_state', '=', RELEASED_STATUS)
            ])
        logging.info(
            '[Automate Nbom scheduler started] found %s components'
            % (len(releasedComponents.ids))
        )
        for prodBrws in releasedComponents:
            try:
                bomBrwsList = mrpBomObj.search([
                    ('product_id', '=', prodBrws.id),
                    ('type', '=', 'normal')
                ])
                if not bomBrwsList:
                    engBoms = mrpBomObj.search([
                        ('product_id', '=', prodBrws.id),
                        ('type', '=', 'ebom')
                    ])

                    if engBoms:

                        prodBrws.action_create_normalBom_WF()
                        logging.info(
                            'Created Normal bom of %s component on %s' % (
                                releasedComponents.ids.index(prodBrws.id),
                                len(releasedComponents.ids)
                            )
                        )
            except Exception as ex:
                errors.append(ex)
        logging.info('[Automate Nbom scheduler ended]')
        if errors:
            logging.warning(
                '[Automate Nbom scheduler errors]'
                'some errors are found during normal bom computation.'
            )
        for error in errors:
            logging.warning(error)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
