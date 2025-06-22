{
    'name': 'HiTech AFAFERP Stock Usability',
    'version': '18.0.1.0.0',
    'category': 'Inventory, Logistic, Storage',
    'license': 'AGPL-3',
    'summary': 'Several usability enhancements in Warehouse management',
    'description': """
Stock Usability
===============

The usability enhancements include:
* display the source location on the tree view of the move lines of the pickings (by default, only the destination location is displayed).
* always display the field *Backorder* on the form view of picking (by default, this field is only displayed when it has a value, so the user doesn't know when the field has no value because he doesn't see the field !)
* add a group by Partner in the picking search view (particularly usefull for receptions)
* add graph view for pickings
* remove ability to translate stock.location, stock.location.route and stock.picking.type
    """,
    'author': 'HiTechnologia',
    'depends': ['stock'],
    'data': [
        'views/stock_quant.xml',
        'views/stock_location.xml',
        'views/stock_move.xml',
        'views/stock_move_line.xml',
        'views/stock_picking.xml',
        'views/stock_picking_type.xml',
        'views/stock_warehouse.xml',
        'views/stock_warehouse_orderpoint.xml',
        'views/product.xml',
        'views/procurement_group.xml',
        'views/stock_lot.xml',
        'views/procurement_scheduler_log.xml',
        'security/ir.model.access.csv',
        ],
    'installable': True,
}
