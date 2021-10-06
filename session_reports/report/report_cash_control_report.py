from odoo import api, fields, models


class CashControlReport(models.AbstractModel):
    _name = 'report.session_reports.report_cash_control_report'
    _description = "Session Cash Control Report"


    @api.model
    def _get_report_values(self, docids, data=None):
        sale_data = self.get_sale_count(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'session.session',
            'order_data':sale_data,
            'docs': self.env['session.session'].browse(docids),
            'report_type': data.get('report_type') if data else '',
        }

    def get_sale_count(self, docids=False):
        if docids:
            sessions = self.env['session.session'].browse(docids)
            values = {}
            for session in sessions:
                orders = self.env['sale.order'].search([('user_id','=',session.user_id.id)])
                orders = orders.filtered(lambda x: x.create_date>=session.opening_date and x.create_date<=session.closing_date)
                cash_orders = orders.filtered(lambda x:x.sale_type == 'cash')
                layby_orders = orders.filtered(lambda x:x.sale_type == 'lay_by')
                hp_orders = orders.filtered(lambda x:x.sale_type == 'hire_purchase')
                values[session.id]={
                    'cash':[len(cash_orders),sum(cash_orders.mapped('amount_total'))],
                    'lay_by':[len(layby_orders),sum(layby_orders.mapped('amount_total'))],
                    'hp':[len(hp_orders),sum(hp_orders.mapped('amount_total'))]
                }
            return values
