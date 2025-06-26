{
    "name": "HiTech AFAFERP PLM Breakages",
    "version": "18.0.1.0.0",
    "author": "HiTechnologia",
    "category": "Manufacturing/Product Lifecycle Management (PLM)",
    "license": "AGPL-3",
    "summary": "PLM Breakages",
    "depends": ["base", "product", "mrp"],
    "data": [
        "security/base_plm_security.xml",
        "data/sequence.xml",
        "views/breakages_view.xml",
        "views/product_view.xml",
        "views/bom_view.xml",
        "views/mrp_production.xml",
    ],
    "installable": True,
}
