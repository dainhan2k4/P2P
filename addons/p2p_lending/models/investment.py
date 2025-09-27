from odoo import models, fields, api

class P2PInvestment(models.Model):
    _name = 'p2p.investment'  # Main investment model
    _inherit = ['p2p.base.investment']  # Inherit from base model
    _description = 'Đầu tư (Extended)'

    name = fields.Char(string='Mã đầu tư', required=True, default='New', readonly=True)
    investor_id = fields.Many2one('p2p.investor', string='Nhà đầu tư', required=True)
    investor_partner_id = fields.Many2one('res.partner', string='Đối tác', related='investor_id.partner_id', store=True, readonly=True)
    loan_id = fields.Many2one('p2p.loan', string='Khoản vay', required=True)
    amount = fields.Float(string='Số tiền đầu tư', required=True)
    date = fields.Date(string='Ngày đầu tư', default=fields.Date.today())
    expected_return = fields.Float(string='Lợi nhuận kỳ vọng', compute='_compute_expected_return', store=True)
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('confirmed', 'Đã xác nhận'),
        ('completed', 'Hoàn thành'),
        ('cancelled', 'Đã hủy')
    ], string='Trạng thái', default='draft', tracking=True)
    payment_ids = fields.One2many('p2p.investment.payment', 'investment_id', string='Thanh toán')

    @api.depends('amount', 'loan_id.interest_rate', 'loan_id.term_months')
    def _compute_expected_return(self):
        for inv in self:
            if inv.amount and inv.loan_id.interest_rate and inv.loan_id.term_months:
                inv.expected_return = inv.amount * (inv.loan_id.interest_rate / 100) * (inv.loan_id.term_months / 12)
            else:
                inv.expected_return = 0

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('p2p.investment') or 'New'
        return super(P2PInvestment, self).create(vals)

    def action_confirm(self):
        self.write({'state': 'confirmed'})
        # Cập nhật trạng thái khoản vay nếu đã gọi đủ vốn
        self.loan_id._check_funding_status()

    def action_cancel(self):
        self.write({'state': 'cancelled'})