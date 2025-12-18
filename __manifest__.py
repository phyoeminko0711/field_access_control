{
    'name': 'Dynamic Field Access Control',
    'version': '18.0.1.0.0',
    'category': 'Tools',
    'summary': 'Prevent updates and control field visibility dynamically',
    'description': """
        Dynamic Field Access Control
        =============================
        - Configure field-level access control per model
        - Set fields as readonly or hidden for specific users/groups
        - Prevent updates on product and product category
        - Flexible configuration through UI
    """,
    'author': 'Innovix Company',
    'website': 'https://www.innovix-solutions.com',
    'depends': ['base', 'product', 'sale_management', 'purchase', 'innovix_material_requisition'],
    'data': [
        'security/ir.model.access.csv',
        'views/field_access_config_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}