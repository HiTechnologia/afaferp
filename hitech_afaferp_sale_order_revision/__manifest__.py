{
    "name": "HiTech AFAFERP Sale order revisions",
    "summary": "Keep track of revised quotations",
    "version": "18.0.1.0.0",
    "category": "Sale Management",
    "author": "HiTechnologia",
    "company": "HiTechnologia",
    "license": "AGPL-3",
    "depends": ["base_revision", "sale_management"],
    "data": ["view/sale_order.xml"],
    "installable": True,
    "post_init_hook": "populate_unrevisioned_name",
}
