# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date, datetime
import logging

_logger = logging.getLogger(__name__)

class P2PInvestorEnhanced(models.Model):
    """Enhanced Investor Model với đầy đủ thông tin cho P2P Lending"""
    _name = 'p2p.investor.enhanced'
    _inherit = ['p2p.investor']
    _description = 'Nhà đầu tư nâng cao'
    
    # ===========================================
    # THÔNG TIN CÁ NHÂN CHI TIẾT
    # ===========================================
    
    # Thông tin cá nhân cơ bản
    full_name = fields.Char(string='Tên đầy đủ', required=True, tracking=True)
    first_name = fields.Char(string='Tên', required=True)
    last_name = fields.Char(string='Họ', required=True)
    middle_name = fields.Char(string='Tên đệm')
    display_name = fields.Char(string='Tên hiển thị', compute='_compute_display_name', store=True)
    
    # Thông tin định danh
    id_number = fields.Char(string='Số CMND/CCCD', required=True, tracking=True)
    id_issue_date = fields.Date(string='Ngày cấp CMND/CCCD')
    id_issue_place = fields.Char(string='Nơi cấp CMND/CCCD')
    passport_number = fields.Char(string='Số hộ chiếu')
    passport_expiry = fields.Date(string='Hộ chiếu hết hạn')
    
    # Thông tin cá nhân
    date_of_birth = fields.Date(string='Ngày sinh', required=True)
    age = fields.Integer(string='Tuổi', compute='_compute_age', store=True)
    gender = fields.Selection([
        ('male', 'Nam'),
        ('female', 'Nữ'),
        ('other', 'Khác')
    ], string='Giới tính', required=True)
    marital_status = fields.Selection([
        ('single', 'Độc thân'),
        ('married', 'Đã kết hôn'),
        ('divorced', 'Ly hôn'),
        ('widowed', 'Góa phụ')
    ], string='Tình trạng hôn nhân')
    nationality = fields.Char(string='Quốc tịch', default='Việt Nam')
    
    # Thông tin liên lạc
    phone = fields.Char(string='Số điện thoại chính', required=True)
    phone_secondary = fields.Char(string='Số điện thoại phụ')
    email = fields.Char(string='Email chính', required=True)
    email_secondary = fields.Char(string='Email phụ')
    website = fields.Char(string='Website cá nhân')
    
    # Thông tin địa chỉ
    address_home = fields.Text(string='Địa chỉ thường trú', required=True)
    address_temporary = fields.Text(string='Địa chỉ tạm trú')
    city = fields.Char(string='Thành phố/Tỉnh', required=True)
    district = fields.Char(string='Quận/Huyện', required=True)
    ward = fields.Char(string='Phường/Xã', required=True)
    postal_code = fields.Char(string='Mã bưu điện')
    country_id = fields.Many2one('res.country', string='Quốc gia', default=lambda self: self.env.ref('base.vn'))
    
    # ===========================================
    # THÔNG TIN TÀI CHÍNH CHI TIẾT
    # ===========================================
    
    # Thu nhập và tài sản
    monthly_income = fields.Float(string='Thu nhập hàng tháng', digits=(16, 2))
    annual_income = fields.Float(string='Thu nhập hàng năm', digits=(16, 2), compute='_compute_annual_income', store=True)
    income_source = fields.Selection([
        ('salary', 'Lương'),
        ('business', 'Kinh doanh'),
        ('investment', 'Đầu tư'),
        ('rental', 'Cho thuê'),
        ('pension', 'Lương hưu'),
        ('other', 'Khác')
    ], string='Nguồn thu nhập chính')
    
    # Tài sản
    total_assets = fields.Float(string='Tổng tài sản', digits=(16, 2))
    liquid_assets = fields.Float(string='Tài sản lỏng', digits=(16, 2))
    real_estate_value = fields.Float(string='Giá trị bất động sản', digits=(16, 2))
    vehicle_value = fields.Float(string='Giá trị phương tiện', digits=(16, 2))
    other_assets = fields.Float(string='Tài sản khác', digits=(16, 2))
    
    # Nợ và nghĩa vụ tài chính
    total_debt = fields.Float(string='Tổng nợ', digits=(16, 2))
    monthly_debt_payment = fields.Float(string='Trả nợ hàng tháng', digits=(16, 2))
    debt_to_income_ratio = fields.Float(string='Tỷ lệ nợ/thu nhập (%)', digits=(5, 2), compute='_compute_debt_to_income_ratio', store=True)
    
    # ===========================================
    # THÔNG TIN ĐẦU TƯ
    # ===========================================
    
    # Khả năng đầu tư
    investment_capacity = fields.Float(string='Khả năng đầu tư', digits=(16, 2), required=True)
    available_capital = fields.Float(string='Vốn khả dụng', digits=(16, 2), compute='_compute_available_capital', store=True)
    minimum_investment = fields.Float(string='Đầu tư tối thiểu', digits=(16, 2), default=1000000)
    maximum_investment = fields.Float(string='Đầu tư tối đa', digits=(16, 2))
    
    # Rủi ro và sở thích
    risk_tolerance = fields.Selection([
        ('very_low', 'Rất thấp'),
        ('low', 'Thấp'),
        ('medium', 'Trung bình'),
        ('high', 'Cao'),
        ('very_high', 'Rất cao')
    ], string='Khả năng chấp nhận rủi ro', required=True, default='medium')
    
    investment_experience = fields.Selection([
        ('beginner', 'Mới bắt đầu'),
        ('intermediate', 'Trung bình'),
        ('advanced', 'Nâng cao'),
        ('expert', 'Chuyên gia')
    ], string='Kinh nghiệm đầu tư', default='beginner')
    
    preferred_investment_types = fields.Selection([
        ('short_term', 'Ngắn hạn (1-6 tháng)'),
        ('medium_term', 'Trung hạn (6-24 tháng)'),
        ('long_term', 'Dài hạn (2+ năm)')
    ], string='Loại đầu tư ưa thích', default='medium_term')
    
    # ===========================================
    # THÔNG TIN NGHỀ NGHIỆP
    # ===========================================
    
    employment_status = fields.Selection([
        ('employed', 'Đang làm việc'),
        ('self_employed', 'Tự kinh doanh'),
        ('business_owner', 'Chủ doanh nghiệp'),
        ('retired', 'Nghỉ hưu'),
        ('student', 'Sinh viên'),
        ('unemployed', 'Thất nghiệp')
    ], string='Tình trạng việc làm', required=True)
    
    employer_name = fields.Char(string='Tên công ty/Doanh nghiệp')
    job_title = fields.Char(string='Chức vụ')
    employment_length_years = fields.Integer(string='Số năm kinh nghiệm')
    industry = fields.Char(string='Ngành nghề')
    
    # ===========================================
    # THÔNG TIN LIÊN HỆ KHẨN CẤP
    # ===========================================
    
    emergency_contact_name = fields.Char(string='Tên người liên hệ khẩn cấp')
    emergency_contact_phone = fields.Char(string='Số điện thoại liên hệ khẩn cấp')
    emergency_contact_relationship = fields.Char(string='Quan hệ')
    emergency_contact_address = fields.Text(string='Địa chỉ liên hệ khẩn cấp')
    
    # ===========================================
    # THÔNG TIN PHÁP LÝ VÀ TUÂN THỦ
    # ===========================================
    
    # KYC/AML
    kyc_status = fields.Selection([
        ('pending', 'Chờ xác minh'),
        ('verified', 'Đã xác minh'),
        ('rejected', 'Từ chối'),
        ('expired', 'Hết hạn')
    ], string='Trạng thái KYC', default='pending')
    
    kyc_verification_date = fields.Date(string='Ngày xác minh KYC')
    kyc_expiry_date = fields.Date(string='KYC hết hạn')
    aml_risk_level = fields.Selection([
        ('low', 'Thấp'),
        ('medium', 'Trung bình'),
        ('high', 'Cao')
    ], string='Mức độ rủi ro AML', default='low')
    
    # Tài liệu
    id_document = fields.Binary(string='Bản sao CMND/CCCD')
    id_document_filename = fields.Char(string='Tên file CMND/CCCD')
    address_proof = fields.Binary(string='Giấy tờ chứng minh địa chỉ')
    address_proof_filename = fields.Char(string='Tên file địa chỉ')
    income_proof = fields.Binary(string='Giấy tờ chứng minh thu nhập')
    income_proof_filename = fields.Char(string='Tên file thu nhập')
    
    # ===========================================
    # THÔNG TIN ĐẦU TƯ VÀ PORTFOLIO
    # ===========================================
    
    # Portfolio
    investment_ids = fields.One2many('p2p.investment.enhanced', 'investor_id', string='Danh mục đầu tư')
    investment_count = fields.Integer(string='Số khoản đầu tư', compute='_compute_investment_stats', store=True)
    total_invested = fields.Float(string='Tổng đã đầu tư', digits=(16, 2), compute='_compute_investment_stats', store=True)
    total_returns = fields.Float(string='Tổng lợi nhuận', digits=(16, 2), compute='_compute_investment_stats', store=True)
    active_investments = fields.Integer(string='Đầu tư đang hoạt động', compute='_compute_investment_stats', store=True)
    
    # Performance metrics
    roi_percentage = fields.Float(string='ROI (%)', digits=(5, 2), compute='_compute_roi', store=True)
    average_investment_amount = fields.Float(string='Đầu tư trung bình', digits=(16, 2), compute='_compute_investment_stats', store=True)
    
    # ===========================================
    # THÔNG TIN HỆ THỐNG
    # ===========================================
    
    # Trạng thái
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('pending_verification', 'Chờ xác minh'),
        ('verified', 'Đã xác minh'),
        ('active', 'Hoạt động'),
        ('suspended', 'Tạm dừng'),
        ('blocked', 'Bị khóa'),
        ('inactive', 'Không hoạt động')
    ], string='Trạng thái', default='draft', tracking=True)
    
    # Thông tin hệ thống
    registration_date = fields.Date(string='Ngày đăng ký', default=fields.Date.today)
    last_login_date = fields.Datetime(string='Lần đăng nhập cuối')
    last_activity_date = fields.Datetime(string='Hoạt động cuối')
    notes = fields.Text(string='Ghi chú')
    
    # ===========================================
    # COMPUTED FIELDS
    # ===========================================
    
    @api.depends('first_name', 'last_name', 'middle_name')
    def _compute_display_name(self):
        for investor in self:
            name_parts = [part for part in [investor.first_name, investor.middle_name, investor.last_name] if part]
            investor.display_name = ' '.join(name_parts)
    
    @api.depends('date_of_birth')
    def _compute_age(self):
        for investor in self:
            if investor.date_of_birth:
                today = date.today()
                investor.age = today.year - investor.date_of_birth.year - ((today.month, today.day) < (investor.date_of_birth.month, investor.date_of_birth.day))
            else:
                investor.age = 0
    
    @api.depends('monthly_income')
    def _compute_annual_income(self):
        for investor in self:
            investor.annual_income = investor.monthly_income * 12 if investor.monthly_income else 0.0
    
    @api.depends('monthly_debt_payment', 'monthly_income')
    def _compute_debt_to_income_ratio(self):
        for investor in self:
            if investor.monthly_income and investor.monthly_debt_payment:
                investor.debt_to_income_ratio = (investor.monthly_debt_payment / investor.monthly_income) * 100
            else:
                investor.debt_to_income_ratio = 0.0
    
    @api.depends('investment_capacity', 'total_invested')
    def _compute_available_capital(self):
        for investor in self:
            investor.available_capital = investor.investment_capacity - investor.total_invested
    
    @api.depends('investment_ids', 'investment_ids.amount', 'investment_ids.returns', 'investment_ids.state')
    def _compute_investment_stats(self):
        for investor in self:
            investments = investor.investment_ids
            investor.investment_count = len(investments)
            investor.total_invested = sum(investments.mapped('amount'))
            investor.total_returns = sum(investments.mapped('returns'))
            investor.active_investments = len(investments.filtered(lambda x: x.state in ['confirmed', 'active']))
            investor.average_investment_amount = investor.total_invested / investor.investment_count if investor.investment_count > 0 else 0
    
    @api.depends('total_invested', 'total_returns')
    def _compute_roi(self):
        for investor in self:
            if investor.total_invested > 0:
                investor.roi_percentage = (investor.total_returns / investor.total_invested) * 100
            else:
                investor.roi_percentage = 0.0
    
    # ===========================================
    # METHODS
    # ===========================================
    
    def action_verify_kyc(self):
        """Xác minh KYC cho nhà đầu tư"""
        self.write({
            'kyc_status': 'verified',
            'kyc_verification_date': fields.Date.today(),
            'state': 'verified'
        })
    
    def action_activate(self):
        """Kích hoạt nhà đầu tư"""
        self.write({'state': 'active'})
    
    def action_suspend(self):
        """Tạm dừng nhà đầu tư"""
        self.write({'state': 'suspended'})
    
    def action_block(self):
        """Khóa nhà đầu tư"""
        self.write({'state': 'blocked'})
    
    def action_view_investments(self):
        """Xem danh mục đầu tư"""
        return {
            'name': 'Danh mục đầu tư',
            'type': 'ir.actions.act_window',
            'res_model': 'p2p.investment.enhanced',
            'view_mode': 'tree,form',
            'domain': [('investor_id', '=', self.id)],
            'context': {'default_investor_id': self.id}
        }
    
    def action_view_portfolio(self):
        """Xem portfolio chi tiết"""
        return {
            'name': 'Portfolio',
            'type': 'ir.actions.act_window',
            'res_model': 'p2p.investor.portfolio',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new'
        }
    
    # ===========================================
    # CONSTRAINTS
    # ===========================================
    
    _sql_constraints = [
        ('id_number_unique', 'UNIQUE(id_number)', 'Số CMND/CCCD đã tồn tại!'),
        ('email_unique', 'UNIQUE(email)', 'Email đã tồn tại!'),
        ('phone_unique', 'UNIQUE(phone)', 'Số điện thoại đã tồn tại!'),
    ]
