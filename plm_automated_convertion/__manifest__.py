{
    "name": "HiTech AFAFERP Product Lifecycle Management Batch conversion",
    "version": "18.0.1.0.0",
    "author": "HiTechnologia",
    "category": "Manufacturing/Product Lifecycle Management (PLM)",
    "sequence": 15,
    "license": "AGPL-3",
    "summary": "CAD editors batch conversion tool",
    "depends": ["plm"],
    "data": [
        "security/security.xml",
        "data/ir_cron.xml",
        "data/ir_action_server.xml",
        "data/data.xml",
        "wizards/plm_convert.xml",
        "view/ir_attachment.xml",
        "view/plm_convert_rule.xml",
        "view/plm_convert_servers.xml",
        "view/plm_convert_stack.xml",
    ],
    "external_dependencies": {
        "python": ["ezdxf", "matplotlib", "cadquery", "numpy-stl"]
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
