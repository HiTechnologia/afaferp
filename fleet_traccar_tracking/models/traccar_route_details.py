import requests
import json
import logging

from ast import literal_eval
from datetime import datetime, timedelta
from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

class TraccarRouteDetails(models.Model):
    _name = "traccar.route.details"
    _inherit = ['mail.thread']
    _description = "Route Details"
    _order = 'id desc'

    def _default_route_name(self):
        return self.env['ir.sequence'].next_by_code('traccar.route.details')

    name = fields.Char(string='Name', default=lambda self: self._default_route_name(), help="Sequence of Route")
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    driver_id = fields.Many2one(related="vehicle_id.driver_id", string="Driver", readonly=False)
    traccar_device_uniqueid = fields.Char(related="vehicle_id.traccar_device_uniqueid", string="Traccar Unique Id", readonly=False)
    route_date = fields.Date('Route Date', default=fields.Date.today, help='Route Date')

    route_id = fields.Integer('Travel ID')
    device_id = fields.Integer('Device ID')
    protocol = fields.Char(string='Protocol')

    src_latitude = fields.Char(string='Source Latitude', help="Source Latitude")
    src_longitude = fields.Char(string='Source Longitude', help="Source Longitude")
    dst_latitude = fields.Char(string='Destination Latitude', help="Destination Latitude")
    dst_longitude = fields.Char(string='Destination Longitude', help="Destination Longitude")

    altitude = fields.Char(string='Altitude')    
    speed = fields.Float('Speed')
    course = fields.Float('Cource')
    accuracy = fields.Float('Accuracy')
    
    battery_level = fields.Float('Battery Level')
    distance = fields.Float('Distance')
    total_distance = fields.Float('Total Distance')
    motion = fields.Float('Motion')
    device_time = fields.Datetime(string='Device Time')

    def write(self, vals):
        for obj in self:
            if not obj.name:
                vals['name'] = self.env['ir.sequence'].next_by_code('traccar.route.details')
        return super().write(vals)
    
    @api.model
    def create(self, vals):
        if not vals.get('name', False):
            vals['name'] = self.env['ir.sequence'].next_by_code('traccar.route.details')
        return super().create(vals)

    def create_route(self, route_data): 
        route_details_sudo = self.env['traccar.route.details'].sudo()
        fleet_vehicle_sudo = self.env['fleet.vehicle'].sudo()
        for route in route_data:
            data = {}           

            route_id = route.get('id', '')
            route_details = route_details_sudo.search([('route_id', '=', route_id)], limit=1, order="id desc")
            if route_details:
                continue

            device_id = route.get('deviceId', '')
            fleet_vehicle = fleet_vehicle_sudo.search([('traccar_device_id', '=', device_id)], limit=1)            
            if fleet_vehicle and fleet_vehicle.is_traccar:                
                data['vehicle_id'] = fleet_vehicle.id
            else:
                continue

            previous_route = route_details_sudo.search([('device_id', '=', device_id)], limit=1, order="id desc")
            protocol = route.get('protocol', '')
            src_longitude = previous_route.dst_longitude if previous_route else route.get('longitude', '')
            src_latitude = previous_route.dst_latitude if previous_route else route.get('latitude', '')
            dst_latitude = route.get('latitude', '')
            dst_longitude = route.get('longitude', '')
            altitude = route.get('altitude', '')
            speed = route.get('speed', '')
            course = route.get('course', '')
            accuracy = route.get('accuracy', '')
            battery_level = route.get('attributes', {}).get('batteryLevel', 0.0)
            distance = route.get('attributes', {}).get('distance', '')
            total_distance = route.get('attributes', {}).get('totalDistance', '')
            motion = route.get('motion', '')                                    
            deviceTime = "".join(route.get('deviceTime', '').split(".")[:-1])
                        
            data['route_id'] = route_id
            data['device_id'] = device_id
            data['protocol'] = protocol
            
            data['src_longitude'] = src_longitude
            data['src_latitude'] = src_latitude
            data['dst_longitude'] = dst_longitude
            data['dst_latitude'] = dst_latitude

            data['altitude'] = altitude
            data['speed'] = speed
            data['course'] = course
            data['accuracy'] = accuracy

            data['battery_level'] = battery_level
            data['distance'] = distance
            data['total_distance'] = total_distance
            data['motion'] = motion
            
            data['device_time'] = datetime.strptime(deviceTime, "%Y-%m-%dT%H:%M:%S")

            self.create(data)

    def cron_update_route_details(self, to_date=False, from_date=False):
        format = "%Y-%m-%dT%H:%M:%SZ"
        if not to_date:
            to_date = datetime.now().strftime(format)
        if not from_date:
            from_date = (fields.Datetime.from_string(datetime.now()) - timedelta(minutes=15)).strftime(format)

        config = self.env['traccar.config.settings'].sudo().search([('active', '=', True)], limit=1)       
        devices = config.fetch_devices_info()

        if devices:
            try:
                for device in devices:
                    url = "{}/api/reports/route?deviceId={}&from={}&to={}".format(config.api_url, device['id'], from_date, to_date)
                    payload={}
                    headers = {
                        'Accept': 'application/json',
                    }
                    response = requests.get(url, auth=(config.api_user, config.api_pwd), headers=headers, data=payload)
                    if response.status_code == 200:
                        route_data = response.json()
                        self.create_route(route_data)                        
                    elif response.status_code == 401:
                        _logger.info(('Traccar Unauthorized Access: Check traccar credentials %s') % response.text)
                    else :
                        _logger.info(('Traccar Connection Error: %s') % response.text)
            except Exception as e:
                _logger.info(('Error! Traccar Connection Error: %r') % e)
        else:
            _logger.info('Error! Update Sync Information was conducted, but no devices were found.')
        return True
