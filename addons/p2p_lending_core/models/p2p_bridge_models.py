# -*- coding: utf-8 -*-

from odoo import models, fields, api
from .mongo_service import MongoService
import logging

_logger = logging.getLogger(__name__)

# Local mapping to keep status values compatible with Odoo selection
_P2P_ALLOWED_STATUSES = {"waiting", "success", "clean", "fail"}
_P2P_STATUS_MAP = {
    # Map server-like synonyms
    "waiting": "waiting",
    "queued": "waiting",
    "processing": "success",
    "in_progress": "success",
    "done": "clean",
    "finished": "clean",
    "canceled": "fail",
    "cancel": "fail",
    # Map legacy Odoo values to server model
    "pending": "waiting",
    "active": "success",
    "completed": "clean",
    "cancelled": "fail",
}

def _normalize_status(raw_status: str) -> str:
    if not raw_status:
        return "pending"
    mapped = _P2P_STATUS_MAP.get(str(raw_status).lower(), str(raw_status).lower())
    return mapped if mapped in _P2P_ALLOWED_STATUSES else "waiting"

class P2PBridge(models.Model):
    _name = 'p2p.bridge'
    _description = 'P2P MongoDB Bridge'

    user_id = fields.Char(string='User ID', required=True)
    wallet_balance = fields.Float(compute="_compute_wallet_balance", string='Wallet Balance')
    last_sync = fields.Datetime(string='Last Sync', default=fields.Datetime.now)

    @api.depends('user_id')
    def _compute_wallet_balance(self):
        for record in self:
            try:
                mongo = MongoService()
                wallet = mongo.get_wallet(record.user_id)
                record.wallet_balance = wallet.get("balance", 0) if wallet else 0
            except Exception as e:
                _logger.error(f"Error computing wallet balance: {e}")
                record.wallet_balance = 0

    def sync_from_mongo(self):
        """Sync data from MongoDB"""
        try:
            _logger.info("=== P2P BRIDGE SYNC STARTED ===")
            mongo = MongoService()
            _logger.info("=== CALLING mongo.sync_all_data ===")
            result = mongo.sync_all_data(self.env)
            _logger.info(f"=== SYNC RESULT: {result} ===")
            self.last_sync = fields.Datetime.now()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Thành công',
                    'message': 'Đồng bộ dữ liệu từ MongoDB thành công!',
                    'type': 'success',
                }
            }
        except Exception as e:
            _logger.error(f"Error syncing from MongoDB: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Lỗi',
                    'message': f'Lỗi đồng bộ dữ liệu: {str(e)}',
                    'type': 'danger',
                }
            }

    def test_connection(self):
        """Test MongoDB connection"""
        try:
            mongo = MongoService()
            result = mongo.test_connection()
            if result:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Thành công',
                        'message': 'Kết nối MongoDB thành công!',
                        'type': 'success',
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Lỗi',
                        'message': 'Không thể kết nối đến MongoDB',
                        'type': 'danger',
                    }
                }
        except Exception as e:
            _logger.error(f"Error testing MongoDB connection: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Lỗi',
                    'message': f'Lỗi kết nối MongoDB: {str(e)}',
                    'type': 'danger',
                }
            }


class P2PWallet(models.Model):
    _name = 'p2p.wallet'
    _description = 'P2P Wallet'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    user_id = fields.Char('User ID', required=True, tracking=True)
    balance = fields.Float('Số dư', default=0, tracking=True)
    currency = fields.Char('Tiền tệ', default='VND', tracking=True)
    
    # Blockchain info
    blockchain_address = fields.Char('Địa chỉ Blockchain', tracking=True)
    blockchain_network = fields.Selection([
        ('ethereum', 'Ethereum'),
        ('tron', 'TRON'),
        ('bsc', 'BSC')
    ], string='Mạng Blockchain', default='ethereum', tracking=True)
    
    # Sync info
    last_sync = fields.Datetime('Lần đồng bộ cuối', tracking=True)
    sync_status = fields.Selection([
        ('pending', 'Chờ đồng bộ'),
        ('synced', 'Đã đồng bộ'),
        ('failed', 'Lỗi đồng bộ')
    ], string='Trạng thái đồng bộ', default='pending', tracking=True)
    
    # Transaction history
    transaction_count = fields.Integer('Số giao dịch', default=0)
    total_deposits = fields.Float('Tổng nạp', default=0)
    total_withdrawals = fields.Float('Tổng rút', default=0)

    def sync_from_server(self):
        """Đồng bộ từ server"""
        for record in self:
            try:
                mongo = MongoService()
                wallet_data = mongo.get_wallet(record.user_id)
                
                if wallet_data:
                    record.write({
                        'balance': wallet_data.get('balance', 0),
                        'currency': wallet_data.get('currency', 'VND'),
                        'blockchain_address': wallet_data.get('blockchain_address'),
                        'blockchain_network': wallet_data.get('blockchain_network', 'ethereum'),
                        'last_sync': fields.Datetime.now(),
                        'sync_status': 'synced'
                    })
                else:
                    record.sync_status = 'failed'
                    
            except Exception as e:
                _logger.error(f"Error syncing wallet {record.user_id}: {e}")
                record.sync_status = 'failed'


