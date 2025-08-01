{
    "name": "HiTech AFAFERP PLM Document Syncronization",
    "version": "18.0.0.1",
    "author": "HiTechnologia",
    "category": "Manufacturing/Product Lifecycle Management (PLM)",
    "sequence": 15,
    "license": "AGPL-3",
    "summary": "PLM document server syncronization",
    "images": [],
    "depends": ["plm"],
    "data": [
        "views/ir_attachment.xml",
        "views/plm_remote_server.xml",
        "views/plm_document_action_syncronize.xml",
        "data/server_action.xml",
        "security/base_plm_web_rev_security.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
