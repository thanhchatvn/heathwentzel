from odoo import api, fields, models, _
from odoo.tools import float_utils, float_compare


import logging

_logger = logging.getLogger(__name__)

class stock_picking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def button_validate(self):
        if not self._context.get('from_wizard'):
            product_ids = self.move_lines.filtered(lambda l:l.product_id.type == 'consu' and self.picking_type_id.code == 'incoming')
            if product_ids:
                return {
                        'name': _('Receive Product Warning'),
                        'type': 'ir.actions.act_window',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'wizard.receive.product',
                        'target': 'new',
                        'context':{'stock_picking_id':self.id}
                    }
            else:
                return super(stock_picking, self).button_validate()
        else:
            return super(stock_picking, self).button_validate()


class StockTakeDMX(models.Model):
    _name = 'stock.take'
    _description = 'Stock take model'

    name = fields.Char()
    note = fields.Text()
    stock_inventory_ids = fields.One2many(
            'stock.inventory',
            'stock_take_id',
            string='Inventory Batches')
    state = fields.Selection([
                             ('draft', 'Draft'),
                             ('in_progress', 'In Progress'),
                             ('validated', 'Validated'),
                             ('cancelled', 'Cancelled'),
                            ],
                            default="draft")

    def start_stock_take(self):
        for rec in self:
            rec.state = 'in_progress'

    def validate_stock_take(self):
        return {
            'name': 'Validate Stock Take',
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.stock.take.validate',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {
                'default_stock_take_id': self.id,
            }
        }

    def cancel_stock_take(self):
        for rec in self:
            for inv_adjsmnt in rec.stock_inventory_ids:
                inv_adjsmnt.action_cancel_draft()
            rec.state = 'cancelled'