class P2PBorrower(models.Model):
    _name = 'p2p.borrower'
    _description = 'P2P Borrower'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    user_id = fields.Char('User ID', required=True, tracking=True)
    name = fields.Char('Tên', required=True, tracking=True)
    phone = fields.Char('Số điện thoại', tracking=True)
    email = fields.Char('Email', tracking=True)
    
    # Personal info
    identity_card = fields.Char('CMND/CCCD', tracking=True)
    address = fields.Text('Địa chỉ', tracking=True)
    date_of_birth = fields.Date('Ngày sinh', tracking=True)
    
    # Financial info
    monthly_income = fields.Float('Thu nhập hàng tháng', tracking=True)
    credit_score = fields.Integer('Điểm tín dụng', tracking=True)
    employment_status = fields.Selection([
        ('employed', 'Có việc làm'),
        ('self_employed', 'Tự kinh doanh'),
        ('unemployed', 'Thất nghiệp'),
        ('student', 'Sinh viên')
    ], string='Tình trạng việc làm', tracking=True)
    
    # Loan info
    total_loans = fields.Integer('Tổng số khoản vay', default=0)
    active_loans = fields.Integer('Khoản vay đang hoạt động', default=0)
    total_borrowed = fields.Float('Tổng số tiền đã vay', default=0)
    total_repaid = fields.Float('Tổng số tiền đã trả', default=0)
    
    # Status
    status = fields.Selection([
        ('active', 'Hoạt động'),
        ('suspended', 'Tạm khóa'),
        ('blacklisted', 'Cấm vay')
    ], string='Trạng thái', default='active', tracking=True)
    
    # Sync info
    last_sync = fields.Datetime('Lần đồng bộ cuối', tracking=True)
    sync_status = fields.Selection([
        ('pending', 'Chờ đồng bộ'),
        ('synced', 'Đã đồng bộ'),
        ('failed', 'Lỗi đồng bộ')
    ], string='Trạng thái đồng bộ', default='pending', tracking=True)

    def sync_from_server(self):
        """Đồng bộ từ server"""
        for record in self:
            try:
                mongo = MongoService()
                borrower_data = mongo.get_borrower(record.user_id)
                
                if borrower_data:
                    record.write({
                        'name': borrower_data.get('name', ''),
                        'phone': borrower_data.get('phone', ''),
                        'email': borrower_data.get('email', ''),
                        'identity_card': borrower_data.get('identity_card', ''),
                        'address': borrower_data.get('address', ''),
                        'date_of_birth': borrower_data.get('date_of_birth'),
                        'monthly_income': borrower_data.get('monthly_income', 0),
                        'credit_score': borrower_data.get('credit_score', 0),
                        'employment_status': borrower_data.get('employment_status', 'employed'),
                        'total_loans': borrower_data.get('total_loans', 0),
                        'active_loans': borrower_data.get('active_loans', 0),
                        'total_borrowed': borrower_data.get('total_borrowed', 0),
                        'total_repaid': borrower_data.get('total_repaid', 0),
                        'status': borrower_data.get('status', 'active'),
                        'last_sync': fields.Datetime.now(),
                        'sync_status': 'synced'
                    })
                else:
                    record.sync_status = 'failed'
                    
            except Exception as e:
                _logger.error(f"Error syncing borrower {record.user_id}: {e}")
                record.sync_status = 'failed'


