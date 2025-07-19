import requests
import json
import logging

from ast import literal_eval
from datetime import datetime, timedelta
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError, AccessError

_logger = logging.getLogger(__name__)

class WizardTraccarDeviceSummary(models.TransientModel):
    _name = "wizard.traccar.device.summary"
    _description = "Traccar Device Summary Wizard"

    name = fields.Char(string="Name")
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle', domain="[('is_traccar', '=', True)]")
    device_id = fields.Char(string='Device ID', help="Device ID")
    from_date = fields.Datetime(string='Date From', required=True, default=fields.Datetime.now, help="Date starting range for filter")
    to_date = fields.Datetime(string='Date To', required=True, default=fields.Datetime.now, help="Date end range for filter")
    
    @api.onchange('to_date','from_date')
    def onchange_date(self):
        if self.from_date and self.to_date and self.to_date < self.from_date:
            raise UserError(_('End date must be greater than start date.'))

    def create_summary(self, summary_data):
        if len(summary_data) > 0:
            details = False
            for summary in summary_data:
                if not summary.get('deviceId', ''):
                    continue
                data = {}
                startTime = "".join(summary.get('startTime', '').split(".")[:-1])
                endTime = "".join(summary.get('endTime', '').split(".")[:-1])

                data['name'] = "Traccar Device Summary Details"
                data['device_id'] = summary.get('deviceId', '')
                data['distance'] = summary.get('distance', '')
                data['average_speed'] = summary.get('averageSpeed', '')
                data['max_speed'] = summary.get('maxSpeed', '')
                data['spent_fuel'] = summary.get('spentFuel', '')
                data['start_odometer'] = summary.get('startOdometer', '')
                data['end_odometer'] = summary.get('endOdometer', '')
                data['start_time'] = datetime.strptime(startTime, "%Y-%m-%dT%H:%M:%S")
                data['end_time'] = datetime.strptime(endTime, "%Y-%m-%dT%H:%M:%S")
                data['engine_hours'] = summary.get('engineHours', '')

                details = self.env['details.traccar.device.summary'].create(data)
            return details
        else:
            return False

    def open_device_summary(self):
        config = self.env['traccar.config.settings'].sudo().search([('active', '=', True)], limit=1)
        to_date = self.to_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        from_date = self.from_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        device_id = self.device_id
        if device_id:
            try:                
                url = "{}/api/reports/summary?deviceId={}&from={}&to={}".format(config.api_url, device_id, from_date, to_date)

                headers = {
                    'Accept' : 'application/json'
                }
                response = requests.get(url, auth=(config.api_user, config.api_pwd), headers=headers)
                if response.status_code == 200:
                    summary_data = response.json()               
                    details = self.create_summary(summary_data)
                    if details:
                        form_id = self.env.ref('fleet_traccar_tracking.form_details_traccar_device_summary').id
                        return {
                            'name': ("View Device Summary Details"),
                            'type': 'ir.actions.act_window',
                            'res_model': 'details.traccar.device.summary',
                            'view_mode': 'form',
                            'views': [(form_id, 'form')],
                            'res_id': int(details.id),
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

class DetailsTraccarDeviceSummary(models.TransientModel):
    _name = "details.traccar.device.summary"
    _description = "Traccar Device Summary Details"

    name = fields.Char("Name")
    device_id = fields.Char(string='Device ID', help="Device ID")
    average_speed = fields.Float('Average Speed')
    max_speed = fields.Float('Max Speed')
    distance = fields.Float(string='Distance')    
    spent_fuel = fields.Float('Spent Fuel')
    start_odometer = fields.Float('Start Odometer')
    end_odometer = fields.Float('End Odometer')
    start_time = fields.Datetime(string='Start Time')
    end_time = fields.Datetime(string='End Time')
    engine_hours = fields.Float('Engine Hours')