# -*- coding: utf-8 -*-
#################################################################################
# Author      : CFIS (<https://www.cfis.store/>)
# Copyright(c): 2017-Present CFIS.
# All Rights Reserved.
#
#
#                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://www.cfis.store/>
#################################################################################

{
    "name": "Fleet Traccar Tracking | Fleet Tracking | Vehicle Tracking | Fleet Vehicle Traccar Tracking",
    "summary": """
        You may handle tracking data and report it utilizing for Odoo users more easily with the help of the module.
        The journeys, routes, and events for Traccar-integrated vehicles are managed by this module.
        
        traccar app and odoo fleet integration will allow you to simply manage vehicle tracking from a single piece of
        software. You can check the travel history for a specific custom time period and check the movements of the 
        vehicles with its assistance.
    """,
    "version": "18.0",
    "description": """
        You may handle tracking data and report it utilizing for Odoo users more easily with the help of the module.
        The journeys, routes, and events for Traccar-integrated vehicles are managed by this module.
        
        traccar app and odoo fleet integration will allow you to simply manage vehicle tracking from a single piece of
        software. You can check the travel history for a specific custom time period and check the movements of the 
        vehicles with its assistance.
        Fleet Traccar Tracking,
        Fleet Tracking,
        Vehicle Tracking,
        Fleet Vehicle Tracking,
    """,    
    "author": "CFIS",
    "maintainer": "CFIS",
    "license" :  "Other proprietary",
    "website": "https://www.cfis.store",
    "images": ["images/fleet_traccar_tracking.png"],
    "category": "Employees",
    "depends": [
        "base",
        'web',
        "fleet",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/ir_cron_data.xml",
        "wizard/raise_message.xml",
        "wizard/wizard_traccar_device_summary.xml",
        "wizard/wizard_traccar_fetch_trips.xml",
        "wizard/wizard_traccar_fetch_routes.xml",
        "wizard/wizard_traccar_device_location.xml",
        "wizard/employee_movement_report_view.xml",
        "views/traccar_config_settings_views.xml",
        "views/fleet_vehicle_views.xml",
        "views/fleet_traccar_vehicle_views.xml",
        "views/traccar_trip_details_views.xml",
        "views/traccar_route_details_views.xml",
        "views/traccar_event_details_views.xml",
        'views/dashboard_view.xml',
    ],
    "assets": {
        "web.assets_backend": [
            "/fleet_traccar_tracking/static/src/js/*.js",
            "/fleet_traccar_tracking/static/src/css/*.css",
            "/fleet_traccar_tracking/static/src/xml/*.xml",
            # 'fleet_traccar_tracking/static/src/js/traccar_dashboard.js',
            # 'https://cdn.jsdelivr.net/npm/chart.js',
        ],
    },
    "installable": True,
    "application": True,
    "price"                :  150,
    "currency"             :  "EUR",
    "pre_init_hook"        :  "pre_init_check", 
}
