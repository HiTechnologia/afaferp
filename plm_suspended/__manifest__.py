{
    "name": "HiTech AFAFERP PLM Suspended State",
    "version": "18.0.1.0.0",
    "author": "HiTechnologia",
    "category": "Manufacturing/Product Lifecycle Management (PLM)",
    "sequence": 15,
    "license": "AGPL-3",
    "summary": "Add obsolete status to the work flow",
    "depends": ["mrp", "plm"],
    "data": [
        # views
        "views/ir_attachment.xml",
        "views/product_product.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
