from odoo import api, fields, models, _

class RaiseMessage(models.TransientModel):
	_name = "raise.message"
	_description = "Raise Message"

	message = fields.Text(string='Message')

	@api.model
	def raise_message(self, message, title):
		res = self.sudo().create({'message': message})
		return {
			'name'     : title or 'Message',
			'type'     : 'ir.actions.act_window',
			'res_model': 'raise.message',
			'view_mode': 'form',
			'res_id'   : res.id,
			'target'   : 'new',
		}
