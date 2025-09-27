# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging
import requests
import json
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

class LoanDisbursement(models.Model):
    _name = 'loan.disbursement'
    _description = 'Loan Disbursement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char('Mã giải ngân', required=True, copy=False, readonly=True, 
                      default=lambda self: _('New'))
    
    # Liên kết với server hiện tại
    server_loan_id = fields.Char('Server Loan ID', tracking=True)
    server_investment_id = fields.Char('Server Investment ID', tracking=True)
    
    loan_application_id = fields.Many2one('loan.application', string='Khoản vay', required=True)
    borrower_id = fields.Many2one('res.partner', string='Người vay', related='loan_application_id.borrower_id', store=True)
    
    amount = fields.Float('Số tiền giải ngân', required=True, tracking=True)
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', default=lambda self: self.env.company.currency_id)
    
    disbursement_date = fields.Date('Ngày giải ngân', default=fields.Date.today, tracking=True)
    due_date = fields.Date('Ngày đáo hạn', related='loan_application_id.due_date', store=True)
    
    status = fields.Selection([
        ('draft', 'Nháp'),
        ('pending', 'Chờ phê duyệt'),
        ('approved', 'Đã phê duyệt'),
        ('processing', 'Đang xử lý'),
        ('disbursed', 'Đã giải ngân'),
        ('rejected', 'Từ chối'),
        ('cancelled', 'Đã hủy')
    ], string='Trạng thái', default='draft', tracking=True)
    
    approval_user_id = fields.Many2one('res.users', string='Người phê duyệt', tracking=True)
    approval_date = fields.Datetime('Ngày phê duyệt', tracking=True)
    
    disbursement_method = fields.Selection([
        ('bank_transfer', 'Chuyển khoản ngân hàng'),
        ('cash', 'Tiền mặt'),
        ('blockchain', 'Blockchain Transfer')
    ], string='Phương thức giải ngân', default='bank_transfer', tracking=True)
    
    # Thông tin blockchain
    blockchain_transaction_id = fields.Char('Blockchain Transaction ID', tracking=True)
    blockchain_status = fields.Selection([
        ('pending', 'Chờ xử lý'),
        ('confirmed', 'Đã xác nhận'),
        ('failed', 'Thất bại')
    ], string='Trạng thái Blockchain', default='pending')
    
    # Thông tin ngân hàng
    bank_account_id = fields.Many2one('res.partner.bank', string='Tài khoản ngân hàng')
    bank_reference = fields.Char('Mã tham chiếu ngân hàng', tracking=True)
    
    # Phí và lãi suất
    interest_rate = fields.Float('Lãi suất (%)', related='loan_application_id.interest_rate', store=True)
    service_fee = fields.Float('Phí dịch vụ', compute='_compute_fees', store=True)
    total_amount = fields.Float('Tổng số tiền', compute='_compute_total_amount', store=True)
    
    # Ghi chú và lý do
    notes = fields.Text('Ghi chú')
    rejection_reason = fields.Text('Lý do từ chối')
    
    # Thông tin đồng bộ
    sync_status = fields.Selection([
        ('pending', 'Chờ đồng bộ'),
        ('synced', 'Đã đồng bộ'),
        ('failed', 'Lỗi đồng bộ')
    ], string='Trạng thái đồng bộ', default='pending', tracking=True)
    
    sync_date = fields.Datetime('Ngày đồng bộ', tracking=True)
    sync_error = fields.Text('Lỗi đồng bộ')
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('loan.disbursement') or _('New')
        return super(LoanDisbursement, self).create(vals)
    
    @api.depends('amount', 'service_fee')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = record.amount + record.service_fee
    
    @api.depends('amount')
    def _compute_fees(self):
        for record in self:
            # Lấy cấu hình phí dịch vụ
            config = self.env['loan.config'].search([('active', '=', True)], limit=1)
            if config:
                record.service_fee = record.amount * (config.service_fee_rate / 100)
            else:
                record.service_fee = 0
    
    def action_approve(self):
        """Phê duyệt giải ngân"""
        for record in self:
            if record.status != 'pending':
                raise UserError(_('Chỉ có thể phê duyệt giải ngân đang chờ phê duyệt'))
            
            record.write({
                'status': 'approved',
                'approval_user_id': self.env.user.id,
                'approval_date': fields.Datetime.now()
            })
            
            # Tạo hoạt động
            record.activity_schedule(
                'mail.mail_activity_data_todo',
                summary='Giải ngân đã được phê duyệt',
                note=f'Giải ngân {record.name} đã được phê duyệt bởi {self.env.user.name}'
            )
    
    def action_reject(self):
        """Từ chối giải ngân"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Từ chối giải ngân',
            'res_model': 'loan.disbursement.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_disbursement_id': self.id}
        }
    
    def action_process(self):
        """Xử lý giải ngân"""
        for record in self:
            if record.status != 'approved':
                raise UserError(_('Chỉ có thể xử lý giải ngân đã được phê duyệt'))
            
            record.status = 'processing'
            
            # Xử lý theo phương thức
            if record.disbursement_method == 'blockchain':
                result = record._process_blockchain_disbursement()
                if not result['success']:
                    record.sync_error = result['error']
                    record.sync_status = 'failed'
                    return
            elif record.disbursement_method == 'bank_transfer':
                result = record._process_bank_transfer()
                if not result['success']:
                    record.sync_error = result['error']
                    record.sync_status = 'failed'
                    return
            
            record.status = 'disbursed'
            record.sync_status = 'synced'
            record.sync_date = fields.Datetime.now()
    
    def _process_blockchain_disbursement(self):
        """Xử lý giải ngân qua blockchain"""
        try:
            # Lấy cấu hình server
            config = self.env['loan.config'].search([('active', '=', True)], limit=1)
            if not config or not config.server_enabled:
                return {'success': False, 'error': 'Chưa cấu hình server'}
            
            # Gọi API giải ngân
            url = f"{config.server_api_url}/api/loan/disburse"
            headers = {
                'Authorization': f"Bearer {config.server_api_key}",
                'Content-Type': 'application/json'
            }
            
            data = {
                'loan_id': self.server_loan_id,
                'amount': self.amount,
                'disbursement_date': self.disbursement_date.isoformat(),
                'method': 'blockchain'
            }
            
            response = requests.post(url, json=data, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                self.blockchain_transaction_id = result.get('transaction_id')
                self.blockchain_status = 'confirmed'
                return {'success': True}
            else:
                return {'success': False, 'error': f'Lỗi API: {response.status_code}'}
                
        except Exception as e:
            _logger.error(f"Lỗi xử lý blockchain disbursement: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _process_bank_transfer(self):
        """Xử lý chuyển khoản ngân hàng"""
        try:
            # Logic xử lý chuyển khoản
            # Có thể tích hợp với hệ thống ngân hàng
            return {'success': True}
        except Exception as e:
            _logger.error(f"Lỗi xử lý bank transfer: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def action_sync_to_server(self):
        """Đồng bộ lên server"""
        for record in self:
            try:
                config = self.env['loan.config'].search([('active', '=', True)], limit=1)
                if not config or not config.server_enabled:
                    raise UserError(_('Chưa cấu hình server'))
                
                # Chuẩn bị dữ liệu
                sync_data = {
                    'odoo_id': record.id,
                    'name': record.name,
                    'server_loan_id': record.server_loan_id,
                    'amount': record.amount,
                    'disbursement_date': record.disbursement_date.isoformat(),
                    'status': record.status,
                    'method': record.disbursement_method
                }
                
                # Gọi API đồng bộ
                url = f"{config.server_api_url}/api/disbursement/sync"
                headers = {
                    'Authorization': f"Bearer {config.server_api_key}",
                    'Content-Type': 'application/json'
                }
                
                response = requests.post(url, json=sync_data, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    record.sync_status = 'synced'
                    record.sync_date = fields.Datetime.now()
                    record.sync_error = False
                else:
                    record.sync_status = 'failed'
                    record.sync_error = f'Lỗi API: {response.status_code}'
                    
            except Exception as e:
                _logger.error(f"Lỗi đồng bộ disbursement: {str(e)}")
                record.sync_status = 'failed'
                record.sync_error = str(e)


class LoanApplication(models.Model):
    _name = 'loan.application'
    _description = 'Loan Application'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char('Mã hồ sơ', required=True, copy=False, readonly=True, 
                      default=lambda self: _('New'))
    
    # Liên kết với server
    server_loan_id = fields.Char('Server Loan ID', tracking=True)
    
    borrower_id = fields.Many2one('res.partner', string='Người vay', required=True)
    loan_type_id = fields.Many2one('loan.type', string='Loại khoản vay', required=True)
    
    amount = fields.Float('Số tiền vay', tracking=True)
    interest_rate = fields.Float('Lãi suất (%)', required=True, tracking=True)
    term_months = fields.Integer('Kỳ hạn (tháng)', required=True, tracking=True)
    
    application_date = fields.Date('Ngày đăng ký', default=fields.Date.today, tracking=True)
    due_date = fields.Date('Ngày đáo hạn', compute='_compute_due_date', store=True)
    
    status = fields.Selection([
        ('draft', 'Nháp'),
        ('submitted', 'Đã nộp'),
        ('under_review', 'Đang xem xét'),
        ('approved', 'Đã phê duyệt'),
        ('rejected', 'Từ chối'),
        ('disbursed', 'Đã giải ngân'),
        ('active', 'Đang hoạt động'),
        ('completed', 'Hoàn thành'),
        ('defaulted', 'Quá hạn')
    ], string='Trạng thái', default='draft', tracking=True)
    
    purpose = fields.Text('Mục đích vay')
    collateral_info = fields.Text('Thông tin tài sản đảm bảo')
    
    # Thông tin tài chính
    monthly_income = fields.Float('Thu nhập hàng tháng')
    monthly_expenses = fields.Float('Chi phí hàng tháng')
    credit_score = fields.Integer('Điểm tín dụng')
    
    # Phí và lãi
    service_fee = fields.Float('Phí dịch vụ', compute='_compute_fees', store=True)
    total_amount = fields.Float('Tổng số tiền', compute='_compute_total_amount', store=True)
    monthly_payment = fields.Float('Trả góp hàng tháng', compute='_compute_monthly_payment', store=True)
    
    # Thông tin đồng bộ
    sync_status = fields.Selection([
        ('pending', 'Chờ đồng bộ'),
        ('synced', 'Đã đồng bộ'),
        ('failed', 'Lỗi đồng bộ')
    ], string='Trạng thái đồng bộ', default='pending', tracking=True)
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('loan.application') or _('New')
        return super(LoanApplication, self).create(vals)
    
    @api.depends('application_date', 'term_months')
    def _compute_due_date(self):
        for record in self:
            if record.application_date and record.term_months:
                record.due_date = record.application_date + timedelta(days=record.term_months * 30)
            else:
                record.due_date = False
    
    @api.depends('amount', 'service_fee')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = record.amount + record.service_fee
    
    @api.depends('amount', 'interest_rate', 'term_months')
    def _compute_fees(self):
        for record in self:
            # Lấy cấu hình phí dịch vụ
            config = self.env['loan.config'].search([('active', '=', True)], limit=1)
            if config:
                record.service_fee = record.amount * (config.service_fee_rate / 100)
            else:
                record.service_fee = 0
    
    @api.depends('amount', 'interest_rate', 'term_months')
    def _compute_monthly_payment(self):
        for record in self:
            if record.amount and record.interest_rate and record.term_months:
                # Tính toán trả góp hàng tháng
                monthly_rate = record.interest_rate / 100 / 12
                if monthly_rate > 0:
                    record.monthly_payment = record.amount * (monthly_rate * (1 + monthly_rate) ** record.term_months) / ((1 + monthly_rate) ** record.term_months - 1)
                else:
                    record.monthly_payment = record.amount / record.term_months
            else:
                record.monthly_payment = 0