class StockInventoryDMX(models.Model):
    _inherit = 'stock.inventory'

    stock_take_id = fields.Many2one(
            'stock.take',
            string='Stock Take')

    all_product_ids = fields.One2many('stock.inventory.line', 'all_products_id', string='All Products')
    parent_inventory_id = fields.Many2one("stock.inventory", string="Parent Adjustment")

    def action_cancel_draft(self):
        self.mapped('move_ids')._action_cancel()
        self.all_product_ids.unlink()
        self.write({
            'state': 'draft'
        })
        if self.search([('parent_inventory_id','=', self.id)]):
            for data in self.search([('parent_inventory_id','=', self.id)]):
                data.mapped('move_ids')._action_cancel()
                data.all_product_ids.unlink()
                data.write({
                    'state': 'draft'
                })
                data.unlink()
        return super(StockInventoryDMX, self).action_cancel_draft()

    def load_all_products(self):
        list1 = []
        for inventory in self.filtered(lambda x: x.state not in ('done', 'cancel')):
            vals = {'state': 'confirm', 'date': fields.Datetime.now()}
            if (inventory.filter == 'partial') and not inventory.all_product_ids:
                for line_values in inventory._get_inventory_lines_values():
                    line_values['product_qty'] =  0
                    if line_values['product_qty'] or line_values['theoretical_qty']:
                        if int(line_values['product_qty']) < int(line_values['theoretical_qty']):
                            line_values.update({'is_new_missing_stock': True})
                        if line_values['product_qty'] > line_values['theoretical_qty']:
                            line_values.update({'is_over_stock': True})
                        if int(line_values['product_qty']) == int(line_values['theoretical_qty']):
                            line_values.update({'is_compare_stock': True})
                    list1.append((0, 0, line_values))
                vals.update({'all_product_ids': list1})
            inventory.write(vals)
        return True

    def view_list_of_products(self):
        action = self.env.ref('stock.action_inventory_line_tree').read()[0]
        action['domain'] = [
            ('all_products_id', '=', self.id),
        ]
        return action

    def run_comparison(self):
        list1 = []
        for each in self.line_ids:
            list1.append(each.product_id.id)
        inventory_ids = self.all_product_ids.filtered(lambda x: x.product_id.id in list1)
        if inventory_ids:
            inventory_ids.unlink()

    def action_start(self):
        list1 = []
        for inventory in self.filtered(lambda x: x.state not in ('done', 'cancel')):
            vals = {'state': 'confirm', 'date': fields.Datetime.now()}
            if (inventory.filter != 'partial') and not inventory.line_ids:
                for line_values in inventory._get_inventory_lines_values():
                    if inventory.filter == 'none':
                        if line_values['product_qty'] and line_values['theoretical_qty']:
                            if int(line_values['product_qty']) < int(line_values['theoretical_qty']):
                                line_values.update({'is_new_missing_stock': True})
                            if line_values['product_qty'] > line_values['theoretical_qty']:
                                line_values.update({'is_over_stock': True})
                            if int(line_values['product_qty']) == int(line_values['theoretical_qty']):
                                line_values.update({'is_compare_stock': True})
                            line_values.update({'is_different_stock': True})
                    line_values.update({'product_qty': 0})
                    list1.append((0, 0, line_values))
                vals.update({'line_ids': list1})
            inventory.write(vals)
            # inventory.action_reset_product_qty()
        return True

    def action_reset_product_qty(self):
        for line in self.line_ids:
            line.write({'product_qty': 0})
        return True

    @api.model
    def create(self, vals):
        res = super(StockInventoryDMX, self).create(vals)
        return res

    def action_spliting_custom(self):
        for inventory in self:
            param_obj = self.env['ir.config_parameter']
            if len(self.line_ids) > int(param_obj.sudo().get_param('stock.stock_inventory_lines_limit')):
                start_limit = 0
                child_limit = 1
                increasing_limit = int(param_obj.sudo().get_param('stock.stock_inventory_lines_limit'))
                ending_limit = len(self.line_ids)
                list1 = self.line_ids
                while True:
                    if increasing_limit <= ending_limit:
                        data_id = self.env['stock.inventory'].create(
                            {'parent_inventory_id': inventory.id, 'state': 'confirm',
                             'location_id': inventory.location_id.id, 'filter': 'none',
                             'company_id': inventory.company_id.id, 'name': inventory.name + "-" + str(child_limit),
                             'stock_take_id': inventory.stock_take_id.id, '_barcode_scanned': False,
                             'accounting_date': False, 'product_id': False, 'category_id': False, 'lot_id': False,
                             'partner_id': False, 'package_id': False, 'exhausted': False})
                        child_limit += 1
                        list1[start_limit:increasing_limit].write({'inventory_id':data_id.id})
                        start_limit = increasing_limit
                        increasing_limit = increasing_limit + int(
                            param_obj.sudo().get_param('stock.stock_inventory_lines_limit'))
                    elif increasing_limit >= ending_limit:
                        break

    def action_validate_custom(self):
        if self.search([('parent_inventory_id','=', self.id)]):
            for data in self.search([('parent_inventory_id','=', self.id)]):
                if data.state != 'done':
                    data.action_validate()
            self.action_validate()
        else:
            self.action_validate()

