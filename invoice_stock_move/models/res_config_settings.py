import ast
from odoo import fields, api, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

   
    auto_transfer_invoice = fields.Boolean(string="Auto Create Transfer from Invoice")
    auto_transfer_bill = fields.Boolean(string="Auto Create Transfer from Bill")

    auto_transfer_invoice_allowed_companies = fields.Many2many('res.company', 'res_companies_allowed_invoice_rel',
                                                               string="Allowed Companies")
    auto_transfer_bill_allowed_companies = fields.Many2many('res.company',  'res_companies_allowed_bill_rel',
                                                            string="Allowed Companies")
    auto_validate_transfer_from_invoice = fields.Boolean('Auto Validate Transfer from Invoice')
   
    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        param_obj = self.env['ir.config_parameter']
        res.update({
            'auto_transfer_invoice': param_obj.sudo().get_param('invoice_stock_move.auto_transfer_invoice'),
            'auto_transfer_bill': param_obj.sudo().get_param('invoice_stock_move.auto_transfer_bill'),
            'auto_validate_transfer_from_invoice': param_obj.sudo().get_param('invoice_stock_move.auto_validate_transfer_from_invoice'),

        })
        invoice_config_ids = param_obj.get_param('invoice_stock_move.auto_transfer_invoice_allowed_companies1')

        bill_config_ids = param_obj.get_param('invoice_stock_move.auto_transfer_bill_allowed_companies1')

        if invoice_config_ids:
            res.update({'auto_transfer_invoice_allowed_companies': ast.literal_eval(invoice_config_ids)})
        if bill_config_ids:
            res.update({'auto_transfer_bill_allowed_companies': ast.literal_eval(bill_config_ids)})
        return res

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        param_obj = self.env['ir.config_parameter']
        param_obj.sudo().set_param('invoice_stock_move.auto_transfer_invoice',
                                   self.auto_transfer_invoice)
        param_obj.sudo().set_param('invoice_stock_move.auto_transfer_bill',
                                   self.auto_transfer_bill)
        param_obj.sudo().set_param('invoice_stock_move.auto_validate_transfer_from_invoice',
                                   self.auto_validate_transfer_from_invoice)
        param_obj.sudo().set_param('invoice_stock_move.auto_transfer_invoice_allowed_companies1',
                                   self.auto_transfer_invoice_allowed_companies.ids)
        param_obj.sudo().set_param('invoice_stock_move.auto_transfer_bill_allowed_companies1',
                                   self.auto_transfer_bill_allowed_companies.ids)
        return res
