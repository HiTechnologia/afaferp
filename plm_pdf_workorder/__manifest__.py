{
    "name": "HiTech AFAFERP PLM Report PDF Workorder",
    "version": "18.0.1.0.0",
    "author": "HiTechnologia",
    "category": "Manufacturing/Product Lifecycle Management (PLM)",
    "sequence": 15,
    "summary": """
    This module allows you to get the plm pdf document
    available into the workorder workscheet.
    """,
    "license": "LGPL-3",
    "depends": ["plm"],
    "data": [
        "views/ir_attachment.xml",
        "views/mrp_routing_workcenter.xml",
        "views/mrp_workorder.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
