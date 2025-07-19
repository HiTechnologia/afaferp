# -*- coding: utf-8 -*-
{
    "name": "HiTech AFAFERP Fleet Traccar Tracking | Fleet Tracking | Vehicle Tracking | Fleet Vehicle Traccar Tracking",
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
    "author": "HiTechnologia",
    "maintainer": "HiTechnologia",
    "license" :  "Other proprietary",
    "images": ["images/fleet_traccar_tracking.png"],
    "category": "Employees",
    "depends": [
        "base",
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
        "views/traccar_config_settings_views.xml",
        "views/fleet_vehicle_views.xml",
        "views/fleet_traccar_vehicle_views.xml",
        "views/traccar_trip_details_views.xml",
        "views/traccar_route_details_views.xml",
        "views/traccar_event_details_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "/fleet_traccar_tracking/static/src/js/*.js",
            "/fleet_traccar_tracking/static/src/css/*.css",
            "/fleet_traccar_tracking/static/src/xml/*.xml",
        ],
    },
    "installable": True,
    "application": True,
    "price"                :  150,
    "currency"             :  "EUR",
    "pre_init_hook"        :  "pre_init_check", 
}
