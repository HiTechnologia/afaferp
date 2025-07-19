import requests
import json
import logging

from ast import literal_eval
from datetime import datetime, timedelta
from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

class TraccarTripDetails(models.Model):
    _name = "traccar.trip.details"
    _inherit = ['mail.thread']
    _description = "Trip Details"
    _order = 'id desc'

    def _default_trip_name(self):
        return self.env['ir.sequence'].next_by_code('traccar.trip.details')

    name = fields.Char(string='Name', default=lambda self: self._default_trip_name(), help="Sequence of Trip")
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    driver_id = fields.Many2one(related="vehicle_id.driver_id", string="Driver", readonly=False)
    traccar_device_uniqueid = fields.Char(related="vehicle_id.traccar_device_uniqueid", string="Traccar Unique Id", readonly=False)
    trip_date = fields.Date('Trip Date', default=fields.Date.today, help='Trip Date')
    trip_id = fields.Char('Device ID')
    device_id = fields.Integer('Device ID')
    distance = fields.Float('Distance')
    average_speed = fields.Float('Average Speed')
    max_speed = fields.Float('Max Speed')
    spent_fuel = fields.Float('Spent Fuel')
    start_odometer = fields.Float('Start Odometer')
    end_odometer = fields.Float('End Odometer')
    start_time = fields.Datetime(string='Start Time')
    end_time = fields.Datetime(string='End Time')
    start_position_id = fields.Char(string='Start Position Id')
    end_position_id = fields.Char(string='End Position Id')
    src_latitude = fields.Char(string='Source Latitude', help="Source Latitude")
    src_longitude = fields.Char(string='Source Longitude', help="Source Longitude")
    dst_latitude = fields.Char(string='Destination Latitude', help="Destination Latitude")
    dst_longitude = fields.Char(string='Destination Longitude', help="Destination Longitude")
    src_address = fields.Char(string='Source Address', help="Source Address")
    dst_address = fields.Char(string='Source Address', help="Source Address")
    duration = fields.Char('Duration')

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
    
    def create_trip(self, trip_data):
        trip_details_sudo = self.env['traccar.trip.details'].sudo()
        fleet_vehicle_sudo = self.env['fleet.vehicle'].sudo()
        for trip in trip_data:
            data = {}

            device_id = trip.get('deviceId', '')
            startTime = "".join(trip.get('startTime', '').split(".")[:-1])
            time = datetime.strptime(startTime,"%Y-%m-%dT%H:%M:%S")
            trip_id = str(device_id) + str(time).replace('T', '').replace('Z', '').replace(':', '').replace('-', '').replace(' ', '')

            trip_details = trip_details_sudo.search([('trip_id', '=', trip_id)], limit=1, order="id desc")
            if trip_details:
                continue

            fleet_vehicle = fleet_vehicle_sudo.search([('traccar_device_id', '=', device_id)], limit=1)
            if fleet_vehicle and fleet_vehicle.is_traccar:                
                data['vehicle_id'] = fleet_vehicle.id
            else:
                continue

            endTime = "".join(trip.get('endTime', '').split(".")[:-1])
            data['trip_id'] = trip_id
            data['device_id'] = device_id            
            data['distance'] = trip.get('distance', '')
            data['average_speed'] = trip.get('averageSpeed', '')
            data['max_speed'] = trip.get('maxSpeed', '')
            data['spent_fuel'] = trip.get('spentFuel', '')
            data['start_odometer'] = trip.get('startOdometer', '')
            data['end_odometer'] = trip.get('endOdometer', '')
            data['start_time'] = datetime.strptime(startTime, "%Y-%m-%dT%H:%M:%S")
            data['end_time'] = datetime.strptime(endTime, "%Y-%m-%dT%H:%M:%S")
            data['start_position_id'] = trip.get('startPositionId', '')
            data['end_position_id'] = trip.get('endPositionId', '')
            data['src_latitude'] = trip.get('startLat', '')
            data['src_longitude'] = trip.get('startLon', '')
            data['dst_latitude'] = trip.get('endLat', '')
            data['dst_longitude'] = trip.get('endLon', '')
            data['src_address'] = trip.get('startAddress', '')
            data['dst_address'] = trip.get('endAddress', '')
            data['duration'] = trip.get('duration', '')

            self.create(data)

    def cron_update_trip_details(self, to_date=False, from_date=False):
        config = self.env['traccar.config.settings'].sudo().search([('active', '=', True)], limit=1)
        to_date = to_date if to_date else datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        from_date = from_date if from_date else (fields.Datetime.from_string(datetime.now()) - timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%SZ")
        devices = config.fetch_devices_info()
        if devices:
            try:
                for device in devices:
                    url = "{}/api/reports/trips?deviceId={}&from={}&to={}".format(config.api_url, device['id'], from_date, to_date)
                    headers = {
                        'Accept' : 'application/json'
                    }
                    response = requests.get(url, auth=(config.api_user, config.api_pwd), headers=headers)
                    if response.status_code == 200:
                        trip_data = response.json()                        
                        self.create_trip(trip_data)   
                    elif response.status_code == 401:
                        _logger.info(('Traccar Unauthorized Access: Check traccar credentials %s') % response.text)
                    else :
                        _logger.info(('Traccar Connection Error: %s') % response.text)
            except Exception as e:
                _logger.info(('Error! Traccar Connection Error: %r') % e)
        else:
            _logger.info('Error! While running update sync information, no devices were discovered.')
        return True
