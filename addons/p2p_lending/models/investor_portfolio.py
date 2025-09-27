# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date, datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class P2PInvestorPortfolio(models.Model):
    """Model quản lý portfolio nhà đầu tư"""
    _name = 'p2p.investor.portfolio'
    _description = 'Portfolio nhà đầu tư'
    
    # ===========================================
    # THÔNG TIN CƠ BẢN
    # ===========================================
    
    name = fields.Char(string='Tên portfolio', required=True)
    investor_id = fields.Many2one('p2p.investor.enhanced', string='Nhà đầu tư', required=True)
    portfolio_type = fields.Selection([
        ('conservative', 'Bảo thủ'),
        ('balanced', 'Cân bằng'),
        ('aggressive', 'Tích cực'),
        ('custom', 'Tùy chỉnh')
    ], string='Loại portfolio', default='balanced')
    
    # ===========================================
    # THÔNG TIN TỔNG QUAN
    # ===========================================
    
    # Tổng quan đầu tư
    total_invested = fields.Float(string='Tổng đã đầu tư', digits=(16, 2), compute='_compute_portfolio_stats', store=True)
    total_returns = fields.Float(string='Tổng lợi nhuận', digits=(16, 2), compute='_compute_portfolio_stats', store=True)
    total_available = fields.Float(string='Vốn khả dụng', digits=(16, 2), compute='_compute_portfolio_stats', store=True)
    
    # Số lượng đầu tư
    active_investments = fields.Integer(string='Đầu tư đang hoạt động', compute='_compute_portfolio_stats', store=True)
    completed_investments = fields.Integer(string='Đầu tư đã hoàn thành', compute='_compute_portfolio_stats', store=True)
    defaulted_investments = fields.Integer(string='Đầu tư vỡ nợ', compute='_compute_portfolio_stats', store=True)
    
    # ===========================================
    # THÔNG TIN HIỆU SUẤT
    # ===========================================
    
    # ROI và hiệu suất
    total_roi = fields.Float(string='ROI tổng (%)', digits=(5, 2), compute='_compute_performance_metrics', store=True)
    annualized_roi = fields.Float(string='ROI năm (%)', digits=(5, 2), compute='_compute_performance_metrics', store=True)
    average_roi = fields.Float(string='ROI trung bình (%)', digits=(5, 2), compute='_compute_performance_metrics', store=True)
    
    # Rủi ro
    portfolio_risk_score = fields.Float(string='Điểm rủi ro portfolio', digits=(5, 2), compute='_compute_risk_metrics', store=True)
    risk_level = fields.Selection([
        ('very_low', 'Rất thấp'),
        ('low', 'Thấp'),
        ('medium', 'Trung bình'),
        ('high', 'Cao'),
        ('very_high', 'Rất cao')
    ], string='Mức độ rủi ro', compute='_compute_risk_metrics', store=True)
    
    # ===========================================
    # THÔNG TIN PHÂN BỔ
    # ===========================================
    
    # Phân bổ theo rủi ro
    low_risk_percentage = fields.Float(string='Rủi ro thấp (%)', digits=(5, 2), compute='_compute_risk_distribution', store=True)
    medium_risk_percentage = fields.Float(string='Rủi ro trung bình (%)', digits=(5, 2), compute='_compute_risk_distribution', store=True)
    high_risk_percentage = fields.Float(string='Rủi ro cao (%)', digits=(5, 2), compute='_compute_risk_distribution', store=True)
    
    # Phân bổ theo kỳ hạn
    short_term_percentage = fields.Float(string='Ngắn hạn (%)', digits=(5, 2), compute='_compute_term_distribution', store=True)
    medium_term_percentage = fields.Float(string='Trung hạn (%)', digits=(5, 2), compute='_compute_term_distribution', store=True)
    long_term_percentage = fields.Float(string='Dài hạn (%)', digits=(5, 2), compute='_compute_term_distribution', store=True)
    
    # ===========================================
    # THÔNG TIN THANH TOÁN
    # ===========================================
    
    # Thanh toán
    total_payments_received = fields.Float(string='Tổng thanh toán nhận', digits=(16, 2), compute='_compute_payment_stats', store=True)
    pending_payments = fields.Float(string='Thanh toán chờ', digits=(16, 2), compute='_compute_payment_stats', store=True)
    overdue_payments = fields.Float(string='Thanh toán trễ hạn', digits=(16, 2), compute='_compute_payment_stats', store=True)
    
    # ===========================================
    # THÔNG TIN MỤC TIÊU
    # ===========================================
    
    # Mục tiêu đầu tư
    target_return = fields.Float(string='Lợi nhuận mục tiêu (%)', digits=(5, 2))
    target_amount = fields.Float(string='Số tiền mục tiêu', digits=(16, 2))
    target_date = fields.Date(string='Ngày đạt mục tiêu')
    
    # Tiến độ
    progress_percentage = fields.Float(string='Tiến độ (%)', digits=(5, 2), compute='_compute_progress', store=True)
    days_to_target = fields.Integer(string='Số ngày đến mục tiêu', compute='_compute_progress', store=True)
    
    # ===========================================
    # THÔNG TIN HỆ THỐNG
    # ===========================================
    
    # Trạng thái
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('active', 'Hoạt động'),
        ('paused', 'Tạm dừng'),
        ('completed', 'Hoàn thành'),
        ('cancelled', 'Đã hủy')
    ], string='Trạng thái', default='draft')
    
    # Thời gian
    create_date = fields.Datetime(string='Ngày tạo', default=fields.Datetime.now)
    last_update_date = fields.Datetime(string='Cập nhật cuối', default=fields.Datetime.now)
    
    # Ghi chú
    notes = fields.Text(string='Ghi chú')
    
    # ===========================================
    # COMPUTED FIELDS
    # ===========================================
    
    @api.depends('investor_id.investment_ids', 'investor_id.investment_ids.amount', 
                 'investor_id.investment_ids.total_returns', 'investor_id.investment_ids.state')
    def _compute_portfolio_stats(self):
        for portfolio in self:
            investments = portfolio.investor_id.investment_ids
            portfolio.total_invested = sum(investments.mapped('amount'))
            portfolio.total_returns = sum(investments.mapped('total_returns'))
            portfolio.total_available = portfolio.investor_id.available_capital
            portfolio.active_investments = len(investments.filtered(lambda x: x.state == 'active'))
            portfolio.completed_investments = len(investments.filtered(lambda x: x.state == 'matured'))
            portfolio.defaulted_investments = len(investments.filtered(lambda x: x.state == 'defaulted'))
    
    @api.depends('total_invested', 'total_returns')
    def _compute_performance_metrics(self):
        for portfolio in self:
            if portfolio.total_invested > 0:
                portfolio.total_roi = (portfolio.total_returns / portfolio.total_invested) * 100
            else:
                portfolio.total_roi = 0.0
            
            # Tính ROI năm (giả sử thời gian đầu tư trung bình là 1 năm)
            portfolio.annualized_roi = portfolio.total_roi
            portfolio.average_roi = portfolio.total_roi
    
    @api.depends('investor_id.investment_ids', 'investor_id.investment_ids.risk_score')
    def _compute_risk_metrics(self):
        for portfolio in self:
            investments = portfolio.investor_id.investment_ids.filtered(lambda x: x.state == 'active')
            if investments:
                portfolio.portfolio_risk_score = sum(investments.mapped('risk_score')) / len(investments)
                
                if portfolio.portfolio_risk_score <= 20:
                    portfolio.risk_level = 'very_low'
                elif portfolio.portfolio_risk_score <= 40:
                    portfolio.risk_level = 'low'
                elif portfolio.portfolio_risk_score <= 60:
                    portfolio.risk_level = 'medium'
                elif portfolio.portfolio_risk_score <= 80:
                    portfolio.risk_level = 'high'
                else:
                    portfolio.risk_level = 'very_high'
            else:
                portfolio.portfolio_risk_score = 0.0
                portfolio.risk_level = 'very_low'
    
    @api.depends('investor_id.investment_ids', 'investor_id.investment_ids.risk_level', 'total_invested')
    def _compute_risk_distribution(self):
        for portfolio in self:
            investments = portfolio.investor_id.investment_ids.filtered(lambda x: x.state == 'active')
            if investments and portfolio.total_invested > 0:
                low_risk_amount = sum(investments.filtered(lambda x: x.risk_level in ['very_low', 'low']).mapped('amount'))
                medium_risk_amount = sum(investments.filtered(lambda x: x.risk_level == 'medium').mapped('amount'))
                high_risk_amount = sum(investments.filtered(lambda x: x.risk_level in ['high', 'very_high']).mapped('amount'))
                
                portfolio.low_risk_percentage = (low_risk_amount / portfolio.total_invested) * 100
                portfolio.medium_risk_percentage = (medium_risk_amount / portfolio.total_invested) * 100
                portfolio.high_risk_percentage = (high_risk_amount / portfolio.total_invested) * 100
            else:
                portfolio.low_risk_percentage = 0.0
                portfolio.medium_risk_percentage = 0.0
                portfolio.high_risk_percentage = 0.0
    
    @api.depends('investor_id.investment_ids', 'investor_id.investment_ids.loan_id.term', 'total_invested')
    def _compute_term_distribution(self):
        for portfolio in self:
            investments = portfolio.investor_id.investment_ids.filtered(lambda x: x.state == 'active')
            if investments and portfolio.total_invested > 0:
                short_term_amount = sum(investments.filtered(lambda x: x.loan_id.term <= 6).mapped('amount'))
                medium_term_amount = sum(investments.filtered(lambda x: 6 < x.loan_id.term <= 24).mapped('amount'))
                long_term_amount = sum(investments.filtered(lambda x: x.loan_id.term > 24).mapped('amount'))
                
                portfolio.short_term_percentage = (short_term_amount / portfolio.total_invested) * 100
                portfolio.medium_term_percentage = (medium_term_amount / portfolio.total_invested) * 100
                portfolio.long_term_percentage = (long_term_amount / portfolio.total_invested) * 100
            else:
                portfolio.short_term_percentage = 0.0
                portfolio.medium_term_percentage = 0.0
                portfolio.long_term_percentage = 0.0
    
    @api.depends('investor_id.investment_ids', 'investor_id.investment_ids.payment_schedule_ids')
    def _compute_payment_stats(self):
        for portfolio in self:
            investments = portfolio.investor_id.investment_ids
            payments = investments.mapped('payment_schedule_ids')
            
            portfolio.total_payments_received = sum(payments.filtered(lambda x: x.state == 'paid').mapped('amount'))
            portfolio.pending_payments = sum(payments.filtered(lambda x: x.state == 'pending').mapped('amount'))
            portfolio.overdue_payments = sum(payments.filtered(lambda x: x.state == 'late').mapped('amount'))
    
    @api.depends('target_amount', 'total_invested', 'target_date')
    def _compute_progress(self):
        for portfolio in self:
            if portfolio.target_amount > 0:
                portfolio.progress_percentage = (portfolio.total_invested / portfolio.target_amount) * 100
            else:
                portfolio.progress_percentage = 0.0
            
            if portfolio.target_date:
                today = fields.Date.today()
                portfolio.days_to_target = (portfolio.target_date - today).days
            else:
                portfolio.days_to_target = 0
    
    # ===========================================
    # METHODS
    # ===========================================
    
    def action_activate(self):
        """Kích hoạt portfolio"""
        self.write({'state': 'active'})
    
    def action_pause(self):
        """Tạm dừng portfolio"""
        self.write({'state': 'paused'})
    
    def action_complete(self):
        """Hoàn thành portfolio"""
        self.write({'state': 'completed'})
    
    def action_cancel(self):
        """Hủy portfolio"""
        self.write({'state': 'cancelled'})
    
    def action_view_investments(self):
        """Xem danh mục đầu tư"""
        return {
            'name': 'Danh mục đầu tư',
            'type': 'ir.actions.act_window',
            'res_model': 'p2p.investment.enhanced',
            'view_mode': 'tree,form',
            'domain': [('investor_id', '=', self.investor_id.id)],
            'context': {'default_investor_id': self.investor_id.id}
        }
    
    def action_view_payments(self):
        """Xem thanh toán"""
        return {
            'name': 'Thanh toán',
            'type': 'ir.actions.act_window',
            'res_model': 'p2p.investment.payment',
            'view_mode': 'tree,form',
            'domain': [('investor_id', '=', self.investor_id.id)],
            'context': {'default_investor_id': self.investor_id.id}
        }
    
    def action_generate_report(self):
        """Tạo báo cáo portfolio"""
        return {
            'name': 'Báo cáo Portfolio',
            'type': 'ir.actions.act_window',
            'res_model': 'p2p.portfolio.report',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new'
        }
    
    def action_rebalance_portfolio(self):
        """Cân bằng lại portfolio"""
        # Logic cân bằng portfolio
        self._rebalance_investments()
    
    def _rebalance_investments(self):
        """Cân bằng danh mục đầu tư"""
        # Logic cân bằng dựa trên mục tiêu và rủi ro
        pass
    
    # ===========================================
    # CONSTRAINTS
    # ===========================================
    
    _sql_constraints = [
        ('target_amount_positive', 'CHECK(target_amount >= 0)', 'Số tiền mục tiêu phải lớn hơn hoặc bằng 0!'),
        ('target_return_positive', 'CHECK(target_return >= 0)', 'Lợi nhuận mục tiêu phải lớn hơn hoặc bằng 0!'),
    ]
