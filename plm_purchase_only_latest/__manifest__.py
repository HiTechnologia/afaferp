{
    "name": "HiTech AFAFERP PLM Purchase Only Latest",
    "version": "18.0.1.0.0",
    "author": "HiTechnologia",
    "category": "Manufacturing/Product Lifecycle Management (PLM)",
    "sequence": 15,
    "license": "AGPL-3",
    "summary": "Show only latest product version in purchase",
    "description": """
        Allow to select only product that have not have engineering_code
        or is in the latest revision for Purchase
        """,
    "depends": ["plm", "purchase"],
    "data": ["data/purchase_only_parameter.xml", "views/purchase_views.xml"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
