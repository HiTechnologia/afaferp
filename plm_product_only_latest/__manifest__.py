{
    "name": "HiTech AFAFERP PLM Produce Only Latest",
    "version": "18.0.1.0.0",
    "author": "HiTechnologia",
    "category": "Manufacturing/Product Lifecycle Management (PLM)",
    "sequence": 15,
    "license": "AGPL-3",
    "summary": "Show only latest product version in production",
    "depends": ["plm", "sale"],
    "description": """
        Allow to select only product that have engineering_code and
        is in the latest revision for Manufacturing
        """,
    "data": ["data/product_only_parameter.xml", "views/mrp_production_views.xml"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
