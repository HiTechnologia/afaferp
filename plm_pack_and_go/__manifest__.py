{
    "name": "HiTech AFAFERP Plm Pack and Go",
    "version": "18.0.1.0.0",
    "author": "HiTechnologia",
    "category": "Manufacturing/Product Lifecycle Management (PLM)",
    "sequence": 15,
    "summary": "Download BOM structure files from a component",
    "license": "AGPL-3",
    "depends": ["plm"],
    "external_dependencies": {"python": ["base64io"]},
    "data": [
        "security/plm_security.xml",
        "data/ir_parameters.xml",
        "wizard/plm_component.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