class P2PInvestor(models.Model):
    _name = 'p2p.investor'
    _description = 'P2P Investor'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    user_id = fields.Char('User ID', required=True, tracking=True)
    name = fields.Char('Tên', required=True, tracking=True)
    phone = fields.Char('Số điện thoại', tracking=True)
    email = fields.Char('Email', tracking=True)
    
    # Personal info
    identity_card = fields.Char('CMND/CCCD', tracking=True)
    address = fields.Text('Địa chỉ', tracking=True)
    city = fields.Char('Thành phố', tracking=True)
    job_title = fields.Char('Nghề nghiệp', tracking=True)
    date_of_birth = fields.Date('Ngày sinh', tracking=True)
    
    # Financial info
    monthly_income = fields.Float('Thu nhập hàng tháng', tracking=True)
    investment_capacity = fields.Float('Năng lực đầu tư', tracking=True)
    risk_tolerance = fields.Selection([
        ('low', 'Thấp'),
        ('medium', 'Trung bình'),
        ('high', 'Cao')
    ], string='Khả năng chấp nhận rủi ro', default='medium', tracking=True)
    
    # Investment info
    total_investments = fields.Integer('Tổng số khoản đầu tư', default=0)
    active_investments = fields.Integer('Khoản đầu tư đang hoạt động', default=0)
    total_invested = fields.Float('Tổng số tiền đã đầu tư', default=0)
    total_returns = fields.Float('Tổng lợi nhuận', default=0)
    
    # Status
    status = fields.Selection([
        ('active', 'Hoạt động'),
        ('suspended', 'Tạm khóa'),
        ('inactive', 'Không hoạt động')
    ], string='Trạng thái', default='active', tracking=True)
    
    # Sync info
    last_sync = fields.Datetime('Lần đồng bộ cuối', tracking=True)
    sync_status = fields.Selection([
        ('pending', 'Chờ đồng bộ'),
        ('synced', 'Đã đồng bộ'),
        ('failed', 'Lỗi đồng bộ')
    ], string='Trạng thái đồng bộ', default='pending', tracking=True)

    def sync_from_server(self):
        """Đồng bộ từ server"""
        for record in self:
            try:
                mongo = MongoService()
                investor_data = mongo.get_investor(record.user_id)
                
                if investor_data:
                    record.write({
                        'name': investor_data.get('name', ''),
                        'phone': investor_data.get('phone', ''),
                        'email': investor_data.get('email', ''),
                        'identity_card': investor_data.get('identity_card', ''),
                        'address': investor_data.get('address', ''),
                        'date_of_birth': investor_data.get('date_of_birth'),
                        'monthly_income': investor_data.get('monthly_income', 0),
                        'investment_capacity': investor_data.get('investment_capacity', 0),
                        'risk_tolerance': investor_data.get('risk_tolerance', 'medium'),
                        'total_investments': investor_data.get('total_investments', 0),
                        'active_investments': investor_data.get('active_investments', 0),
                        'total_invested': investor_data.get('total_invested', 0),
                        'total_returns': investor_data.get('total_returns', 0),
                        'status': investor_data.get('status', 'active'),
                        'last_sync': fields.Datetime.now(),
                        'sync_status': 'synced'
                    })
                else:
                    record.sync_status = 'failed'
                    
            except Exception as e:
                _logger.error(f"Error syncing investor {record.user_id}: {e}")
                record.sync_status = 'failed'


class P2PLoan(models.Model):
    _name = 'p2p.loan'
    _description = 'P2P Loan'
    _order = 'create_date desc'

    name = fields.Char('Loan Name', required=True)
    amount = fields.Float('Loan Amount', required=True)
    interest_rate = fields.Float('Interest Rate (%)', default=0)
    term_months = fields.Integer('Term (Months)', default=0)
    status = fields.Selection([
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='pending')
    
    # Borrower info
    borrower_id = fields.Many2one('p2p.borrower', string='Borrower')
    borrower_name = fields.Char('Borrower Name', related='borrower_id.name')
    borrower_phone = fields.Char('Borrower Phone', related='borrower_id.phone')
    
    # Dates
    create_date = fields.Datetime('Created Date', default=fields.Datetime.now)
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    
    # Sync info
    user_id = fields.Char('MongoDB User ID')
    last_sync = fields.Datetime('Last Sync')
    sync_status = fields.Selection([
        ('pending', 'Pending'),
        ('synced', 'Synced'),
        ('failed', 'Failed')
    ], string='Sync Status', default='pending')


class P2PInvestment(models.Model):
    _name = 'p2p.investment'
    _description = 'P2P Investment'
    _order = 'create_date desc'

    name = fields.Char('Investment Name', required=True)
    amount = fields.Float('Investment Amount', required=True)
    interest_rate = fields.Float('Interest Rate (%)', default=0)
    term_months = fields.Integer('Term (Months)', default=0)
    status = fields.Selection([
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='pending')
    
    # Info from API (investment.info)
    monthly_income = fields.Float('Monthly Income', default=0)
    monthly_profit = fields.Float('Monthly Profit', default=0)
    monthly_principal_income = fields.Float('Monthly Principal Income', default=0)
    monthly_interest_income = fields.Float('Monthly Interest Income', default=0)
    entirely_profit = fields.Float('Entirely Profit', default=0)
    num_notes = fields.Integer('Number of Notes', default=0)
    service_fee = fields.Float('Service Fee', default=0)
    
    # Investor info
    investor_id = fields.Many2one('p2p.investor', string='Investor')
    investor_name = fields.Char('Investor Name', related='investor_id.name')
    investor_phone = fields.Char('Investor Phone', related='investor_id.phone')
    
    # Dates
    create_date = fields.Datetime('Created Date', default=fields.Datetime.now)
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    
    # Sync info
    user_id = fields.Char('MongoDB User ID')
    last_sync = fields.Datetime('Last Sync')
    sync_status = fields.Selection([
        ('pending', 'Pending'),
        ('synced', 'Synced'),
        ('failed', 'Failed')
    ], string='Sync Status', default='pending')
