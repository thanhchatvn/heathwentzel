# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import api, fields, models


class res_config_settings(models.TransientModel):
    _inherit = 'res.config.settings'

    # inventory adjustment
    sh_inven_adjt_barcode_scanner_type = fields.Selection([
        ('int_ref','Internal Reference'),
        ('barcode','Barcode'),
        ('sh_qr_code','QR Code'),
        ('all','All'),
        ],related='company_id.sh_inven_adjt_barcode_scanner_type', string='Product Scan Options', translate=True,readonly = False)
    
    sh_inven_adjt_barcode_scanner_last_scanned_color = fields.Boolean(
        string='Last scanned Color?', 
        related='company_id.sh_inven_adjt_barcode_scanner_last_scanned_color',
        translate=True,readonly = False)

    sh_inven_adjt_barcode_scanner_move_to_top = fields.Boolean(
        string='Last scanned Move To Top?', 
        related='company_id.sh_inven_adjt_barcode_scanner_move_to_top',
        translate=True,readonly = False)

    sh_inven_adjt_barcode_scanner_warn_sound = fields.Boolean(
        string='Warning Sound?', 
        related='company_id.sh_inven_adjt_barcode_scanner_warn_sound',
        translate=True,readonly = False)      
    
    
    sh_inven_adjt_barcode_scanner_auto_close_popup = fields.Integer(
        related='company_id.sh_inven_adjt_barcode_scanner_auto_close_popup', 
        string='Auto close alert/error message after', translate=True,readonly = False)

    @api.model
    def get_values(self):
        res = super(res_config_settings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        res.update(
            sh_inven_adjt_barcode_scanner_type=get_param('sh_inventory_adjustment_barcode_scanner.sh_inven_adjt_barcode_scanner_type'),
        )
        return res

    @api.multi
    def set_values(self):
        super(res_config_settings, self).set_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        ICPSudo.set_param("sh_inventory_adjustment_barcode_scanner.sh_inven_adjt_barcode_scanner_type", self.sh_inven_adjt_barcode_scanner_type)
