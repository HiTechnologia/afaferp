{
    "name": "HiTech AFAFERP PLM Project",
    "version": "18.0.1.0.4",
    "author": "HiTechnologia",
    "category": "Manufacturing/Product Lifecycle Management (PLM)",
    "license": "AGPL-3",
    "sequence": 15,
    "summary": "Connect odoo project with odooPLM",
    "depends": ["plm", "project"],
    "data": [
        "views/project.xml",
        "views/product.xml",
        "views/project_task.xml",
        "views/mail_activity_type.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
