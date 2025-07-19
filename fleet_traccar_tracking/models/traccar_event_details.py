import requests
import json
import logging

from ast import literal_eval
from datetime import datetime, timedelta
from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

class TraccarEventDetails(models.Model):
    _name = "traccar.event.details"
    _inherit = ['mail.thread']
    _description = "Event Details"
    _order = 'id desc'

    def _default_event_name(self):
        return self.env['ir.sequence'].next_by_code('traccar.event.details')

    name = fields.Char(string='Name', default=lambda self: self._default_event_name(), help="Sequence of Event")
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    driver_id = fields.Many2one(related="vehicle_id.driver_id", string="Driver", readonly=False)
    traccar_device_uniqueid = fields.Char(related="vehicle_id.traccar_device_uniqueid", string="Traccar Unique Id", readonly=False)
    event_date = fields.Date('Event Date', default=fields.Date.today, help='Event Date')

    event_id = fields.Integer(string='Event ID')
    device_id = fields.Integer(string='Device ID')
    device_type = fields.Char(string='type')
    event_time = fields.Datetime(string='Device Time')
    position_id = fields.Integer(string='Position ID')
    geofence_id = fields.Integer(string='Geofence ID')
    maintenance_id = fields.Integer(string='Maintenance ID')

    def write(self, vals):
        for obj in self:
            if not obj.name:
                vals['name'] = self.env['ir.sequence'].next_by_code('traccar.event.details')
        return super().write(vals)
    
    @api.model
    def create(self, vals):
        if not vals.get('name', False):
            vals['name'] = self.env['ir.sequence'].next_by_code('traccar.event.details')
        return super().create(vals)

    def create_event(self, event_data): 
        event_details_sudo = self.env['traccar.event.details'].sudo()
        fleet_vehicle_sudo = self.env['fleet.vehicle'].sudo()
        for event in event_data:
            data = {}           

            event_id = event.get('id', '')
            event_details = event_details_sudo.search([('event_id', '=', event_id)], limit=1, order="id desc")
            if event_details:
                continue
                
            device_id = event.get('deviceId', '')
            fleet_vehicle = fleet_vehicle_sudo.search([('traccar_device_id', '=', device_id)], limit=1)            
            if fleet_vehicle and fleet_vehicle.is_traccar:                
                data['vehicle_id'] = fleet_vehicle.id
            else:
                continue

            eventTime = "".join(event.get('eventTime', '').split(".")[:-1])
            data['event_id'] = event_id
            data['device_id'] = device_id            
            data['device_type'] = event.get('type', '')
            data['event_time'] = datetime.strptime(eventTime, "%Y-%m-%dT%H:%M:%S")
            data['position_id'] = event.get('positionId', '')
            data['geofence_id'] = event.get('geofenceId', '')
            data['maintenance_id'] = event.get('geofenceId', '')

            self.create(data)

    def cron_update_event_details(self, to_date=False, from_date=False):
        format = "%Y-%m-%dT%H:%M:%SZ"
        if not to_date:
            to_date = datetime.now().strftime(format)
        if not from_date:
            from_date = (fields.Datetime.from_string(datetime.now()) - timedelta(minutes=15)).strftime(format)

        config = self.env['traccar.config.settings'].sudo().search([('active', '=', True)], limit=1)
        devices = config.fetch_devices_info()

        try:
            for device in devices:
                url = "{}/api/reports/events?deviceId={}&from={}&to={}".format(config.api_url, device['id'], from_date, to_date)
                payload={}
                headers = {
                    'Accept': 'application/json',
                }
                response = requests.get(url, auth=(config.api_user, config.api_pwd), headers=headers, data=payload)
                if response.status_code == 200:
                    event_data = response.json()
                    self.create_event(event_data)                        
                elif response.status_code == 401:
                    _logger.info(('Traccar Unauthorized Access: Check traccar credentials %s') % response.text)
                else :
                    _logger.info(('Traccar Connection Error: %s') % response.text)
        except Exception as e:
            _logger.info(('Error! Traccar Connection Error: %r') % e)
        return True
