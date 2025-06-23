{
    "name": "HiTech AFAFERP PLM Spare",
    "version": "18.0.1.0.1",
    "author": "HiTechnologia",
    "category": "Manufacturing/Product Lifecycle Management (PLM)",
    "sequence": 15,
    "license": "AGPL-3",
    "summary": "Add spare BOM and Spare Parts Manual",
    "depends": ["plm"],
    "data": [
        # reporting
        "report/bom_structure.xml",
        "report/product_product.xml",
        # wizards
        "wizards/plm_temporary.xml",
        # views
        "views/plm_description.xml",
        "views/ir_attachment.xml",
        "views/product_product_view.xml",
        "views/mrp_bom_view.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
