from odoo import models
import logging
logger = logging.getLogger(__name__)


class AccountInvoiceMarkSent(models.TransientModel):
    _name = 'account.invoice.mark.sent'
    _description = 'Mark invoices as sent'

    def run(self):
        assert self.env.context.get('active_model') == 'account.move', \
            'Source model must be invoices'
        assert self.env.context.get('active_ids'), 'No invoices selected'
        invoices = self.env['account.move'].search([
            ('id', 'in', self.env.context.get('active_ids')),
            ('move_type', 'in', ('out_invoice', 'out_refund')),
            ('state', '=', 'posted')])
        invoices.write({'is_move_sent': True})
        logger.info('Marking invoices with ID %s as sent', invoices.ids)
        return
