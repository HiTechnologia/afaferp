{
    "name": "HiTech AFAFERP PLM Web Revision",
    "version": "18.0.1.0.0",
    "author": "HiTechnologia",
    "category": "Manufacturing/Product Lifecycle Management (PLM)",
    "sequence": 15,
    "license": "AGPL-3",
    "summary": "PLM Revision from web side",
    "depends": ["plm"],
    "data": [
        "security/base_plm_web_rev_security.xml",
        "wizards/product_rev_wizard.xml",
        "wizards/document_rev_wizard.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
