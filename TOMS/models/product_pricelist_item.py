from odoo import fields, models, api




class product_pricelist_item(models.Model):
    _inherit = 'product.pricelist.item'

    saoa_code = fields.Many2one(related='product_tmpl_id.saoa_code_id')
    saoa_code_only = fields.Char(string="SAOA Code", related='product_tmpl_id.saoa_code_only')


    @api.model
    def _no_record_rule(self, vals):
        self.env['product.pricelist.item'].sudo().orm_method()



