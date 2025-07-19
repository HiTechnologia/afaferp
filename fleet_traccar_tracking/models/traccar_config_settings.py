import requests
import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError, AccessError

_logger = logging.getLogger(__name__)

class TraccarConfigSettings(models.Model):
    _name = "traccar.config.settings"
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(string='Reference', required=True, index='trigram', copy=False, default='New')
    api_url = fields.Char(string='URL', track_visibility="onchange", required=True)
    api_user = fields.Char(string='User Name', track_visibility="onchange", required=True)
    api_pwd = fields.Char(string='Password', track_visibility="onchange", required=True, size=100)
    active = fields.Boolean(string="Active", track_visibility="onchange", default=True)
    authentication_status = fields.Boolean(string="Authentication Status", default=False)
    create_date = fields.Datetime(string='Created Date')

    @api.constrains('active')
    def _check_is_selected(self):
        active = self.env['traccar.config.settings'].search_count([('active', '=', True)])
        if active > 1:
            raise ValidationError("Active configuration is already here!")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _("New")) == _("New"):
                seq_date = fields.Datetime.context_timestamp(
                    self, fields.Datetime.to_datetime(vals['date_order'])
                ) if 'date_order' in vals else None
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'traccar.config.settings', sequence_date=seq_date) or _("New")
        return super().create(vals_list)

    
    def check_connection(self):
        try:
            data = {
                'email': self.api_user, 
                'password': self.api_pwd
            }
            response = requests.Session().post(self.api_url + "/api/session", data=data)
            if response.status_code == 200:
                self.authentication_status = True
                title = 'Success'
                message = 'Test Connection with Traccar is successful, now you can proceed with synchronization.'
                return self.env['raise.message'].raise_message(message, title)
            elif response.status_code == 401:
                self.authentication_status = False
                title = 'Error'
                message = _('Traccar Unauthorized Access: Check traccar credentials %s') % (response.text)
                return self.env['raise.message'].raise_message(message, title)
            else :
                self.authentication_status = False
                title = 'Error'
                message = _('Traccar Unauthorized Access: Check traccar credentials %s') % (response.text)
                return self.env['raise.message'].raise_message(message, title)
        except Exception as e:
            self.authentication_status = False
            title = 'Error'
            message = _('Error: %s') % (e)
            return self.env['raise.message'].raise_message(message, title)

    def fetch_devices_info(self, uniqueId=False):
        config = self.env['traccar.config.settings'].sudo().search([('active', '=', True)], limit=1)
        device = []
        if config:
            url = config.api_url + "/api/devices"
            if uniqueId:
                url = "{}?uniqueId={}".format(url, str(uniqueId))
            try:
                headers = {
                    'Content-Type' : 'application/json'
                }
                response = requests.get(url, auth=(config.api_user, config.api_pwd), headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    for d in data:
                        vals = {
                            'id' : d.get('id') if 'id' in d else 0,
                            'status': d.get('status') if 'status' in d else 'offline',
                            'lastUpdate': d.get('lastUpdate') if 'lastUpdate' in d else '',
                        }
                        device.append(vals)
            except Exception as e:
                pass
        return device

    def create_device_info(self, data):
        config = self.env['traccar.config.settings'].sudo().search([('active', '=', True)], limit=1)
        device = None
        if config:
            try:
                url = config.api_url + "/api/devices"
                headers = {
                    'Content-Type' : 'application/json'
                }
                timeout = 1.000
                data = json.dumps(data)
                response = requests.post(url, auth=(config.api_user, config.api_pwd), data=data, headers=headers, timeout=timeout)
                if response.status_code == 200:
                    data = response.json()
                    if 'id' in data:
                        device = data.get('id')
            except Exception as e:
                pass
        return device
