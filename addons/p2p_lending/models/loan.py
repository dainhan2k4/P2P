from odoo import models, fields, api
from datetime import date, timedelta

class P2PLoan(models.Model):
    _name = 'p2p.loan'  # Main loan model
    _inherit = ['p2p.base.loan']  # Inherit from base model
    _description = 'Khoản vay (Extended)'

    name = fields.Char(string='Mã khoản vay', required=True, default='New', readonly=True)
    borrower_id = fields.Many2one('p2p.borrower', string='Người vay', required=True, tracking=True)
    amount = fields.Float(string='Số tiền vay', required=True, tracking=True)
    term = fields.Integer(string='Kỳ hạn (tháng)', required=True, default=12)
    interest_rate = fields.Float(string='Lãi suất (%/năm)', required=True, tracking=True)
    start_date = fields.Date(string='Ngày bắt đầu', default=fields.Date.today())
    end_date = fields.Date(string='Ngày đáo hạn', compute='_compute_end_date', store=True)
    purpose = fields.Selection([
        ('debt_consolidation', 'Trả nợ'),
        ('home_improvement', 'Cải tạo nhà'),
        ('business', 'Kinh doanh'),
        ('education', 'Giáo dục'),
        ('medical', 'Y tế'),
        ('other', 'Khác')
    ], string='Mục đích vay', required=True, default='other')
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('waiting_approval', 'Chờ duyệt'),
        ('funding', 'Đang gọi vốn'),
        ('funded', 'Đã gọi đủ vốn'),
        ('disbursed', 'Đã giải ngân'),
        ('in_progress', 'Đang trả nợ'),
        ('paid', 'Đã hoàn thành'),
        ('defaulted', 'Quá hạn'),
        ('cancelled', 'Đã hủy')
    ], string='Trạng thái', default='draft', tracking=True)
    monthly_payment = fields.Float(string='Trả góp hàng tháng', compute='_compute_monthly_payment', store=True)
    total_interest = fields.Float(string='Tổng lãi', compute='_compute_total_interest', store=True)
    total_payment = fields.Float(string='Tổng thanh toán', compute='_compute_total_payment', store=True)
    investment_ids = fields.One2many('p2p.investment', 'loan_id', string='Đầu tư')
    funded_amount = fields.Float(string='Số tiền đã gọi được', compute='_compute_funded_amount', store=True)
    funding_progress = fields.Float(string='Tiến độ gọi vốn', compute='_compute_funding_progress', store=True)
    payment_schedule_ids = fields.One2many('p2p.loan.payment', 'loan_id', string='Lịch trả nợ')

    @api.depends('term', 'start_date')
    def _compute_end_date(self):
        for loan in self:
            if loan.start_date and loan.term:
                loan.end_date = loan.start_date + timedelta(days=loan.term*30)

    @api.depends('amount', 'interest_rate', 'term')
    def _compute_monthly_payment(self):
        for loan in self:
            if loan.amount and loan.interest_rate and loan.term:
                monthly_rate = loan.interest_rate / 100 / 12
                loan.monthly_payment = (loan.amount * monthly_rate * (1 + monthly_rate)**loan.term) / ((1 + monthly_rate)**loan.term - 1)
            else:
                loan.monthly_payment = 0

    @api.depends('monthly_payment', 'term')
    def _compute_total_payment(self):
        for loan in self:
            loan.total_payment = loan.monthly_payment * loan.term

    @api.depends('total_payment', 'amount')
    def _compute_total_interest(self):
        for loan in self:
            loan.total_interest = loan.total_payment - loan.amount

    @api.depends('investment_ids.amount')
    def _compute_funded_amount(self):
        for loan in self:
            loan.funded_amount = sum(investment.amount for investment in loan.investment_ids)

    @api.depends('funded_amount', 'amount')
    def _compute_funding_progress(self):
        for loan in self:
            loan.funding_progress = (loan.funded_amount / loan.amount * 100) if loan.amount > 0 else 0

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('p2p.loan') or 'New'
        return super(P2PLoan, self).create(vals)

    def action_submit_for_approval(self):
        self.write({'state': 'waiting_approval'})

    def action_approve(self):
        self.write({'state': 'funding'})

    def action_fund(self):
        self.write({'state': 'funded'})

    def action_disburse(self):
        self.write({'state': 'disbursed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def generate_payment_schedule(self):
        # Tạo lịch trả nợ
        self.payment_schedule_ids.unlink()  # Xóa lịch cũ nếu có
        payment_date = self.start_date
        balance = self.amount
        
        for i in range(1, self.term + 1):
            # Tính lãi tháng hiện tại
            monthly_interest = balance * (self.interest_rate / 100 / 12)
            principal = self.monthly_payment - monthly_interest
            
            # Điều chỉnh số tiền gốc của kỳ cuối
            if i == self.term:
                principal = balance
                monthly_interest = self.monthly_payment - principal
            
            # Cập nhật số dư
            balance -= principal
            
            # Tạo bản ghi thanh toán
            self.env['p2p.loan.payment'].create({
                'loan_id': self.id,
                'payment_date': payment_date,
                'amount': self.monthly_payment,
                'principal': principal,
                'interest': monthly_interest,
                'balance': balance,
                'state': 'unpaid'
            })
            
            # Cập nhật ngày thanh toán tiếp theo
            payment_date = payment_date + timedelta(days=30)