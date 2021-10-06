# from . import models

from odoo import api, SUPERUSER_ID

def _default_chart_template_id(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    default_template_id = env.ref('l10n_za_humint_sub.default_chart_template_humint', raise_if_not_found=False)
    if default_template_id:
        env.user.company_id.sudo().write({
            'chart_template_id': default_template_id.id,
        })
        env['ir.config_parameter'].sudo().set_param('account.chart_template_id', default_template_id.id)
        default_template_id.sudo().load_for_current_company(15.0, 15.0)


