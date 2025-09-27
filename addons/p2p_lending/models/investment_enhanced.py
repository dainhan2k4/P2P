# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date, datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class P2PInvestmentEnhanced(models.Model):
    """Enhanced Investment Model với đầy đủ thông tin cho P2P Lending"""
    _name = 'p2p.investment.enhanced'
    _inherit = ['p2p.investment']
    _description = 'Đầu tư nâng cao'
    
    # ===========================================
    # THÔNG TIN CƠ BẢN
    # ===========================================
    
    name = fields.Char(string='Mã đầu tư', required=True, default='New', readonly=True)
    investor_id = fields.Many2one('p2p.investor.enhanced', string='Nhà đầu tư', required=True)
    loan_id = fields.Many2one('p2p.loan', string='Khoản vay', required=True)
    
    # Thông tin liên quan
    borrower_id = fields.Many2one('p2p.borrower', string='Người vay', related='loan_id.borrower_id', store=True)
    borrower_name = fields.Char(string='Tên người vay', related='borrower_id.name', store=True)
    loan_amount = fields.Float(string='Số tiền khoản vay', related='loan_id.amount', store=True)
    loan_term = fields.Integer(string='Kỳ hạn khoản vay (tháng)', related='loan_id.term', store=True)
    loan_interest_rate = fields.Float(string='Lãi suất khoản vay (%)', related='loan_id.interest_rate', store=True)
    
    # ===========================================
    # THÔNG TIN ĐẦU TƯ
    # ===========================================
    
    # Số tiền đầu tư
    amount = fields.Float(string='Số tiền đầu tư', required=True, digits=(16, 2))
    amount_original = fields.Float(string='Số tiền đầu tư ban đầu', digits=(16, 2))
    amount_remaining = fields.Float(string='Số tiền còn lại', digits=(16, 2), compute='_compute_amount_remaining', store=True)
    
    # Tỷ lệ đầu tư
    investment_percentage = fields.Float(string='Tỷ lệ đầu tư (%)', digits=(5, 2), compute='_compute_investment_percentage', store=True)
    loan_funding_percentage = fields.Float(string='Tỷ lệ gọi vốn (%)', digits=(5, 2), compute='_compute_loan_funding_percentage', store=True)
    
    # Ngày tháng
    investment_date = fields.Date(string='Ngày đầu tư', default=fields.Date.today, required=True)
    expected_maturity_date = fields.Date(string='Ngày đáo hạn dự kiến', compute='_compute_expected_maturity_date', store=True)
    actual_maturity_date = fields.Date(string='Ngày đáo hạn thực tế')
    
    # ===========================================
    # THÔNG TIN LỢI NHUẬN
    # ===========================================
    
    # Lãi suất và lợi nhuận
    interest_rate = fields.Float(string='Lãi suất đầu tư (%)', digits=(5, 2), compute='_compute_interest_rate', store=True)
    expected_interest = fields.Float(string='Lãi dự kiến', digits=(16, 2), compute='_compute_expected_interest', store=True)
    actual_interest = fields.Float(string='Lãi thực tế', digits=(16, 2), default=0.0)
    total_returns = fields.Float(string='Tổng lợi nhuận', digits=(16, 2), compute='_compute_total_returns', store=True)
    
    # ROI
    roi_percentage = fields.Float(string='ROI (%)', digits=(5, 2), compute='_compute_roi', store=True)
    annualized_roi = fields.Float(string='ROI năm (%)', digits=(5, 2), compute='_compute_annualized_roi', store=True)
    
    # ===========================================
    # THÔNG TIN THANH TOÁN
    # ===========================================
    
    # Thanh toán
    payment_schedule_ids = fields.One2many('p2p.investment.payment', 'investment_id', string='Lịch thanh toán')
    total_paid = fields.Float(string='Tổng đã thanh toán', digits=(16, 2), compute='_compute_payment_stats', store=True)
    total_pending = fields.Float(string='Tổng chờ thanh toán', digits=(16, 2), compute='_compute_payment_stats', store=True)
    next_payment_date = fields.Date(string='Ngày thanh toán tiếp theo', compute='_compute_next_payment_date', store=True)
    next_payment_amount = fields.Float(string='Số tiền thanh toán tiếp theo', digits=(16, 2), compute='_compute_next_payment_amount', store=True)
    
    # ===========================================
    # THÔNG TIN RỦI RO
    # ===========================================
    
    # Đánh giá rủi ro
    risk_level = fields.Selection([
        ('very_low', 'Rất thấp'),
        ('low', 'Thấp'),
        ('medium', 'Trung bình'),
        ('high', 'Cao'),
        ('very_high', 'Rất cao')
    ], string='Mức độ rủi ro', compute='_compute_risk_level', store=True)
    
    risk_score = fields.Float(string='Điểm rủi ro', digits=(5, 2), compute='_compute_risk_score', store=True)
    borrower_credit_score = fields.Float(string='Điểm tín dụng người vay', related='borrower_id.credit_score_ml', store=True)
    
    # Bảo hiểm và bảo đảm
    insurance_coverage = fields.Float(string='Bảo hiểm (%)', digits=(5, 2), default=0.0)
    collateral_value = fields.Float(string='Giá trị tài sản thế chấp', digits=(16, 2))
    guarantee_amount = fields.Float(string='Số tiền bảo lãnh', digits=(16, 2))
    
    # ===========================================
    # THÔNG TIN TRẠNG THÁI
    # ===========================================
    
    # Trạng thái đầu tư
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('pending', 'Chờ xác nhận'),
        ('confirmed', 'Đã xác nhận'),
        ('active', 'Đang hoạt động'),
        ('matured', 'Đã đáo hạn'),
        ('defaulted', 'Vỡ nợ'),
        ('cancelled', 'Đã hủy'),
        ('suspended', 'Tạm dừng')
    ], string='Trạng thái', default='draft', tracking=True)
    
    # Trạng thái thanh toán
    payment_status = fields.Selection([
        ('on_time', 'Đúng hạn'),
        ('late', 'Trễ hạn'),
        ('defaulted', 'Vỡ nợ'),
        ('completed', 'Hoàn thành')
    ], string='Trạng thái thanh toán', compute='_compute_payment_status', store=True)
    
    # ===========================================
    # THÔNG TIN BỔ SUNG
    # ===========================================
    
    # Mục đích đầu tư
    investment_purpose = fields.Selection([
        ('income', 'Tạo thu nhập'),
        ('growth', 'Tăng trưởng'),
        ('diversification', 'Đa dạng hóa'),
        ('short_term', 'Ngắn hạn'),
        ('long_term', 'Dài hạn')
    ], string='Mục đích đầu tư', default='income')
    
    # Nguồn vốn
    capital_source = fields.Selection([
        ('savings', 'Tiết kiệm'),
        ('salary', 'Lương'),
        ('business', 'Kinh doanh'),
        ('investment', 'Đầu tư khác'),
        ('loan', 'Vay mượn'),
        ('other', 'Khác')
    ], string='Nguồn vốn', default='savings')
    
    # Ghi chú
    notes = fields.Text(string='Ghi chú')
    internal_notes = fields.Text(string='Ghi chú nội bộ')
    
    # ===========================================
    # THÔNG TIN HỆ THỐNG
    # ===========================================
    
    # Thời gian
    create_date = fields.Datetime(string='Ngày tạo', default=fields.Datetime.now)
    write_date = fields.Datetime(string='Ngày cập nhật', default=fields.Datetime.now)
    last_payment_date = fields.Date(string='Ngày thanh toán cuối')
    
    # Người tạo/cập nhật
    create_uid = fields.Many2one('res.users', string='Người tạo')
    write_uid = fields.Many2one('res.users', string='Người cập nhật')
    
    # ===========================================
    # COMPUTED FIELDS
    # ===========================================
    
    @api.depends('amount', 'total_paid')
    def _compute_amount_remaining(self):
        for investment in self:
            investment.amount_remaining = investment.amount - investment.total_paid
    
    @api.depends('amount', 'loan_id.amount')
    def _compute_investment_percentage(self):
        for investment in self:
            if investment.loan_id.amount > 0:
                investment.investment_percentage = (investment.amount / investment.loan_id.amount) * 100
            else:
                investment.investment_percentage = 0.0
    
    @api.depends('loan_id.funded_amount', 'loan_id.amount')
    def _compute_loan_funding_percentage(self):
        for investment in self:
            if investment.loan_id.amount > 0:
                investment.loan_funding_percentage = (investment.loan_id.funded_amount / investment.loan_id.amount) * 100
            else:
                investment.loan_funding_percentage = 0.0
    
    @api.depends('investment_date', 'loan_id.term')
    def _compute_expected_maturity_date(self):
        for investment in self:
            if investment.investment_date and investment.loan_id.term:
                investment.expected_maturity_date = investment.investment_date + timedelta(days=investment.loan_id.term * 30)
            else:
                investment.expected_maturity_date = False
    
    @api.depends('loan_id.interest_rate')
    def _compute_interest_rate(self):
        for investment in self:
            investment.interest_rate = investment.loan_id.interest_rate if investment.loan_id.interest_rate else 0.0
    
    @api.depends('amount', 'interest_rate', 'loan_id.term')
    def _compute_expected_interest(self):
        for investment in self:
            if investment.amount and investment.interest_rate and investment.loan_id.term:
                investment.expected_interest = investment.amount * (investment.interest_rate / 100) * (investment.loan_id.term / 12)
            else:
                investment.expected_interest = 0.0
    
    @api.depends('actual_interest', 'amount')
    def _compute_total_returns(self):
        for investment in self:
            investment.total_returns = investment.actual_interest
    
    @api.depends('total_returns', 'amount')
    def _compute_roi(self):
        for investment in self:
            if investment.amount > 0:
                investment.roi_percentage = (investment.total_returns / investment.amount) * 100
            else:
                investment.roi_percentage = 0.0
    
    @api.depends('roi_percentage', 'loan_id.term')
    def _compute_annualized_roi(self):
        for investment in self:
            if investment.loan_id.term > 0:
                investment.annualized_roi = (investment.roi_percentage * 12) / investment.loan_id.term
            else:
                investment.annualized_roi = 0.0
    
    @api.depends('borrower_credit_score')
    def _compute_risk_level(self):
        for investment in self:
            if investment.borrower_credit_score >= 750:
                investment.risk_level = 'very_low'
            elif investment.borrower_credit_score >= 700:
                investment.risk_level = 'low'
            elif investment.borrower_credit_score >= 650:
                investment.risk_level = 'medium'
            elif investment.borrower_credit_score >= 600:
                investment.risk_level = 'high'
            else:
                investment.risk_level = 'very_high'
    
    @api.depends('borrower_credit_score', 'loan_id.amount', 'amount')
    def _compute_risk_score(self):
        for investment in self:
            # Tính điểm rủi ro dựa trên credit score và tỷ lệ đầu tư
            base_score = 100 - investment.borrower_credit_score
            if investment.loan_id.amount > 0:
                investment_ratio = investment.amount / investment.loan_id.amount
                investment.risk_score = base_score + (investment_ratio * 10)
            else:
                investment.risk_score = base_score
    
    @api.depends('payment_schedule_ids', 'payment_schedule_ids.state')
    def _compute_payment_stats(self):
        for investment in self:
            payments = investment.payment_schedule_ids
            investment.total_paid = sum(payments.filtered(lambda p: p.state == 'paid').mapped('amount'))
            investment.total_pending = sum(payments.filtered(lambda p: p.state == 'pending').mapped('amount'))
    
    @api.depends('payment_schedule_ids', 'payment_schedule_ids.payment_date')
    def _compute_next_payment_date(self):
        for investment in self:
            pending_payments = investment.payment_schedule_ids.filtered(lambda p: p.state == 'pending')
            if pending_payments:
                investment.next_payment_date = min(pending_payments.mapped('payment_date'))
            else:
                investment.next_payment_date = False
    
    @api.depends('payment_schedule_ids', 'payment_schedule_ids.amount')
    def _compute_next_payment_amount(self):
        for investment in self:
            if investment.next_payment_date:
                next_payment = investment.payment_schedule_ids.filtered(
                    lambda p: p.payment_date == investment.next_payment_date and p.state == 'pending'
                )
                investment.next_payment_amount = next_payment.amount if next_payment else 0.0
            else:
                investment.next_payment_amount = 0.0
    
    @api.depends('payment_schedule_ids', 'payment_schedule_ids.state', 'payment_schedule_ids.payment_date')
    def _compute_payment_status(self):
        for investment in self:
            today = fields.Date.today()
            payments = investment.payment_schedule_ids
            
            if not payments:
                investment.payment_status = 'on_time'
            elif all(p.state == 'paid' for p in payments):
                investment.payment_status = 'completed'
            elif any(p.state == 'defaulted' for p in payments):
                investment.payment_status = 'defaulted'
            elif any(p.state == 'pending' and p.payment_date < today for p in payments):
                investment.payment_status = 'late'
            else:
                investment.payment_status = 'on_time'
    
    # ===========================================
    # METHODS
    # ===========================================
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('p2p.investment.enhanced') or 'New'
        return super(P2PInvestmentEnhanced, self).create(vals)
    
    def action_confirm(self):
        """Xác nhận đầu tư"""
        self.write({'state': 'confirmed'})
        # Cập nhật trạng thái khoản vay
        self.loan_id._check_funding_status()
    
    def action_activate(self):
        """Kích hoạt đầu tư"""
        self.write({'state': 'active'})
        # Tạo lịch thanh toán
        self._create_payment_schedule()
    
    def action_mature(self):
        """Đáo hạn đầu tư"""
        self.write({
            'state': 'matured',
            'actual_maturity_date': fields.Date.today()
        })
    
    def action_default(self):
        """Đánh dấu vỡ nợ"""
        self.write({'state': 'defaulted'})
    
    def action_cancel(self):
        """Hủy đầu tư"""
        self.write({'state': 'cancelled'})
    
    def _create_payment_schedule(self):
        """Tạo lịch thanh toán"""
        # Xóa lịch cũ
        self.payment_schedule_ids.unlink()
        
        # Tạo lịch mới
        payment_date = self.investment_date
        for i in range(1, self.loan_id.term + 1):
            payment_amount = self.amount * (self.interest_rate / 100 / 12)
            
            self.env['p2p.investment.payment'].create({
                'investment_id': self.id,
                'payment_date': payment_date,
                'amount': payment_amount,
                'state': 'pending'
            })
            
            # Cập nhật ngày thanh toán tiếp theo
            payment_date = payment_date + timedelta(days=30)
    
    def action_view_payments(self):
        """Xem lịch thanh toán"""
        return {
            'name': 'Lịch thanh toán',
            'type': 'ir.actions.act_window',
            'res_model': 'p2p.investment.payment',
            'view_mode': 'tree,form',
            'domain': [('investment_id', '=', self.id)],
            'context': {'default_investment_id': self.id}
        }
    
    def action_view_loan(self):
        """Xem khoản vay"""
        return {
            'name': 'Khoản vay',
            'type': 'ir.actions.act_window',
            'res_model': 'p2p.loan',
            'view_mode': 'form',
            'res_id': self.loan_id.id
        }
    
    def action_view_borrower(self):
        """Xem người vay"""
        return {
            'name': 'Người vay',
            'type': 'ir.actions.act_window',
            'res_model': 'p2p.borrower',
            'view_mode': 'form',
            'res_id': self.borrower_id.id
        }
    
    # ===========================================
    # CONSTRAINTS
    # ===========================================
    
    _sql_constraints = [
        ('amount_positive', 'CHECK(amount > 0)', 'Số tiền đầu tư phải lớn hơn 0!'),
        ('investment_date_future', 'CHECK(investment_date <= CURRENT_DATE)', 'Ngày đầu tư không được trong tương lai!'),
    ]
