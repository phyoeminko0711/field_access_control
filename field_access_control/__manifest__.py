{
    "name": "Dynamic Field Access Control",
    "version": "18.0.1.0.0",
    "category": "Technical",
    "summary": "Dynamic field-level readonly and visibility access control",
    "description": """
Dynamic Field Access Control
============================

This module allows administrators to configure dynamic
field-level access control for any model.

Key Features:
-------------
- Configure field-level access rules per model
- Set fields as readonly or invisible dynamically
- Apply rules per user or user group
- Control write access on selected business objects
- Fully configurable through user interface
""",
    "author": "Phyoe Min Ko",
    "license": "LGPL-3",
    "depends": [
        "base",
        "product",
        "sale_management",
        "purchase",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/field_access_config_views.xml",
        "views/menu_views.xml",
    ],
    "images": ["static/description/icon.png"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
