import requests
import json
import logging

from ast import literal_eval
from datetime import datetime, timedelta
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError, AccessError

_logger = logging.getLogger(__name__)

class WizardTraccarDeviceLocation(models.TransientModel):
    _name = "wizard.traccar.device.location"
    _description = "Traccar Device location Wizard"

    name = fields.Char(string="Name")
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle', domain="[('is_traccar', '=', True)]")
    device_id = fields.Char(string='Device ID', help="Device ID")
    
    @api.onchange('to_date','from_date')
    def onchange_date(self):
        if self.from_date and self.to_date and self.to_date < self.from_date:
            raise UserError(_('End date must be greater than start date.'))

    def create_location(self, location_data):
        if len(location_data) > 0:
            locations = False
            for location in location_data:
                if not location.get('id', ''):
                    continue
                data = {}

                data['name'] = "Traccar Device location Details"
                data['latitude'] = location.get('latitude', '')
                data['longitude'] = location.get('longitude', '')

                locations = self.env['wizard.traccar.current.position'].create(data)
            return locations
        else:
            return False

    def open_device_location(self):
        config = self.env['traccar.config.settings'].sudo().search([('active', '=', True)], limit=1)
        format = "%Y-%m-%dT%H:%M:%SZ"
        to_date = datetime.now().strftime(format)
        from_date = (fields.Datetime.from_string(datetime.now()) - timedelta(minutes=5)).strftime(format)
        device_id = self.device_id
        if device_id:
            try:                
                url = "{}/api/positions?deviceId={}&from={}&to={}".format(config.api_url, device_id, from_date, to_date)

                headers = {
                    'Accept' : 'application/json'
                }
                response = requests.get(url, auth=(config.api_user, config.api_pwd), headers=headers)
                if response.status_code == 200:
                    location_data = response.json()         
                    locations = self.create_location(location_data)
                    if locations:
                        form_id = self.env.ref('fleet_traccar_tracking.form_details_traccar_current_position').id
                        return {
                            'name': ("View Device Current Position"),
                            'type': 'ir.actions.act_window',
                            'res_model': 'wizard.traccar.current.position',
                            'view_mode': 'form',
                            'views': [(form_id, 'form')],
                            'res_id': int(locations.id),
                            'target': 'new',
                        }
                    else:
                        title = 'Message'
                        message = _('No data are avilable between this date')
                        return self.env['raise.message'].raise_message(message, title)
                elif response.status_code == 401:
                    _logger.info(('Traccar Unauthorized Access: Check traccar credentials %s') % response.text)
                else :
                    _logger.info(('Traccar Connection Error: %s') % response.text)
            except Exception as e:
                _logger.info(('Error! Traccar Connection Error: %r') % e)
        else:
            _logger.info('Error! While running update sync information, no devices were discovered.')
        return True


class WizardTraccarCurretPosition(models.TransientModel):
    _name = "wizard.traccar.current.position"
    _description = "Traccar Device Current Position"

    name = fields.Char(string="Name")
    latitude = fields.Char(string='Latitude', help="Latitude")
    longitude = fields.Char(string='Longitude', help="Longitude")