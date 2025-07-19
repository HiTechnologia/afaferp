from odoo import _, api, fields, models

import logging
_logger = logging.getLogger(__name__)

class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    is_traccar = fields.Boolean("Is Traccar", default=False)
    traccar_device_uniqueid = fields.Char(string='Device Identifier', help="Device Identifier")
    traccar_device_id = fields.Char(string='Traccar Device ID', help="Traccar Device ID")
    traccar_device_status = fields.Selection([
        ('online', 'Online'),
        ('offline', 'Offline')
        ], string='Is Online', default="offline", help="Device Status")
    traccar_device_lastupdate = fields.Char(string='Last Update', help="Traccar Last Update")

    def sync_traccar_device(self):
        config = self.env['traccar.config.settings'].sudo().search([('active', '=', True)], limit=1)
        devices = config.fetch_devices_info(uniqueId=self.traccar_device_uniqueid)
        if devices:
            for device in devices:
                self.write({
                    'traccar_device_id': device['id'],
                    'traccar_device_status': 'online' if device['status'] == 'online' else 'offline',
                    'traccar_device_lastupdate': device['lastUpdate'] or False
                })
        else:
            data = {
                "name":self.model_id.name,
                "uniqueId" : self.traccar_device_uniqueid,
            }
            device = config.create_device_info(data)
            if device:
                self.traccar_device_id = device
                self.traccar_device_status = 'offline'
        return True

    def action_open_device_summary(self):
        vals = {
            'vehicle_id':self.id,
            'device_id' : self.traccar_device_id,
        }
        summary = self.env['wizard.traccar.device.summary'].create(vals)
        context = self._context or {}
        return {
            'name': ("View Device Summary"),
            'res_model': 'wizard.traccar.device.summary',
            'view_id': self.env.ref('fleet_traccar_tracking.form_wizard_traccar_device_summary').id,
            'res_id': summary.id,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',                                                
            'context': context,
            'nodestroy': True,
            'target': 'new',
        }

    def action_fetch_trips(self):
        vals = {
            'vehicle_id':self.id,
            'device_id' : self.traccar_device_id,
        }
        trips = self.env['wizard.traccar.fetch.trips'].create(vals)
        context = self._context or {}
        return {
            'name': ("Fetch Trips"),
            'res_model': 'wizard.traccar.fetch.trips',
            'view_id': self.env.ref('fleet_traccar_tracking.form_wizard_traccar_fetch_trips').id,
            'res_id': trips.id,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',                                                
            'context': context,
            'nodestroy': True,
            'target': 'new',
        }
    
    def action_fetch_routes(self):
        vals = {
            'vehicle_id':self.id,
            'device_id' : self.traccar_device_id,
        }
        routes = self.env['wizard.traccar.fetch.routes'].create(vals)
        context = self._context or {}
        return {
            'name': ("Fetch Routes"),
            'res_model': 'wizard.traccar.fetch.routes',
            'view_id': self.env.ref('fleet_traccar_tracking.form_wizard_traccar_fetch_routes').id,
            'res_id': routes.id,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',                                                
            'context': context,
            'nodestroy': True,
            'target': 'new',
        }
    
    def action_open_device_location(self):
        vals = {
            'vehicle_id':self.id,
            'device_id' : self.traccar_device_id,
        }
        location = self.env['wizard.traccar.device.location'].create(vals)
        context = self._context or {}
        return {
            'name': ("Device Location"),
            'res_model': 'wizard.traccar.device.location',
            'view_id': self.env.ref('fleet_traccar_tracking.form_wizard_traccar_device_location').id,
            'res_id': location.id,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',                                                
            'context': context,
            'nodestroy': True,
            'target': 'new',
        }