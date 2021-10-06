# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import models,api, _
from odoo.exceptions import UserError

class StockInventory(models.Model):
    _inherit='stock.inventory'
 
    @api.one
    def sh_on_barcode_scanned(self, barcode):
        inventory_id =self.id
        stock_inventory = self.env['stock.inventory'].search([('id', '=', inventory_id)],limit=1)       
            
        if stock_inventory:
            search_type = self.env['ir.config_parameter'].sudo().get_param('sh_inventory_adjustment_barcode_scanner.sh_inven_adjt_barcode_scanner_type')
            if search_type == 'all':
                domain = ['|',('barcode', '=', barcode), ('default_code','=', barcode)]
            elif search_type == 'int_ref':
                domain = [('default_code','=', barcode)]
            else:
                domain = [('barcode', '=', barcode)]
            product_id = self.env['product.product'].search(domain,limit=1)

            if product_id:
                location_id = 0
                company = self.env.user.company_id
                warehouse = self.env['stock.warehouse'].search([('company_id', '=', company.id)], limit=1)

                if warehouse:
                    location_id = warehouse.lot_stock_id.id
                else:
                    raise UserError(_('You must define a warehouse for the company: %s.') % (company.name,))

                if not stock_inventory.line_ids:
                    inventory_line_val = {
                        'display_name': product_id.name,
                        'product_id': product_id.id,
                        'location_id':location_id,
                        'product_qty': 1,
                        'product_uom_id': product_id.product_tmpl_id.uom_id.id,
                        'inventory_id': stock_inventory.id
                    }

                    stock_inventory.update({'line_ids': [(0, 0, inventory_line_val)]})

                else:
                    stock_picking_line = stock_inventory.line_ids.search([('product_id', '=', product_id.id),('inventory_id','=',inventory_id)], limit=1)

                    if stock_picking_line:
                        stock_picking_line.product_qty += 1

                    else :
                        inventory_line_val = {
                            'display_name': product_id.name,
                            'product_id': product_id.id,
                            'location_id':location_id,
                            'product_qty': 1,
                            'product_uom_id': product_id.product_tmpl_id.uom_id.id,
                            'inventory_id': stock_inventory.id
                        }

                        stock_inventory.update({'line_ids': [(0, 0, inventory_line_val)]})

            else :
                raise UserError('Product does not exist')
