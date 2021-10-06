import logging
from odoo import fields, models, api

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    calendar_bg_color = fields.Char(string="Calendar Background Color")
    calendar_text_color = fields.Char(string="Calendar Text Color")
    display_roster_view = fields.Boolean(string="Display in roster view", default=True)
    active_roster_view = fields.Boolean(string="Active in roster view", default=True)
    optometrist_ids = fields.One2many('optometrist.user', 'optometrist_id', string="Optometrists")

    @api.multi
    def get_optometrist_ids(self):
        optometrist_list = []
        for rec in self.optometrist_ids:
            if rec:
                optometrist_list.append({'id': rec.partner_id.id,
                                         'name': rec.partner_id.name,
                                         'image': rec.partner_id.image,
                                         'calendar_bg_color': rec.partner_id.calendar_bg_color,
                                         'calendar_text_color': rec.partner_id.calendar_text_color,
                                         'active_roster_view': rec.active_roster_view,
                                         'display_roster_view': rec.active_roster_view})
        return optometrist_list

    @api.multi
    def prepare_auto_complete(self):
        prepare_optometrist_list = []
        old_optometrist_list = []
        for rec in self.optometrist_ids:
            old_optometrist_list.append(rec.partner_id.id)

        optometrists = self.search([('optometrist', '=', True), ('id', 'not in', old_optometrist_list)])
        if optometrists:
            for rec in optometrists:
                prepare_optometrist_list.append({'id': rec.id,
                                                'name': rec.name,
                                                 'image': rec.image,
                                                 'calendar_bg_color': rec.calendar_bg_color,
                                                 'calendar_text_color': rec.calendar_text_color,
                                                 'active_roster_view': rec.active_roster_view,
                                                 'display_roster_view': rec.active_roster_view})
        return prepare_optometrist_list


class OptometristUser(models.Model):
    _name = 'optometrist.user'
    _description = 'Optometrist User'

    optometrist_id = fields.Many2one('res.users')
    partner_id = fields.Many2one('res.users', string='Optometrist')
    display_roster_view = fields.Boolean(string="Display in roster view")
    active_roster_view = fields.Boolean(string="Active in roster view")

    @api.multi
    def filter_optometrist(self, id, vals):
        record = self.env['res.users'].search([('id', '=', self.id)])
        if record:
            for each in record.optometrist_ids.filtered(lambda l: l.partner_id.id == id):
                if each.active_roster_view:
                    each.active_roster_view = False
                else:
                    each.active_roster_view = True

    @api.multi
    def remove_optometrist(self, id):
        record = self.env['res.users'].search([('id', '=', self.id)])
        if record:
            for each in record.optometrist_ids.filtered(lambda l: l.partner_id.id == id):
                each.unlink()

    @api.multi
    def add_optometrist(self, id):
        record = self.env['res.users'].search([('id', '=', self.id)])
        add_record_id = self.env['res.users'].search([('id', '=', id)])
        if record:
            record.write({
                'optometrist_ids': [(0, 0, {'partner_id': add_record_id.id,
                                            'display_roster_view': True,
                                            'active_roster_view': True})]
            })



class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.model
    def create(self, vals):

        vals.update({'parent_id': False})
        res = super(MailMessage, self).create(vals)
        return res
