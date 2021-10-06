from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from datetime import datetime
from datetime import date
@tagged('-at_install', 'post_install')
class TestJobPoOrder(TransactionCase):
    """
        Test for Inventory.
    """
    print('\n\n--------test inventory')
    def test_create_inventory(self):
        stock_take_id = False
        location_id = False
        stock_take = self.env['stock.take'].search([('name', '=', 'TEST')], limit=1)
        location = self.env['stock.location'].search([('name', '=', 'Stock')], limit=1)
        if stock_take:
            stock_take_id = stock_take.id
        else:
            stock_take = self.env['stock.take'].create({
                'name': "TEST INVENTORY"
            })
            stock_take_id = stock_take.id
        print("\n\n\n========>new stock_take_id", stock_take_id)
        if location:
            location_id = location.id
        else:
            location = self.env['stock.location'].create({
                'name': "Stock"
            })
            location_id = location.id
        print("\n\n=========> ex location", location_id)
        if stock_take_id and location_id:
            all_product_lines = []
            inventory_lines = []
            inventory_id = self.env['stock.inventory'].create({
                'name': "Test For Inventory",
                'stock_take_id': stock_take_id,
                'location_id': location_id,
                'filter': "partial",
                'company_id': self.env.user.company_id.id,
            })
            print("\n\n=========>inventory_id", inventory_id.state)
            inventory_id.action_start()
            print("\n\n\n============>inventory start==========>")
            inventory_id.load_all_products()
            print("\n\n=========>loading all products========>")
            product_ids = self.env['product.product'].search([('type', '=', 'product')],order='id ASC', limit=2)
            all_product_ids = self.env['product.product'].search([('type', '=', 'product')], order='id DESC', limit=10)
            print("\n\n========>product_ids", product_ids)
            print("\n\n========>all_product_ids", all_product_ids)
            if all_product_ids:
                for rec in all_product_ids:
                    all_product_lines.append([0, 0, {'inventory_id': inventory_id.id,
                                                     'product_id': rec.id,
                                                     'location_id': location_id}])
            if product_ids:
                for each in product_ids:
                    inventory_lines.append([0, 0, {'inventory_id': inventory_id.id,
                                                   'product_id': each.id,
                                                   'location_id': location_id}])
            inventory_id.write({'line_ids': inventory_lines})
            if inventory_id.line_ids:
                inventory_id.action_reset_product_qty()
                print("\n\n============>Resetting product quantity to zero.")
            if inventory_id.state != "confirm":
                inventory_id.write({'all_product_ids': all_product_lines})
            inventory_id.run_comparison()
            print("\n\n============>Run Comparison.===============>")
            inventory_id.action_validate()
            print("\n\n========>All products in inventory_id.line_ids", inventory_id.line_ids)
            for each in inventory_id.line_ids:
                print("\n\n=========>each============>", each.product_id.name)

