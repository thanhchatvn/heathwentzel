from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from datetime import datetime
from datetime import date
@tagged('-at_install', 'post_install')
class TestJobPoOrder(TransactionCase):
    """
        Test for Job and PO Order.
    """
    print('\n\n--------test')
    def test_create_exam_data(self):
        # Create New Exam.
        print("\n\n\n=============>test for job purchase==================>")
        partner_id = self.env['res.partner'].browse(7082)
        if not partner_id:
            partner_id = self.env['res.partner'].search([], limit=1)
        print('\n\n=====partner_id', partner_id)
        test_clinic_exam = self.env['clinical.examination'].create({
            'partner_id': partner_id.id,
            'company_id': 3
        })
        print('Your test was succesfull!', test_clinic_exam)
        print('Your test was succesfull!', test_clinic_exam.partner_id, test_clinic_exam.partner_id.name)
        print('\n\n state', test_clinic_exam.state)
        test_clinic_exam.progress_examination()
        print('\n\n state11111', test_clinic_exam.state)

        clinical_final_rx_value = {'name': 'Test',
                                   'od_syh': 2,
                                   'od_cyl': 2,
                                   'od_axis': 2,
                                   'od_add': 2,
                                   'od_va': 2,
                                   'os_syh': 2,
                                   'os_cyl': 2,
                                   'os_axis': 2,
                                   'os_add': 2,
                                   'os_va': 2,
                                   'dispense': True,
                                   }

        test_clinic_exam.write({'clinical_final_rx_ids': [(0, 0, clinical_final_rx_value)]})
        print('\n\n----->test_clinic_exam.clinical_final_rx_ids------', test_clinic_exam.clinical_final_rx_ids)
        print('\n\n----->test_clinic_exam.clinical_final_rx_dis_ids------', test_clinic_exam.clinical_final_rx_dis_ids)

        wizard_final_rx_obj = self.env['wizard.final.rx']

        product_ids = self.env['product.template'].search([('type', '=', 'consu'),('categ_id.name', '=', 'Contact Lenses')
                                                           ], limit=2)
        location_id = self.env['stock.location'].search([('name', '=', 'stock')], limit=1)
        print("\n\n\n============>location_id",location_id)
        stock_picking_type_id = self.env['stock.picking.type'].search([], limit=1)
        stock_picking_id = self.env['stock.picking'].create({
            'location_id': 27,
            'location_dest_id': 27,
            'picking_type_id': stock_picking_type_id.id,
        })
        print("\n\n\n========>location_id==========",stock_picking_id.location_id.name)
        print("\n\n\n========>location_dest_id==========",stock_picking_id.location_dest_id.name)
        print("\n\n\n========>picking_type_id=========",stock_picking_id.picking_type_id.name)
        for rec in product_ids:
            product_id = self.env['product.product'].search([('product_tmpl_id', '=', rec.id)], limit=2)
            print("\n\n\n------->product_id", product_id)
            for each in product_id:
                self.env['stock.move'].create({
                    'name': 'Test move',
                    'product_id': each.id,
                    'product_uom_qty': 10.00,
                    'product_uom': each.uom_id.id,
                    'picking_id': stock_picking_id.id,
                    'location_id': 27,
                    'location_dest_id': 27})
        frame_product_id = self.env['product.template'].search([('default_code', '=', '43529')])
        if frame_product_id:
            new_frame_product_id = self.env['product.product'].search([('product_tmpl_id', '=', frame_product_id.id)], limit=1)
            self.env['stock.move'].create({
                'name': 'Test move',
                'product_id': new_frame_product_id.id,
                'product_uom_qty': 10.00,
                'product_uom': new_frame_product_id.uom_id.id,
                'picking_id': stock_picking_id.id,
                'location_id': 27,
                'location_dest_id': 27})
        print("\n\n\n==========>stock_picking_id",stock_picking_id.move_ids_without_package)
        for each in stock_picking_id.move_ids_without_package:
            print("\n\n\n==========>products", each.product_id.name)
        stock_picking_id.action_confirm()
        stock_picking_id.move_ids_without_package.write({'quantity_done': 10})
        print("\n\n========stock picking confirm==========")
        stock_picking_id.button_validate()
        print("\n\n========>stock validated========>")

        frame_product_id = self.env['product.template'].search([('default_code', '=', '43529')])
        if frame_product_id:
            wizard_final_rx_id = wizard_final_rx_obj.create(
                {'clinical_final_rx_id': test_clinic_exam.clinical_final_rx_dis_ids.ids[0],
                 'lens_type_od': [(6, 0, product_ids.ids)],
                 'lens_type_os': [(6, 0, product_ids.ids)],
                 'frame_model': frame_product_id.id,
                 'clinical_exam_id': test_clinic_exam.id
                 })
            print('\n\n=========wizard_final_rx_id', wizard_final_rx_id)
            wizard_final_rx_id.with_context(
                default_clinical_final_rx_id=test_clinic_exam.clinical_final_rx_dis_ids.ids[0]).fitting_details_apply()
            print('\n\n=======calllll')
            wizard_final_rx_id.submit_fitting_details()
        print('\n\n=========test line ------------', test_clinic_exam.dispensing_line_ids)
        for each in test_clinic_exam.dispensing_line_ids:
            print("\n\n\n----------products",each.product_id.name)
        invoice_id = test_clinic_exam.examination_invoice()
        print("\n\n========test_clinic_exam", test_clinic_exam.clinical_final_rx_dis_ids)
        print("\n\n========invoice_id", test_clinic_exam.invoice_id, test_clinic_exam.name)
        print("\n\n========invoice_id.invoice_line_ids",test_clinic_exam.invoice_id.invoice_line_ids)
        test_clinic_exam.clinical_final_rx_dis_ids.add_to_job_queue()
        job_id = self.env['project.task'].search([('exam_id', '=', test_clinic_exam.id)])
        print("\n\n\n=========>job_id", job_id)
        print("\n\n\n=========>job created successfully")
        purchase_order_id = self.env['purchase.order'].search([('project_task_id', '=', job_id.id)])
        print("\n\n\n========>purchase_order_id",purchase_order_id)
        for each in purchase_order_id.order_line:
            print("\n\n\n========>purchase_order_id", each.product_id.name)
        print("\n\n\n========>purchase order created and found.")