# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import models, fields, api, _
from odoo.exceptions import Warning, UserError



class StockInventoryLine(models.Model):
    _inherit = "stock.inventory.line"
    
    sequence = fields.Integer(string='Sequence', default=0)
    sh_inven_adjt_barcode_scanner_is_last_scanned = fields.Boolean(string = "Last Scanned?")    
    

class StockInventory(models.Model):
    _name = "stock.inventory"
    _inherit = ['barcodes.barcode_events_mixin', 'stock.inventory']
    
    def _add_product(self, barcode):
        
        is_last_scanned = False
        sequence = 0
        warm_sound_code = ""
        
        if self.env.user.company_id.sudo().sh_inven_adjt_barcode_scanner_last_scanned_color:  
            is_last_scanned = True          
        
        if self.env.user.company_id.sudo().sh_inven_adjt_barcode_scanner_move_to_top:
            sequence = -1
            
        if self.env.user.company_id.sudo().sh_inven_adjt_barcode_scanner_warn_sound:
            warm_sound_code = "SH_BARCODE_SCANNER_"     
                    
        if self.env.user.company_id.sudo().sh_inven_adjt_barcode_scanner_auto_close_popup:
            warm_sound_code += "AUTO_CLOSE_AFTER_" + str(self.env.user.company_id.sudo().sh_inven_adjt_barcode_scanner_auto_close_popup) + "_MS&"   


        
        
        #step 1: state validation.
        if self and self.state != 'confirm':
            selections = self.fields_get()['state']['selection']
            value = next((v[1] for v in selections if v[0] == self.state), self.state)
            raise UserError(_(warm_sound_code + "You can not scan item in %s state.") %(value))
        
        elif self:
            
            self.line_ids.update({
                'sh_inven_adjt_barcode_scanner_is_last_scanned': False,
                'sequence': 0,
                })             
            
            
            search_lines = False
            domain = []
            
            if self.env.user.company_id.sudo().sh_inven_adjt_barcode_scanner_type == 'barcode':
                search_lines = self.line_ids.filtered(lambda l: l.product_id.barcode == barcode)
                domain = [("barcode","=",barcode)]
            
            elif self.env.user.company_id.sudo().sh_inven_adjt_barcode_scanner_type == 'int_ref':
                search_lines = self.line_ids.filtered(lambda l: l.product_id.default_code == barcode)
                domain = [("default_code","=",barcode)]
            
            
            elif self.env.user.company_id.sudo().sh_inven_adjt_barcode_scanner_type == 'sh_qr_code':
                search_lines = self.line_ids.filtered(lambda l: l.product_id.sh_qr_code == barcode)
                domain = [("sh_qr_code","=",barcode)]                
                
                            
            
            elif self.env.user.company_id.sudo().sh_inven_adjt_barcode_scanner_type == 'all':
                search_lines = self.line_ids.filtered(lambda l: l.product_id.barcode == barcode or 
                                                      l.product_id.default_code == barcode or
                                                      l.product_id.sh_qr_code == barcode,                                                      
                                                      )
                domain = ["|","|",
                          
                    ("default_code","=",barcode),
                    ("barcode","=",barcode),
                    ("sh_qr_code","=",barcode)
                    
                ]              
            
            if search_lines:
                for line in search_lines:
                    line.product_qty += 1
                    line.sh_inven_adjt_barcode_scanner_is_last_scanned = is_last_scanned,
                    line.sequence = sequence
                    
                    break
            else:
                search_product = self.env["product.product"].search(domain, limit = 1)
                if search_product:                    
                    inventory_line_val = {
                            'display_name': search_product.name,
                            'product_id': search_product.id,
                            'location_id':self.location_id.id,   
                            'product_qty': 1,
                            'inventory_id': self.id,
                            'sh_inven_adjt_barcode_scanner_is_last_scanned' : is_last_scanned,
                            'sequence' : sequence,
                    }
                    if search_product.uom_id:
                        inventory_line_val.update({
                            'product_uom_id': search_product.uom_id.id,                            
                            })
                    self.env["stock.inventory.line"].new(inventory_line_val)                               
  
                else:
                    raise UserError(_(warm_sound_code + "Scanned Internal Reference/Barcode not exist in any product!"))         
            
    def on_barcode_scanned(self, barcode):  
        self._add_product(barcode)    



                    