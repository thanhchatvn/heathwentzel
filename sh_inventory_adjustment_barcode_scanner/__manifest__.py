# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.
{
    "name": "Stock Adjustment Barcode Scanner",

    "author" : "Softhealer Technologies",
    
    "website": "https://www.softhealer.com",
    
    "support": "support@softhealer.com",    
        
    "version": "12.0.5",
        
    "category": "Warehouse",

    "summary": """scan barcode product app odoo, scan product internal ref no, scan barcode inventory module, scan barcode stock, barcode product reference no, scan stock adjustment barcode, scan inventory adjustment""", 
        
   "description": """Do your time-wasting in inventory operations by manual product selection? So here are the solutions these modules useful do quick operations of inventory using a barcode scanner. We have added tree view in the form view. You can scan products and that qty increase by 1(One). You no need to select the product and do one by one. scan it and you do! So be very quick in all operations of odoo and cheers!

 Stock Adjustment Barcode Scanner Odoo
 Scan Product By Barcode, Scan Product By Internal Reference Number, Scan Inventory With Barcode, Scan Stock With Barcode, Scan Stock Product With Barcode, Scan Warehouse Product With Reference No, Stock Adjustment With Barcode, Inventory Adjustment With Reference Number Odoo.
 Scan Barcode Product App, Scan Product Internal Reference No, Scan Barcode Inventory, Scan Barcode Stock, Scan Barcode Product Reference No, Scan Stock Adjustment Barcode, Scan Inventory Adjustment Reference No Odoo.

""",
    
    "depends": ["barcodes","stock","sh_product_qrcode_generator"],
    
    "data": [
        
        "views/assets.xml",
        "views/res_config_settings_views.xml",
        "views/stock_inventory_template.xml",
        "views/stock_view.xml",
    ],    
    
    "images": ["static/description/background.png",],
    "live_test_url": "https://youtu.be/JDjyV1YISJU",
    "installable": True,    
    "application": True,    
    "autoinstall": False,
    "price": 17,
    "currency": "EUR"        
}
