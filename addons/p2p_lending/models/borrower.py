from odoo import models, fields, api
import pandas as pd
import logging
from datetime import date

_logger = logging.getLogger(__name__)

class P2PBorrower(models.Model):
    _name = 'p2p.borrower'  # Main borrower model
    _inherit = ['p2p.base.borrower']  # Inherit from base model
    _description = 'Người vay (Extended)'

    # Thông tin cá nhân cơ bản
    name = fields.Char(string='Tên đầy đủ', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Đối tác', required=True)
    id_number = fields.Char(string='Số CMND/CCCD', tracking=True)
    id_issue_date = fields.Date(string='Ngày cấp CMND/CCCD')
    id_issue_place = fields.Char(string='Nơi cấp CMND/CCCD')
    date_of_birth = fields.Date(string='Ngày sinh', required=True)
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

    # Thông tin liên lạc
    phone = fields.Char(string='Số điện thoại di động', required=True)
    phone_home = fields.Char(string='Số điện thoại nhà')
    email = fields.Char(string='Email chính', required=True)
    email_secondary = fields.Char(string='Email phụ')

    # Thông tin địa chỉ
    address = fields.Text(string='Địa chỉ thường trú', required=True)
    address_temporary = fields.Text(string='Địa chỉ tạm trú')
    city = fields.Char(string='Thành phố/Tỉnh', required=True)
    district = fields.Char(string='Quận/Huyện', required=True)
    ward = fields.Char(string='Phường/Xã', required=True)
    postal_code = fields.Char(string='Mã bưu điện')

    # Thông tin việc làm và tài chính
    employment_status = fields.Selection([
        ('employed', 'Đang làm việc'),
        ('self_employed', 'Tự kinh doanh'),
        ('business_owner', 'Chủ doanh nghiệp'),
        ('freelancer', 'Làm việc tự do'),
        ('student', 'Sinh viên'),
        ('retired', 'Nghỉ hưu'),
        ('unemployed', 'Đang thất nghiệp')
    ], string='Tình trạng việc làm', required=True)
    employer_name = fields.Char(string='Tên công ty/Doanh nghiệp')
    employer_address = fields.Text(string='Địa chỉ công ty')
    job_title = fields.Char(string='Chức vụ')
    employment_length_years = fields.Integer(string='Số năm kinh nghiệm')
    employment_length_months = fields.Integer(string='Số tháng kinh nghiệm')

    # Thu nhập
    monthly_income = fields.Float(string='Thu nhập hàng tháng', digits=(16, 2), required=True)
    annual_income = fields.Float(string='Thu nhập hàng năm', digits=(16, 2), compute='_compute_annual_income', store=True)
    income_source = fields.Selection([
        ('salary', 'Lương'),
        ('business', 'Doanh nghiệp'),
        ('investment', 'Đầu tư'),
        ('rental', 'Cho thuê'),
        ('other', 'Khác')
    ], string='Nguồn thu nhập chính')
    spouse_income = fields.Float(string='Thu nhập của vợ/chồng', digits=(16, 2))

    # Thông tin tài chính bổ sung
    monthly_expenses = fields.Float(string='Chi phí hàng tháng', digits=(16, 2))
    dependents_count = fields.Integer(string='Số người phụ thuộc')
    home_ownership = fields.Selection([
        ('own', 'Sở hữu'),
        ('mortgage', 'Vay mua nhà'),
        ('rent', 'Thuê'),
        ('family', 'Ở với gia đình'),
        ('other', 'Khác')
    ], string='Tình trạng nhà ở', required=True)

    # Thông tin tín dụng lịch sử
    credit_score_ml = fields.Float(string='Điểm tín dụng (ML)', digits=(16, 2), compute='_compute_credit_score', store=True)
    credit_score_date = fields.Date(string='Ngày cập nhật điểm tín dụng', default=fields.Date.today)
    has_credit_history = fields.Boolean(string='Có lịch sử tín dụng')
    credit_limit = fields.Float(string='Hạn mức tín dụng hiện tại', digits=(16, 2))
    outstanding_debt = fields.Float(string='Dư nợ hiện tại', digits=(16, 2))
    delinquent_accounts = fields.Integer(string='Số tài khoản nợ xấu')
    public_records = fields.Integer(string='Số bản ghi công khai')

    # Thông tin tín dụng chi tiết cho chấm điểm
    open_accounts = fields.Integer(string='Số tài khoản tín dụng đang mở', help='Số lượng tài khoản tín dụng đang hoạt động')
    total_accounts = fields.Integer(string='Tổng số tài khoản tín dụng', help='Tổng số tài khoản tín dụng đã từng mở')
    revolving_balance = fields.Float(string='Dư nợ tín dụng quay vòng', digits=(16, 2), help='Tổng dư nợ trên các tài khoản tín dụng quay vòng')
    revolving_utilization = fields.Float(string='Tỷ lệ sử dụng tín dụng (%)', digits=(5, 2), compute='_compute_revolving_utilization', store=True, help='Tỷ lệ sử dụng hạn mức tín dụng (0-100%)')
    inquiries_last_6_months = fields.Integer(string='Số lần truy vấn tín dụng 6 tháng', help='Số lần kiểm tra tín dụng trong 6 tháng qua')
    debt_to_income_ratio = fields.Float(string='Tỷ lệ nợ/thu nhập (%)', digits=(5, 2), compute='_compute_debt_to_income_ratio', store=True, help='Tỷ lệ nợ so với thu nhập (DTI)')
    fico_range_low = fields.Integer(string='Điểm FICO thấp nhất', help='Giới hạn dưới của điểm FICO')
    fico_range_high = fields.Integer(string='Điểm FICO cao nhất', help='Giới hạn trên của điểm FICO')
    last_credit_pull_date = fields.Date(string='Ngày kiểm tra tín dụng cuối', help='Ngày cuối cùng kiểm tra báo cáo tín dụng')
    credit_utilization_trend = fields.Selection([
        ('improving', 'Đang cải thiện'),
        ('stable', 'Ổn định'),
        ('declining', 'Đang suy giảm')
    ], string='Xu hướng sử dụng tín dụng', help='Xu hướng sử dụng hạn mức tín dụng')

    # Thông tin bổ sung
    education_level = fields.Selection([
        ('high_school', 'Trung học'),
        ('college', 'Cao đẳng'),
        ('university', 'Đại học'),
        ('postgraduate', 'Sau đại học')
    ], string='Trình độ học vấn')
    nationality = fields.Char(string='Quốc tịch', default='Việt Nam')
    emergency_contact_name = fields.Char(string='Tên người liên hệ khẩn cấp')
    emergency_contact_phone = fields.Char(string='Số điện thoại liên hệ khẩn cấp')
    emergency_contact_relationship = fields.Char(string='Quan hệ với người liên hệ')
    loan_ids = fields.One2many('p2p.loan', 'borrower_id', string='Khoản vay')
    active = fields.Boolean(default=True, string='Hoạt động')
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('confirmed', 'Đã xác nhận'),
        ('done', 'Hoàn thành')
    ], string='Trạng thái', default='draft', tracking=True)
    
    _sql_constraints = [
        ('id_number_unique', 'UNIQUE(id_number)', 'Số CMND/CCCD đã tồn tại!')
    ]

    @api.depends('monthly_income')
    def _compute_annual_income(self):
        """Tính thu nhập hàng năm từ thu nhập hàng tháng"""
        for borrower in self:
            borrower.annual_income = borrower.monthly_income * 12 if borrower.monthly_income else 0.0

    @api.depends('outstanding_debt', 'credit_limit')
    def _compute_revolving_utilization(self):
        """Tính tỷ lệ sử dụng tín dụng quay vòng"""
        for borrower in self:
            if borrower.credit_limit and borrower.credit_limit > 0:
                borrower.revolving_utilization = (borrower.outstanding_debt / borrower.credit_limit) * 100
                borrower.revolving_utilization = min(borrower.revolving_utilization, 100)  # Giới hạn tối đa 100%
            else:
                borrower.revolving_utilization = 0.0

    @api.depends('monthly_income', 'monthly_expenses', 'loan_ids')
    def _compute_debt_to_income_ratio(self):
        """Tính tỷ lệ nợ/thu nhập (DTI)"""
        for borrower in self:
            if not borrower.monthly_income:
                borrower.debt_to_income_ratio = 0.0
                continue

            # Tính tổng nợ hàng tháng
            monthly_debt = 0.0

            # Bao gồm các khoản vay đang hoạt động
            active_loans = borrower.loan_ids.filtered(lambda l: l.state in ['disbursed', 'in_progress'])
            monthly_debt += sum(active_loans.mapped('monthly_payment'))

            # Bao gồm chi phí hàng tháng khác
            if borrower.monthly_expenses:
                monthly_debt += borrower.monthly_expenses

            # Tính DTI
            borrower.debt_to_income_ratio = (monthly_debt / borrower.monthly_income) * 100
            borrower.debt_to_income_ratio = min(borrower.debt_to_income_ratio, 100)  # Giới hạn tối đa 100%

    @api.depends('monthly_income', 'employment_status', 'loan_ids', 'date_of_birth', 'annual_income',
                 'employment_length_years', 'home_ownership', 'delinquent_accounts', 'public_records',
                 'outstanding_debt', 'credit_limit', 'dependents_count', 'monthly_expenses',
                 'open_accounts', 'total_accounts', 'revolving_balance', 'revolving_utilization',
                 'inquiries_last_6_months', 'debt_to_income_ratio', 'fico_range_low', 'fico_range_high')
    def _compute_credit_score(self):
        """Tự động tính điểm tín dụng dựa trên mô hình ML đã được train"""
        for borrower in self:
            if not borrower.monthly_income:
                borrower.credit_score_ml = 0.0
                continue

            try:
                # Lấy mô hình PD active từ lending_club_analysis module
                risk_model = self.env['credit.risk.model'].search([
                    ('model_type', '=', 'pd'),
                    ('is_active', '=', True)
                ], limit=1)

                if risk_model:
                    # Chuẩn bị features theo format của mô hình
                    features = self._prepare_borrower_features_for_ml(borrower)

                    if features:
                        # Dự đoán PD sử dụng mô hình ML
                        pd_value = risk_model.predict_pd(features)

                        # Chuyển đổi PD sang điểm tín dụng (FICO-like scale)
                        # PD thấp = điểm cao, PD cao = điểm thấp
                        score = 850 - 550 * pd_value
                        score = max(300, min(850, score))

                        borrower.credit_score_ml = score
                        _logger.info(f"Đã tính điểm tín dụng cho borrower {borrower.id}: {score:.2f} (PD: {pd_value:.4f})")
                    else:
                        borrower.credit_score_ml = 0.0
                        _logger.warning(f"Không thể chuẩn bị features cho borrower {borrower.id}")
                else:
                    # Không có model active, sử dụng điểm mặc định
                    borrower.credit_score_ml = self._calculate_default_credit_score(borrower)
                    _logger.info(f"Sử dụng điểm mặc định cho borrower {borrower.id}: {borrower.credit_score:.2f} (không có model PD active)")

            except Exception as e:
                _logger.error(f"Lỗi tính điểm tín dụng cho borrower {borrower.id}: {e}")
                # Nếu có lỗi, đặt điểm mặc định dựa trên thu nhập
                borrower.credit_score_ml = self._calculate_default_credit_score(borrower)

    def _calculate_default_credit_score(self, borrower):
        """Tính điểm tín dụng mặc định khi không có model ML"""
        if not borrower.monthly_income:
            return 0.0

        # Điểm cơ bản dựa trên thu nhập (300-700)
        base_score = 300 + min(400, (borrower.monthly_income / 100) * 2)

        # Điều chỉnh dựa trên tình trạng việc làm
        if borrower.employment_status in ['employed', 'self_employed', 'business_owner']:
            base_score += 50
        elif borrower.employment_status == 'student':
            base_score -= 50

        # Điều chỉnh dựa trên home ownership
        if borrower.home_ownership == 'own':
            base_score += 30
        elif borrower.home_ownership == 'mortgage':
            base_score += 20

        # Điều chỉnh dựa trên lịch sử tín dụng
        if borrower.delinquent_accounts and borrower.delinquent_accounts > 0:
            base_score -= borrower.delinquent_accounts * 20
        if borrower.public_records and borrower.public_records > 0:
            base_score -= borrower.public_records * 30

        # Đảm bảo trong khoảng 300-700
        return max(300, min(700, base_score))

    def _prepare_borrower_features(self, borrower):
        """Chuẩn bị features cho borrower"""
        features = {}

        # Thu nhập hàng tháng
        if borrower.monthly_income:
            features['monthly_income'] = borrower.monthly_income

        # Tình trạng việc làm
        if borrower.employment_status:
            employment_map = {
                'employed': 1,
                'self_employed': 2,
                'student': 3,
                'unemployed': 4
            }
            features['employment_status'] = employment_map.get(borrower.employment_status, 0)

        # Tuổi
        if borrower.date_of_birth:
            age = date.today().year - borrower.date_of_birth.year
            features['age'] = age

        # Số lượng khoản vay hiện tại
        active_loans = borrower.loan_ids.filtered(lambda l: l.state in ['disbursed', 'in_progress'])
        features['active_loans_count'] = len(active_loans)
        features['active_loans_amount'] = sum(active_loans.mapped('amount'))

        if features:
            return pd.DataFrame([features])
        return False

    def _prepare_borrower_features_for_ml(self, borrower):
        """Chuẩn bị features theo format của mô hình ML đã được train với thông tin đầy đủ"""
        # Lấy thông tin khoản vay gần nhất để làm cơ sở
        latest_loan = borrower.loan_ids.filtered(lambda l: l.state != 'draft').sorted('create_date', reverse=True)[:1]

        # Giá trị mặc định cho các features
        features = {
            'loan_amnt': latest_loan.amount if latest_loan else borrower.monthly_income * 3,  # Ước tính dựa trên thu nhập
            'int_rate': latest_loan.interest_rate if latest_loan else 10.0,  # Lãi suất mặc định
            'installment': latest_loan.monthly_payment if latest_loan else (borrower.monthly_income * 3 * 0.1 / 12),  # Ước tính
            'annual_inc': borrower.annual_income or (borrower.monthly_income * 12) or 50000,  # Thu nhập năm
            'dti': borrower.debt_to_income_ratio or 20.0,  # Sử dụng DTI đã tính
            'delinq_2yrs': borrower.delinquent_accounts or 0,  # Số tài khoản nợ xấu
            'pub_rec': borrower.public_records or 0,  # Số bản ghi công khai
            'fico_range_low': borrower.fico_range_low or 650,  # FICO score từ borrower
            'fico_range_high': borrower.fico_range_high or 700,
            'open_acc': borrower.open_accounts or 2,  # Số tài khoản mở từ borrower
            'total_acc': borrower.total_accounts or 5,  # Tổng số tài khoản từ borrower
            'revol_bal': borrower.revolving_balance or borrower.outstanding_debt or 1000,  # Dư nợ quay vòng
            'revol_util': borrower.revolving_utilization or 30.0,  # Tỷ lệ sử dụng tín dụng
            'inq_last_6mths': borrower.inquiries_last_6_months or 1,  # Số lần truy vấn 6 tháng
            'emp_length_num': borrower.employment_length_years or 3  # Số năm kinh nghiệm
        }

        # Cập nhật với thông tin thực tế từ borrower
        if borrower.annual_income:
            features['annual_inc'] = borrower.annual_income

        # Tính tuổi và cập nhật emp_length_num
        if borrower.date_of_birth:
            age = date.today().year - borrower.date_of_birth.year
            # Nếu không có thông tin kinh nghiệm, ước tính dựa trên tuổi
            if not borrower.employment_length_years:
                features['emp_length_num'] = max(0, age - 22)  # Giả sử bắt đầu làm việc từ 22 tuổi
            else:
                features['emp_length_num'] = borrower.employment_length_years

        # Tính DTI (Debt-to-Income Ratio) chi tiết hơn
        active_loans = borrower.loan_ids.filtered(lambda l: l.state in ['disbursed', 'in_progress'])
        monthly_debt = sum(active_loans.mapped('monthly_payment')) if active_loans else 0

        # Bao gồm các chi phí khác nếu có
        total_monthly_debt = monthly_debt
        if borrower.monthly_expenses:
            total_monthly_debt += borrower.monthly_expenses

        if borrower.monthly_income and total_monthly_debt > 0:
            features['dti'] = (total_monthly_debt / borrower.monthly_income) * 100
            features['dti'] = min(features['dti'], 100)  # Giới hạn tối đa 100%

        # Cập nhật thông tin tài khoản tín dụng
        features['open_acc'] = len(active_loans) if active_loans else 1
        features['total_acc'] = len(borrower.loan_ids) if borrower.loan_ids else 2

        # Cập nhật thông tin tín dụng lịch sử
        if borrower.delinquent_accounts is not None:
            features['delinq_2yrs'] = borrower.delinquent_accounts

        if borrower.public_records is not None:
            features['pub_rec'] = borrower.public_records

        # Cập nhật FICO score dựa trên credit_limit và outstanding_debt
        if borrower.credit_limit and borrower.outstanding_debt:
            utilization = (borrower.outstanding_debt / borrower.credit_limit) * 100
            features['revol_util'] = min(utilization, 100)

            # Ước tính FICO score dựa trên utilization
            if utilization < 10:
                features['fico_range_low'] = 750
                features['fico_range_high'] = 800
            elif utilization < 30:
                features['fico_range_low'] = 700
                features['fico_range_high'] = 750
            elif utilization < 50:
                features['fico_range_low'] = 650
                features['fico_range_high'] = 700
            else:
                features['fico_range_low'] = 600
                features['fico_range_high'] = 650

        # Cập nhật revol_bal
        if borrower.outstanding_debt:
            features['revol_bal'] = borrower.outstanding_debt

        return features

    def action_view_loans(self):
        """
        This action opens the loan list view for the current borrower
        """
        self.ensure_one()
        return {
            'name': 'Khoản vay',
            'type': 'ir.actions.act_window',
            'res_model': 'p2p.loan',
            'view_mode': 'tree,form',
            'domain': [('borrower_id', '=', self.id)],
            'context': {
                'default_borrower_id': self.id,
                'search_default_borrower_id': self.id,
                'default_state': 'draft',
            }
        }