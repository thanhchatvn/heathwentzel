# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class res_company(models.Model):
    _inherit = "res.company"

    #inventory adjustment
    sh_inven_adjt_barcode_scanner_type = fields.Selection([
        ('int_ref','Internal Reference'),
        ('barcode','Barcode'),
        ('sh_qr_code','QR Code'),
        ('all','All'),
        ],default = 'barcode' ,string='Product Scan Options', translate=True)
    
    
    sh_inven_adjt_barcode_scanner_last_scanned_color = fields.Boolean(
        string='Last scanned Color?', translate=True)

    sh_inven_adjt_barcode_scanner_move_to_top = fields.Boolean(
        string='Last scanned Move To Top?', translate=True)

    sh_inven_adjt_barcode_scanner_warn_sound = fields.Boolean(
        string='Warning Sound?', translate=True)  
    
        
    sh_inven_adjt_barcode_scanner_auto_close_popup = fields.Integer(
        string='Auto close alert/error message after', translate=True)   
    
    