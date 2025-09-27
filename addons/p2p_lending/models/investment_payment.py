# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date, datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class P2PInvestmentPayment(models.Model):
    """Model quản lý thanh toán đầu tư"""
    _name = 'p2p.investment.payment'
    _description = 'Thanh toán đầu tư'
    _order = 'payment_date desc'
    
    # ===========================================
    # THÔNG TIN CƠ BẢN
    # ===========================================
    
    name = fields.Char(string='Mã thanh toán', required=True, default='New', readonly=True)
    investment_id = fields.Many2one('p2p.investment.enhanced', string='Đầu tư', required=True, ondelete='cascade')
    investor_id = fields.Many2one('p2p.investor.enhanced', string='Nhà đầu tư', related='investment_id.investor_id', store=True)
    loan_id = fields.Many2one('p2p.loan', string='Khoản vay', related='investment_id.loan_id', store=True)
    
    # ===========================================
    # THÔNG TIN THANH TOÁN
    # ===========================================
    
    # Số tiền
    amount = fields.Float(string='Số tiền thanh toán', required=True, digits=(16, 2))
    principal_amount = fields.Float(string='Số tiền gốc', digits=(16, 2), compute='_compute_principal_interest', store=True)
    interest_amount = fields.Float(string='Số tiền lãi', digits=(16, 2), compute='_compute_principal_interest', store=True)
    
    # Ngày tháng
    payment_date = fields.Date(string='Ngày thanh toán', required=True)
    due_date = fields.Date(string='Ngày đến hạn', required=True)
    actual_payment_date = fields.Date(string='Ngày thanh toán thực tế')
    
    # ===========================================
    # THÔNG TIN TRẠNG THÁI
    # ===========================================
    
    # Trạng thái thanh toán
    state = fields.Selection([
        ('pending', 'Chờ thanh toán'),
        ('paid', 'Đã thanh toán'),
        ('late', 'Trễ hạn'),
        ('defaulted', 'Vỡ nợ'),
        ('cancelled', 'Đã hủy')
    ], string='Trạng thái', default='pending', tracking=True)
    
    # Trạng thái xử lý
    processing_status = fields.Selection([
        ('pending', 'Chờ xử lý'),
        ('processing', 'Đang xử lý'),
        ('completed', 'Hoàn thành'),
        ('failed', 'Thất bại')
    ], string='Trạng thái xử lý', default='pending')
    
    # ===========================================
    # THÔNG TIN BỔ SUNG
    # ===========================================
    
    # Loại thanh toán
    payment_type = fields.Selection([
        ('monthly', 'Hàng tháng'),
        ('quarterly', 'Quý'),
        ('semi_annual', 'Nửa năm'),
        ('annual', 'Hàng năm'),
        ('final', 'Cuối kỳ'),
        ('early', 'Trả trước'),
        ('late_fee', 'Phí trễ hạn')
    ], string='Loại thanh toán', default='monthly')
    
    # Phương thức thanh toán
    payment_method = fields.Selection([
        ('bank_transfer', 'Chuyển khoản ngân hàng'),
        ('cash', 'Tiền mặt'),
        ('check', 'Séc'),
        ('credit_card', 'Thẻ tín dụng'),
        ('digital_wallet', 'Ví điện tử'),
        ('other', 'Khác')
    ], string='Phương thức thanh toán')
    
    # Thông tin ngân hàng
    bank_account = fields.Char(string='Tài khoản ngân hàng')
    bank_name = fields.Char(string='Tên ngân hàng')
    transaction_reference = fields.Char(string='Mã giao dịch')
    
    # ===========================================
    # THÔNG TIN TÍNH TOÁN
    # ===========================================
    
    # Số ngày trễ hạn
    days_overdue = fields.Integer(string='Số ngày trễ hạn', compute='_compute_days_overdue', store=True)
    
    # Phí trễ hạn
    late_fee = fields.Float(string='Phí trễ hạn', digits=(16, 2), compute='_compute_late_fee', store=True)
    
    # Tổng thanh toán (bao gồm phí)
    total_amount = fields.Float(string='Tổng thanh toán', digits=(16, 2), compute='_compute_total_amount', store=True)
    
    # ===========================================
    # THÔNG TIN HỆ THỐNG
    # ===========================================
    
    # Thời gian
    create_date = fields.Datetime(string='Ngày tạo', default=fields.Datetime.now)
    write_date = fields.Datetime(string='Ngày cập nhật', default=fields.Datetime.now)
    
    # Ghi chú
    notes = fields.Text(string='Ghi chú')
    internal_notes = fields.Text(string='Ghi chú nội bộ')
    
    # ===========================================
    # COMPUTED FIELDS
    # ===========================================
    
    @api.depends('amount', 'investment_id.interest_rate', 'investment_id.loan_id.term')
    def _compute_principal_interest(self):
        for payment in self:
            if payment.investment_id.interest_rate and payment.investment_id.loan_id.term:
                # Tính lãi suất hàng tháng
                monthly_rate = payment.investment_id.interest_rate / 100 / 12
                # Tính số tiền lãi
                payment.interest_amount = payment.amount * monthly_rate
                # Tính số tiền gốc
                payment.principal_amount = payment.amount - payment.interest_amount
            else:
                payment.interest_amount = 0.0
                payment.principal_amount = payment.amount
    
    @api.depends('due_date', 'state')
    def _compute_days_overdue(self):
        for payment in self:
            if payment.state == 'pending' and payment.due_date:
                today = fields.Date.today()
                if today > payment.due_date:
                    payment.days_overdue = (today - payment.due_date).days
                else:
                    payment.days_overdue = 0
            else:
                payment.days_overdue = 0
    
    @api.depends('days_overdue', 'amount')
    def _compute_late_fee(self):
        for payment in self:
            if payment.days_overdue > 0:
                # Phí trễ hạn: 0.5% mỗi ngày trễ
                payment.late_fee = payment.amount * 0.005 * payment.days_overdue
            else:
                payment.late_fee = 0.0
    
    @api.depends('amount', 'late_fee')
    def _compute_total_amount(self):
        for payment in self:
            payment.total_amount = payment.amount + payment.late_fee
    
    # ===========================================
    # METHODS
    # ===========================================
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('p2p.investment.payment') or 'New'
        return super(P2PInvestmentPayment, self).create(vals)
    
    def action_mark_paid(self):
        """Đánh dấu đã thanh toán"""
        self.write({
            'state': 'paid',
            'actual_payment_date': fields.Date.today(),
            'processing_status': 'completed'
        })
        # Cập nhật trạng thái đầu tư
        self.investment_id._update_investment_status()
    
    def action_mark_late(self):
        """Đánh dấu trễ hạn"""
        self.write({'state': 'late'})
    
    def action_mark_defaulted(self):
        """Đánh dấu vỡ nợ"""
        self.write({'state': 'defaulted'})
        # Cập nhật trạng thái đầu tư
        self.investment_id.action_default()
    
    def action_cancel(self):
        """Hủy thanh toán"""
        self.write({'state': 'cancelled'})
    
    def action_process_payment(self):
        """Xử lý thanh toán"""
        self.write({'processing_status': 'processing'})
        # Logic xử lý thanh toán
        try:
            # Gọi API thanh toán hoặc xử lý nội bộ
            self._process_payment_internal()
            self.write({'processing_status': 'completed'})
        except Exception as e:
            _logger.error(f"Payment processing failed: {e}")
            self.write({'processing_status': 'failed'})
    
    def _process_payment_internal(self):
        """Xử lý thanh toán nội bộ"""
        # Logic xử lý thanh toán
        # Có thể tích hợp với hệ thống thanh toán bên thứ 3
        pass
    
    def action_view_investment(self):
        """Xem đầu tư"""
        return {
            'name': 'Đầu tư',
            'type': 'ir.actions.act_window',
            'res_model': 'p2p.investment.enhanced',
            'view_mode': 'form',
            'res_id': self.investment_id.id
        }
    
    def action_view_investor(self):
        """Xem nhà đầu tư"""
        return {
            'name': 'Nhà đầu tư',
            'type': 'ir.actions.act_window',
            'res_model': 'p2p.investor.enhanced',
            'view_mode': 'form',
            'res_id': self.investor_id.id
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
    
    # ===========================================
    # CONSTRAINTS
    # ===========================================
    
    _sql_constraints = [
        ('amount_positive', 'CHECK(amount > 0)', 'Số tiền thanh toán phải lớn hơn 0!'),
        ('due_date_future', 'CHECK(due_date >= payment_date)', 'Ngày đến hạn phải sau ngày thanh toán!'),
    ]
