{
    "name": "HiTech AFAFERP PLM Consumption Plans",
    "version": "18.0.0.0.2",
    "author": "HiTechnologia",
    "category": "Manufacturing/Product Lifecycle Management (PLM)",
    "sequence": 15,
    "summary": "Manage and track reference and actual consumption plans for BoM lines",
    "description": """
        PLM Consumption Plans
        This module introduces a structured approach for defining and managing production consumption plans
        within the Product Lifecycle Management (PLM) workflow in Odoo 18
    """,
    "license": "LGPL-3",
    "depends": ["plm"],
    "data": [
        # security files
        "security/ir.model.access.csv",
        # data files
        "data/ir_cron_data.xml",
        # views files
        "views/product_template_views.xml",
        "views/product_product_views.xml",
        "views/plm_template_consumption_plan_menu.xml",
        "views/plm_template_consumption_plan_view.xml",
        "views/mrp_bom_line_views.xml",
        "views/consumption_state_views.xml",
        # report files
        "report/report_consumption_plan.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