class StockInventoryLineDMX(models.Model):
    _inherit = 'stock.inventory.line'
    _debug= True

    product_categ_id = fields.Many2one(related='product_id.categ_id', store=True, string="Category")
    all_products_id = fields.Many2one('stock.inventory', string='All Product ID', invisible=True)
    is_new_missing_stock = fields.Boolean(string='Missing Stock')
    is_over_stock = fields.Boolean(string='over Stock')
    is_compare_stock = fields.Boolean(string='Compare Stock')
    is_different_stock = fields.Boolean(string='Different Stock')
    real_cost = fields.Float(string="Real Cost", store=True, compute="_get_cost_value")
    theoretical_cost = fields.Float(string="Theoretical Cost", store=True, compute="_get_cost_value")
    difference_cost = fields.Float(string="Difference Cost", store=True, compute="_get_cost_value")
    parent_location_id = fields.Many2one(related="location_id.location_id", string="Parent Location", store=True)

    def log(self, msg):
        if self._debug:
            _logger.info(msg)

    @api.multi
    def write(self, vals):
        if vals.get('product_qty'):
            if float(vals['product_qty']) < float(self.theoretical_qty):
                vals.update({'is_new_missing_stock': True,
                         'is_over_stock': False,
                         'is_compare_stock': False,
                         'is_different_stock': True})
            if float(vals['product_qty']) > float(self.theoretical_qty):
                vals.update({'is_over_stock': True,
                             'is_new_missing_stock': False,
                             'is_compare_stock': False,
                             'is_different_stock': True})
            if float(vals['product_qty']) == float(self.theoretical_qty):
                vals.update({'is_compare_stock': True,
                             'is_new_missing_stock': False,
                             'is_over_stock': False,
                             'is_different_stock': False})
        else:
            if vals.get('product_qty') and int(vals['product_qty']) == 0:
                if float(vals['product_qty']) < float(self.theoretical_qty):
                    vals.update({'is_new_missing_stock': True,
                                 'is_over_stock': False,
                                 'is_compare_stock': False,
                                 'is_different_stock': True})
                if float(vals['product_qty']) > float(self.theoretical_qty):
                    vals.update({'is_over_stock': True,
                             'is_new_missing_stock': False,
                             'is_compare_stock': False,
                             'is_different_stock': True})
                if float(vals['product_qty']) == float(self.theoretical_qty):
                    vals.update({'is_compare_stock': True,
                             'is_new_missing_stock': False,
                             'is_over_stock': False,
                                 'is_different_stock': False})
        return super(StockInventoryLineDMX, self).write(vals)

    @api.multi
    @api.depends('product_qty', 'theoretical_qty', 'value')
    def _get_cost_value(self):
        for each in self:
            if each.product_qty:
                each.real_cost = each.product_qty * each.product_id.standard_price
            if each.theoretical_qty:
                each.theoretical_cost = each.theoretical_qty * each.product_id.standard_price
            if each.real_cost and each.theoretical_cost:
                each.difference_cost = each.theoretical_cost - each.real_cost

    @api.depends('product_qty', 'theoretical_qty', 'value')
    def _get_total_value(self):
        for rec in self:
            rec.variance= rec.product_qty - rec.theoretical_qty
            rec.total_value = rec.value * rec.variance

    @api.depends('product_id')
    def _get_value(self):
        for rec in self:
            rec.value = rec.product_id.standard_price


    variance = fields.Float(string='Variance', store=True,
            compute=_get_total_value,
        )
    value = fields.Float(string='Unit Value',
            compute=_get_value,
            store=True)
    total_value = fields.Float(string='Total Value',
            compute=_get_total_value,
            store=True,
            readonly=True)
    stock_take_id = fields.Many2one("stock.take", string='Stock Name',
            store=True,
            readonly=True)

    @api.model
    def create(self, vals):
        if vals.get('product_qty'):
            product_id = self.env['product.product'].browse(int(vals.get('product_id')))
            theoretical_qty = product_id.get_theoretical_quantity(
                product_id.id,
                vals.get('location_id'),
                lot_id=vals.get('lot_id'),
                package_id=vals.get('package_id'),
                owner_id=vals.get('partner_id'),
                to_uom=vals.get('product_uom_id'),
            )
            if float(vals['product_qty']) < float(theoretical_qty):
                vals.update({'is_new_missing_stock': True})
            if float(vals['product_qty']) > float(theoretical_qty):
                vals.update({'is_over_stock': True})
            if float(vals['product_qty']) == float(theoretical_qty):
                vals.update({'is_compare_stock': True})
            if float(vals['product_qty']) != float(theoretical_qty):
                vals.update({'is_different_stock': True})
        return super(StockInventoryLineDMX, self).create(vals)


    @api.model
    def default_get(self, fields):
        fields.append('stock_take_id')
        print("\n\n\n fields-->", fields)
        res = super(StockInventoryLineDMX, self).default_get(fields)
        print("\n\n\n res--->", res)
        return res
    
    @api.model
    def create(self, vals):
        print("\n\n\n vals--->", vals)
        res = super(StockInventoryLineDMX, self).create(vals)
        if res.inventory_id:
            res.stock_take_id = res.inventory_id.stock_take_id.id
        return res