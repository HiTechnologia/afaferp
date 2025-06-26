{
    "name": "HiTech AFAFERP Plm Box",
    "version": "18.0.1.0.0",
    "author": "Hitechnologia",
    "category": "Productivity/Documents",
    "sequence": 1,
    "summary": "",
    "depends": [
        "base",
        "plm",
        "account",  # to work with plm box entities
        "project",  # to work with plm box entities
        "sale",  # to work with plm box entities
    ],
    "license": "AGPL-3",
    "data": [
        "security/plm_security.xml",
        "data/plm_box_sequence_data.xml",
        "views/non_cad_doc.xml",
        "views/box_object_rel.xml",
        "views/ir_attachment.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
