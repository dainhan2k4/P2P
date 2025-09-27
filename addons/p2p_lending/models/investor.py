from odoo import models, fields, api

class P2PInvestor(models.Model):
    _name = 'p2p.investor'  # Main investor model
    _inherit = ['p2p.base.investor']  # Inherit from base model
    _description = 'Nhà đầu tư (Extended)'

    name = fields.Char(string='Tên', related='partner_id.name', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Đối tác', required=True)
    id_number = fields.Char(string='Số CMND/CCCD')
    date_of_birth = fields.Date(string='Ngày sinh')
    phone = fields.Char(string='Điện thoại')
    email = fields.Char(string='Email')
    address = fields.Text(string='Địa chỉ')
    investment_ids = fields.One2many('p2p.investment', 'investor_id', string='Đầu tư')
    investment_count = fields.Integer(string='Số lượng đầu tư', compute='_compute_investment_count', store=True)
    total_invested = fields.Float(string='Tổng đầu tư', compute='_compute_total_invested', store=True)
    active = fields.Boolean(default=True, string='Hoạt động')

    @api.depends('investment_ids')
    def _compute_investment_count(self):
        for investor in self:
            investor.investment_count = len(investor.investment_ids)

    @api.depends('investment_ids.amount')
    def _compute_total_invested(self):
        for investor in self:
            investor.total_invested = sum(investor.investment_ids.mapped('amount'))

    def action_view_investments(self):
        """
        Open the list view of investments for this investor
        """
        self.ensure_one()
        return {
            'name': 'Đầu tư',
            'type': 'ir.actions.act_window',
            'res_model': 'p2p.investment',
            'view_mode': 'list,form',
            'domain': [('investor_id', '=', self.id)],
            'context': {'default_investor_id': self.id},
        }

    _sql_constraints = [
        ('partner_uniq', 'unique(partner_id)', 'Mỗi đối tác chỉ được tạo 1 nhà đầu tư!'),
    ]