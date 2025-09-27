# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)

class P2PBaseBorrower(models.Model):
    """Base model cho Borrower - được kế thừa bởi các module khác"""
    _name = 'p2p.base.borrower'
    _description = 'Base Borrower Model'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    # Thông tin cơ bản
    name = fields.Char(string='Tên đầy đủ', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Đối tác', required=True)
    id_number = fields.Char(string='Số CMND/CCCD', tracking=True)
    phone = fields.Char(string='Số điện thoại', required=True)
    email = fields.Char(string='Email', required=True)
    date_of_birth = fields.Date(string='Ngày sinh', required=True)
    gender = fields.Selection([
        ('male', 'Nam'),
        ('female', 'Nữ'),
        ('other', 'Khác')
    ], string='Giới tính', required=True)
    
    # Thông tin tài chính cơ bản
    monthly_income = fields.Float(string='Thu nhập hàng tháng', digits=(16, 2))
    employment_status = fields.Selection([
        ('employed', 'Đang làm việc'),
        ('self_employed', 'Tự kinh doanh'),
        ('business_owner', 'Chủ doanh nghiệp'),
        ('unemployed', 'Đang thất nghiệp')
    ], string='Tình trạng việc làm')
    
    # Trạng thái
    active = fields.Boolean(default=True, string='Hoạt động')
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('confirmed', 'Đã xác nhận'),
        ('done', 'Hoàn thành')
    ], string='Trạng thái', default='draft', tracking=True)
    
    _sql_constraints = [
        ('id_number_unique', 'UNIQUE(id_number)', 'Số CMND/CCCD đã tồn tại!')
    ]

class P2PBaseLoan(models.Model):
    """Base model cho Loan - được kế thừa bởi các module khác"""
    _name = 'p2p.base.loan'
    _description = 'Base Loan Model'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    # Thông tin cơ bản
    name = fields.Char(string='Mã khoản vay', required=True, default='New', readonly=True)
    borrower_id = fields.Many2one('p2p.base.borrower', string='Người vay', required=True, tracking=True)
    amount = fields.Float(string='Số tiền vay', required=True, tracking=True)
    term = fields.Integer(string='Kỳ hạn (tháng)', required=True, default=12)
    interest_rate = fields.Float(string='Lãi suất (%/năm)', required=True, tracking=True)
    start_date = fields.Date(string='Ngày bắt đầu', default=fields.Date.today)
    end_date = fields.Date(string='Ngày đáo hạn', compute='_compute_end_date', store=True)
    
    # Trạng thái cơ bản
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('waiting_approval', 'Chờ duyệt'),
        ('approved', 'Đã duyệt'),
        ('disbursed', 'Đã giải ngân'),
        ('in_progress', 'Đang trả nợ'),
        ('paid', 'Đã hoàn thành'),
        ('defaulted', 'Quá hạn'),
        ('cancelled', 'Đã hủy')
    ], string='Trạng thái', default='draft', tracking=True)
    
    # Tính toán cơ bản
    monthly_payment = fields.Float(string='Trả góp hàng tháng', compute='_compute_monthly_payment', store=True)
    total_interest = fields.Float(string='Tổng lãi', compute='_compute_total_interest', store=True)
    total_payment = fields.Float(string='Tổng thanh toán', compute='_compute_total_payment', store=True)
    
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
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('p2p.base.loan') or 'New'
        return super(P2PBaseLoan, self).create(vals)

class P2PBaseInvestor(models.Model):
    """Base model cho Investor - được kế thừa bởi các module khác"""
    _name = 'p2p.base.investor'
    _description = 'Base Investor Model'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    # Thông tin cơ bản
    name = fields.Char(string='Tên đầy đủ', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Đối tác', required=True)
    phone = fields.Char(string='Số điện thoại', required=True)
    email = fields.Char(string='Email', required=True)
    
    # Thông tin tài chính
    investment_capacity = fields.Float(string='Khả năng đầu tư', digits=(16, 2))
    risk_tolerance = fields.Selection([
        ('low', 'Thấp'),
        ('medium', 'Trung bình'),
        ('high', 'Cao')
    ], string='Khả năng chấp nhận rủi ro', default='medium')
    
    # Trạng thái
    active = fields.Boolean(default=True, string='Hoạt động')
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('confirmed', 'Đã xác nhận'),
        ('active', 'Hoạt động'),
        ('suspended', 'Tạm dừng')
    ], string='Trạng thái', default='draft', tracking=True)

class P2PBaseInvestment(models.Model):
    """Base model cho Investment - được kế thừa bởi các module khác"""
    _name = 'p2p.base.investment'
    _description = 'Base Investment Model'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    # Thông tin cơ bản
    name = fields.Char(string='Mã đầu tư', required=True, default='New', readonly=True)
    investor_id = fields.Many2one('p2p.base.investor', string='Nhà đầu tư', required=True, tracking=True)
    loan_id = fields.Many2one('p2p.base.loan', string='Khoản vay', required=True, tracking=True)
    amount = fields.Float(string='Số tiền đầu tư', required=True, tracking=True)
    investment_date = fields.Date(string='Ngày đầu tư', default=fields.Date.today)
    
    # Trạng thái
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('confirmed', 'Đã xác nhận'),
        ('active', 'Đang hoạt động'),
        ('completed', 'Hoàn thành'),
        ('cancelled', 'Đã hủy')
    ], string='Trạng thái', default='draft', tracking=True)
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('p2p.base.investment') or 'New'
        return super(P2PBaseInvestment, self).create(vals)
