{
    "name": "HiTech AFAFERP PLM Engineering",
    "version": "18.0.1.0.0",
    "author": "HiTechnologia",
    "category": "Manufacturing/Product Lifecycle Management (PLM)",
    "sequence": 15,
    "summary": "Allow to use engineering boms",
    "license": "AGPL-3",
    "depends": ["plm"],
    "data": [
        "views/mrp_bom.xml",
        # 'views/product_product_kanban.xml',
        "views/menu.xml",
        "views/product_product.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
