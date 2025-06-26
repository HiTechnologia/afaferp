{
    "name": "HiTech AFAFERP PLM Sale Only Latest",
    "version": "18.0.1.0.0",
    "author": "HiTechnologia",
    "category": "Manufacturing/Product Lifecycle Management (PLM)",
    "sequence": 15,
    "license": "AGPL-3",
    "summary": "Show only latest product version in sale",
    "description": """
        Allow to select only product that have not engineering_code or
        is in the latest revision for sale.
        """,
    "depends": ["plm", "sale_management"],
    "data": [
        "data/sale_only_parameter.xml",
        "views/sale_order.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
