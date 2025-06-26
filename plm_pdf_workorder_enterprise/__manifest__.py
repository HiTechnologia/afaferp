{
    "name": "HiTech AFAFERP PLM Report PDF Workorder Enterprise",
    "version": "18.0.2.0.0",
    "author": "HiTechnologia",
    "category": "Manufacturing/Product Lifecycle Management (PLM)",
    "sequence": 15,
    "summary": """
    This module allows you to get the plm pdf document
    available into the workorder workscheet.
    """,
    "license": "LGPL-3",
    "depends": ["plm_pdf_workorder", 
                "mrp_workorder"],
    "assets": {
        "web.assets_backend": [
            "plm_pdf_workorder_enterprise/static/src/mrpWorksheet.js",
            "plm_pdf_workorder_enterprise/static/src/mrpDisplayRecord.xml",
        ]
    },
    "installable": True,
    "application": False,
    "auto_install": True,
}
