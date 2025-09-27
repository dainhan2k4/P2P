# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
import json
import logging

logger = logging.getLogger(__name__)

class P2PDashboard(models.Model):
    _name = 'p2p.dashboard'
    _description = 'Bảng điều khiển P2P Lending Core'
    _rec_name = 'name'

    name = fields.Char('Tên', required=True, default="Bảng điều khiển P2P Core")
    date_from = fields.Date('Từ ngày', default=lambda self: (date.today().replace(day=1) - timedelta(days=180)))
    date_to = fields.Date('Đến ngày', default=fields.Date.today)
    company_id = fields.Many2one('res.company', string='Công ty', default=lambda self: self.env.company)
    prefer_bridge = fields.Boolean('Ưu tiên dữ liệu bridge (p2p.*)', default=False)
    loan_data_source = fields.Char('Nguồn dữ liệu hồ sơ vay', readonly=True)
    disb_data_source = fields.Char('Nguồn dữ liệu giải ngân', readonly=True)
    
    # ===== THỐNG KÊ TỔNG QUAN =====
    # System Health 
    access_status = fields.Text('Trạng thái quyền truy cập', compute='_compute_access_status')
    models_accessible = fields.Boolean('Models có thể truy cập', compute='_compute_access_status')
    
    # Loan Applications
    total_loan_applications = fields.Integer('Tổng hồ sơ vay', compute='_compute_loan_application_stats')
    total_loan_application_amount = fields.Float('Tổng giá trị đăng ký vay', compute='_compute_loan_application_stats')
    approved_applications = fields.Integer('Hồ sơ đã phê duyệt', compute='_compute_loan_application_stats')
    rejected_applications = fields.Integer('Hồ sơ bị từ chối', compute='_compute_loan_application_stats')
    pending_applications = fields.Integer('Hồ sơ chờ duyệt', compute='_compute_loan_application_stats')
    approval_rate = fields.Float('Tỷ lệ phê duyệt (%)', compute='_compute_loan_application_stats')
    average_loan_amount = fields.Float('Giá trị vay trung bình', compute='_compute_loan_application_stats')
    average_interest_rate = fields.Float('Lãi suất trung bình (%)', compute='_compute_loan_application_stats')
    
    # Disbursements
    total_disbursements = fields.Integer('Tổng số giải ngân', compute='_compute_disbursement_stats')
    total_disbursed_amount = fields.Float('Tổng số tiền đã giải ngân', compute='_compute_disbursement_stats')
    pending_disbursements = fields.Integer('Chờ giải ngân', compute='_compute_disbursement_stats')
    completed_disbursements = fields.Integer('Đã giải ngân', compute='_compute_disbursement_stats')
    disbursement_success_rate = fields.Float('Tỷ lệ giải ngân thành công (%)', compute='_compute_disbursement_stats')
    
    # Users & Risk
    total_borrowers = fields.Integer('Tổng số người vay', compute='_compute_user_stats')
    high_risk_borrowers = fields.Integer('Người vay rủi ro cao', compute='_compute_user_stats')
    average_credit_score = fields.Float('Điểm tín dụng trung bình', compute='_compute_user_stats')
    
    # System Health
    total_wallets = fields.Integer('Tổng ví điện tử', compute='_compute_system_stats')
    total_wallet_balance = fields.Float('Tổng số dư ví', compute='_compute_system_stats')
    sync_success_rate = fields.Float('Tỷ lệ đồng bộ thành công (%)', compute='_compute_system_stats')
    
    # ===== BIỂU ĐỒ PHÂN TÍCH =====
    # Loan Application Charts
    chart_application_status = fields.Json('Trạng thái hồ sơ vay', compute='_compute_loan_application_stats')
    chart_loan_amount_by_status = fields.Json('Giá trị vay theo trạng thái', compute='_compute_loan_application_stats')
    # BỔ SUNG: Các biểu đồ theo tiêu chí
    chart_loans_by_type = fields.Json('Phân bổ khoản vay theo loại', compute='_compute_loan_application_stats')
    chart_loans_by_purpose = fields.Json('Khoản vay theo mục đích', compute='_compute_loan_application_stats')
    chart_loans_by_credit_tier = fields.Json('Khoản vay theo mức điểm tín dụng', compute='_compute_loan_application_stats')
    # Nhãn hiển thị tiêu chí nhóm (tùy theo nguồn dữ liệu Core/Bridge)
    loans_by_type_label = fields.Char('Tiêu chí nhóm (loans by type)', readonly=True)
    loans_by_purpose_label = fields.Char('Tiêu chí nhóm (loans by purpose)', readonly=True)
    # ĐÃ LOẠI BỎ: Các biểu đồ không có dữ liệu thực tế để tinh gọn mã nguồn
    
    # Disbursement Charts
    chart_disbursement_status = fields.Json('Trạng thái giải ngân', compute='_compute_disbursement_stats')
    # ĐÃ LOẠI BỎ: chart_disbursement_methods, chart_disbursement_by_month, chart_blockchain_status
    
    # User Analysis Charts
    # ĐÃ LOẠI BỎ: Các biểu đồ phân tích người dùng để tinh gọn
    
    # System Performance Charts
    # ĐÃ LOẠI BỎ: Các biểu đồ hệ thống không có dữ liệu
    
    # Financial Analysis Charts
    # ĐÃ LOẠI BỎ: Các biểu đồ phân tích tài chính

    def _check_model_access(self, model_name):
        """Kiểm tra quyền truy cập model"""
        try:
            model = self.env[model_name]
            # Kiểm tra quyền read
            model.check_access_rights('read')
            return True
        except Exception as e:
            logger.warning(f"No access to model {model_name}: {e}")
            return False

    @api.depends('date_from', 'date_to')
    def _compute_access_status(self):
        """Kiểm tra trạng thái quyền truy cập các model"""
        for dashboard in self:
            models_to_check = [
                'loan.application',
                'loan.disbursement', 
                'loan.type',
                'p2p.wallet',
                'p2p.borrower'
            ]
            
            access_results = {}
            all_accessible = True
            
            for model_name in models_to_check:
                accessible = dashboard._check_model_access(model_name)
                access_results[model_name] = accessible
                if not accessible:
                    all_accessible = False
            
            # Tạo thông báo trạng thái
            status_lines = []
            for model_name, accessible in access_results.items():
                status = "✅ Có quyền" if accessible else "❌ Không có quyền"
                status_lines.append(f"{model_name}: {status}")
            
            dashboard.access_status = "\n".join(status_lines)
            dashboard.models_accessible = all_accessible

    @api.depends('date_from', 'date_to', 'prefer_bridge')
    def _compute_loan_application_stats(self):
        """Thống kê hồ sơ vay từ P2P Lending Core"""
        for dashboard in self:
            try:
                # Kiểm tra quyền truy cập models
                if not self._check_model_access('loan.application'):
                    raise Exception("No access to loan.application model")
                if not self._check_model_access('loan.type'):
                    logger.warning("No access to loan.type model - some features may be limited")
                
                # Xác định nguồn dữ liệu theo prefer_bridge và fallback hợp lý
                applications = self.env['loan.application'].browse([])
                using_fallback = False
                try:
                    if dashboard.prefer_bridge and self._check_model_access('p2p.loan'):
                        dfrom_dt = datetime.combine(dashboard.date_from, datetime.min.time()) if dashboard.date_from else False
                        dto_dt = datetime.combine(dashboard.date_to, datetime.max.time()) if dashboard.date_to else False
                        loan_domain = ['|',
                                       '&', ('start_date', '>=', dashboard.date_from), ('start_date', '<=', dashboard.date_to),
                                       '&', ('create_date', '>=', dfrom_dt), ('create_date', '<=', dto_dt)]
                        applications = self.env['p2p.loan'].search(loan_domain)
                        using_fallback = True
                        # Nếu bridge không có, thử Core
                        if not applications:
                            application_domain = [
                                ('application_date', '>=', dashboard.date_from), 
                                ('application_date', '<=', dashboard.date_to)
                            ]
                            applications = self.env['loan.application'].search(application_domain)
                            using_fallback = False
                    else:
                        # Mặc định: Core trước, nếu trống thì bridge
                        application_domain = [
                            ('application_date', '>=', dashboard.date_from), 
                            ('application_date', '<=', dashboard.date_to)
                        ]
                        applications = self.env['loan.application'].search(application_domain)
                        if not applications and self._check_model_access('p2p.loan'):
                            dfrom_dt = datetime.combine(dashboard.date_from, datetime.min.time()) if dashboard.date_from else False
                            dto_dt = datetime.combine(dashboard.date_to, datetime.max.time()) if dashboard.date_to else False
                            loan_domain = ['|',
                                           '&', ('start_date', '>=', dashboard.date_from), ('start_date', '<=', dashboard.date_to),
                                           '&', ('create_date', '>=', dfrom_dt), ('create_date', '<=', dto_dt)]
                            applications = self.env['p2p.loan'].search(loan_domain)
                            if applications:
                                using_fallback = True
                except Exception as fe:
                    logger.info(f"Source selection for loans failed: {fe}")
                dashboard.total_loan_applications = len(applications)
                dashboard.total_loan_application_amount = sum(getattr(app, 'amount', 0) or 0 for app in applications)
                
                # Thống kê theo trạng thái
                if not using_fallback:
                    dashboard.approved_applications = len(applications.filtered(lambda a: a.status == 'approved'))
                    dashboard.rejected_applications = len(applications.filtered(lambda a: a.status == 'rejected'))
                    dashboard.pending_applications = len(applications.filtered(lambda a: a.status in ['draft', 'submitted', 'under_review']))
                else:
                    # Map trạng thái từ p2p.loan
                    approved_like = [a for a in applications if getattr(a, 'status', '') in ['active', 'completed']]
                    rejected_like = [a for a in applications if getattr(a, 'status', '') in ['cancelled']]
                    pending_like = [a for a in applications if getattr(a, 'status', '') in ['pending']]
                    dashboard.approved_applications = len(approved_like)
                    dashboard.rejected_applications = len(rejected_like)
                    dashboard.pending_applications = len(pending_like)
                
                # Tỷ lệ phê duyệt
                total_processed = dashboard.approved_applications + dashboard.rejected_applications
                dashboard.approval_rate = (dashboard.approved_applications / total_processed * 100) if total_processed > 0 else 0
                
                # Giá trị trung bình
                dashboard.average_loan_amount = dashboard.total_loan_application_amount / dashboard.total_loan_applications if dashboard.total_loan_applications > 0 else 0
                
                # Lãi suất trung bình
                interest_rates = [getattr(app, 'interest_rate', 0) for app in applications if getattr(app, 'interest_rate', 0) and getattr(app, 'interest_rate', 0) > 0]
                dashboard.average_interest_rate = sum(interest_rates) / len(interest_rates) if interest_rates else 0
                
                # === BIỂU ĐỒ ===
                
                # 1. Trạng thái hồ sơ vay
                status_counts = {}
                status_amounts = {}
                status_labels = {
                    'draft': 'Nháp',
                    'submitted': 'Đã nộp',
                    'under_review': 'Đang xem xét',
                    'approved': 'Đã phê duyệt',
                    'rejected': 'Từ chối',
                    'disbursed': 'Đã giải ngân',
                    'active': 'Đang hoạt động',
                    'completed': 'Hoàn thành',
                    'defaulted': 'Quá hạn'
                }
                
                for app in applications:
                    st = getattr(app, 'status', 'draft') or 'draft'
                    if using_fallback:
                        mapping = {
                            'pending': 'submitted',
                            'active': 'active',
                            'completed': 'completed',
                            'cancelled': 'rejected',
                        }
                        status = mapping.get(st, st)
                    else:
                        status = st
                    amt = getattr(app, 'amount', 0) or 0
                    status_counts[status] = status_counts.get(status, 0) + 1
                    status_amounts[status] = status_amounts.get(status, 0) + amt
                
                dashboard.chart_application_status = json.dumps({
                    'labels': [status_labels.get(k, k) for k in status_counts.keys()],
                    'datasets': [{
                        'label': 'Số lượng hồ sơ',
                        'data': list(status_counts.values()),
                        'backgroundColor': self._get_status_colors(list(status_counts.keys()))
                    }]
                })
                
                dashboard.chart_loan_amount_by_status = json.dumps({
                    'labels': [status_labels.get(k, k) for k in status_amounts.keys()],
                    'datasets': [{
                        'label': 'Giá trị vay (VNĐ)',
                        'data': list(status_amounts.values()),
                        'backgroundColor': self._get_status_colors(list(status_amounts.keys()))
                    }]
                })
                
                # Ghi nhận nguồn dữ liệu đã dùng
                dashboard.loan_data_source = 'Bridge (p2p.loan)' if using_fallback else 'Core (loan.application)'

                # ĐÃ LOẠI BỎ: Các biểu đồ không cần thiết để tinh gọn
                
                # === BIỂU ĐỒ BỔ SUNG THEO TIÊU CHÍ ===
                # 2. Phân bổ theo tiêu chí "loại" (Core) hoặc "kỳ hạn" (Bridge)
                type_counts = {}
                if not using_fallback:
                    # CORE: nhóm theo loan_type_id.name hoặc thuộc tính tương đương
                    for app in applications:
                        tname = None
                        try:
                            tname = getattr(getattr(app, 'loan_type_id', None), 'name', None)
                        except Exception:
                            tname = None
                        if not tname:
                            tname = getattr(app, 'loan_type_name', None) or getattr(app, 'type', None) or 'Không xác định'
                        type_counts[tname] = type_counts.get(tname, 0) + 1
                    dashboard.loans_by_type_label = 'Loại vay (Core)'
                else:
                    # BRIDGE: không có loan_type, nhóm theo "kỳ hạn (tháng)" buckets
                    def term_bucket(m):
                        try:
                            m = int(m or 0)
                        except Exception:
                            m = 0
                        if m <= 3:
                            return '≤ 3 tháng'
                        if m <= 6:
                            return '4–6 tháng'
                        if m <= 9:
                            return '7–9 tháng'
                        if m <= 12:
                            return '10–12 tháng'
                        return '> 12 tháng'
                    for app in applications:
                        bucket = term_bucket(getattr(app, 'term_months', 0))
                        type_counts[bucket] = type_counts.get(bucket, 0) + 1
                    dashboard.loans_by_type_label = 'Kỳ hạn (tháng) (Bridge)'
                labels_types = list(type_counts.keys())
                data_types = [type_counts[k] for k in labels_types]
                colors_types = self._get_chart_colors(len(labels_types))
                dashboard.chart_loans_by_type = json.dumps({
                    'labels': labels_types,
                    'datasets': [{
                        'label': 'Số lượng hồ sơ',
                        'data': data_types,
                        'backgroundColor': colors_types.get('backgroundColor')
                    }]
                })

                # 3. Khoản vay theo mục đích (Core) hoặc theo khoảng tiền (Bridge)
                if not using_fallback:
                    purpose_counts = {}
                    for app in applications:
                        purpose = (getattr(app, 'purpose', None) or '').strip() or 'Không xác định'
                        purpose_counts[purpose] = purpose_counts.get(purpose, 0) + 1
                    sorted_purposes = sorted(purpose_counts.items(), key=lambda x: x[1], reverse=True)
                    top_n = 6
                    top_labels = [p for p, _ in sorted_purposes[:top_n]]
                    top_values = [purpose_counts[p] for p in top_labels]
                    other_total = sum(v for _, v in sorted_purposes[top_n:])
                    if other_total:
                        top_labels.append('Khác')
                        top_values.append(other_total)
                    colors_purpose = self._get_chart_colors(len(top_labels))
                    dashboard.chart_loans_by_purpose = json.dumps({
                        'labels': top_labels,
                        'datasets': [{
                            'label': 'Số lượng hồ sơ',
                            'data': top_values,
                            'backgroundColor': colors_purpose.get('backgroundColor')
                        }]
                    })
                    dashboard.loans_by_purpose_label = 'Mục đích vay (Core)'
                else:
                    # BRIDGE: không có purpose, nhóm theo khoảng tiền vay
                    def amount_bucket(a):
                        try:
                            a = float(a or 0)
                        except Exception:
                            a = 0.0
                        if a <= 2_000_000:
                            return '≤ 2 triệu'
                        if a <= 5_000_000:
                            return '2–5 triệu'
                        if a <= 10_000_000:
                            return '5–10 triệu'
                        if a <= 20_000_000:
                            return '10–20 triệu'
                        if a <= 40_000_000:
                            return '20–40 triệu'
                        return '> 40 triệu'
                    amount_counts = {}
                    for app in applications:
                        bucket = amount_bucket(getattr(app, 'amount', 0))
                        amount_counts[bucket] = amount_counts.get(bucket, 0) + 1
                    labels_amt = list(amount_counts.keys())
                    data_amt = [amount_counts[k] for k in labels_amt]
                    colors_amt = self._get_chart_colors(len(labels_amt))
                    dashboard.chart_loans_by_purpose = json.dumps({
                        'labels': labels_amt,
                        'datasets': [{
                            'label': 'Số lượng hồ sơ',
                            'data': data_amt,
                            'backgroundColor': colors_amt.get('backgroundColor')
                        }]
                    })
                    dashboard.loans_by_purpose_label = 'Khoảng tiền vay (Bridge)'

                # 4. Khoản vay theo mức điểm tín dụng
                def credit_tier(score):
                    try:
                        s = float(score)
                    except Exception:
                        return 'Không có điểm'
                    if s < 580:
                        return 'Rất thấp (<580)'
                    if s < 670:
                        return 'Thấp (580-669)'
                    if s < 740:
                        return 'Trung bình (670-739)'
                    if s < 800:
                        return 'Cao (740-799)'
                    return 'Rất cao (≥800)'
                tier_counts = {}
                for app in applications:
                    # Core: credit_score trên loan.application; Bridge: lấy từ borrower.credit_score
                    cs = getattr(app, 'credit_score', None)
                    if using_fallback and cs in (None, False):
                        try:
                            cs = getattr(getattr(app, 'borrower_id', None), 'credit_score', None)
                        except Exception:
                            cs = None
                    tier = credit_tier(cs)
                    tier_counts[tier] = tier_counts.get(tier, 0) + 1
                labels_tier = list(tier_counts.keys())
                data_tier = [tier_counts[k] for k in labels_tier]
                colors_tier = self._get_chart_colors(len(labels_tier))
                dashboard.chart_loans_by_credit_tier = json.dumps({
                    'labels': labels_tier,
                    'datasets': [{
                        'label': 'Số lượng hồ sơ',
                        'data': data_tier,
                        'backgroundColor': colors_tier.get('backgroundColor')
                    }]
                })
                
            except Exception as e:
                logger.warning(f"_compute_loan_application_stats skipped due to: {e}")
                # Reset các giá trị về 0
                dashboard.total_loan_applications = 0
                dashboard.total_loan_application_amount = 0
                dashboard.approved_applications = 0
                dashboard.rejected_applications = 0
                dashboard.pending_applications = 0
                dashboard.approval_rate = 0
                dashboard.average_loan_amount = 0
                dashboard.average_interest_rate = 0
                dashboard.chart_application_status = json.dumps({'labels': [], 'datasets': []})
                dashboard.chart_loan_amount_by_status = json.dumps({'labels': [], 'datasets': []})
                dashboard.chart_loans_by_type = json.dumps({'labels': [], 'datasets': []})
                dashboard.chart_loans_by_purpose = json.dumps({'labels': [], 'datasets': []})
                dashboard.chart_loans_by_credit_tier = json.dumps({'labels': [], 'datasets': []})
                dashboard.loan_data_source = ''
                dashboard.loans_by_type_label = ''
                dashboard.loans_by_purpose_label = ''
                # Các biểu đồ đã loại bỏ không cần reset

    # ĐÃ LOẠI BỎ: _compute_loan_trend_data

    @api.depends('date_from', 'date_to', 'prefer_bridge')
    def _compute_disbursement_stats(self):
        """Thống kê giải ngân từ P2P Lending Core"""
        for dashboard in self:
            try:
                # Kiểm tra quyền truy cập
                if not self._check_model_access('loan.disbursement'):
                    raise Exception("No access to loan.disbursement model")
                
                # Xác định nguồn dữ liệu theo prefer_bridge và fallback hợp lý
                disbursements = self.env['loan.disbursement'].browse([])
                using_fallback = False
                try:
                    if dashboard.prefer_bridge and self._check_model_access('p2p.investment'):
                        dfrom_dt = datetime.combine(dashboard.date_from, datetime.min.time()) if dashboard.date_from else False
                        dto_dt = datetime.combine(dashboard.date_to, datetime.max.time()) if dashboard.date_to else False
                        inv_domain = ['|',
                                      '&', ('start_date', '>=', dashboard.date_from), ('start_date', '<=', dashboard.date_to),
                                      '&', ('create_date', '>=', dfrom_dt), ('create_date', '<=', dto_dt)]
                        disbursements = self.env['p2p.investment'].search(inv_domain)
                        using_fallback = True
                        if not disbursements:
                            disbursement_domain = [
                                ('disbursement_date', '>=', dashboard.date_from), 
                                ('disbursement_date', '<=', dashboard.date_to)
                            ]
                            disbursements = self.env['loan.disbursement'].search(disbursement_domain)
                            using_fallback = False
                    else:
                        disbursement_domain = [
                            ('disbursement_date', '>=', dashboard.date_from), 
                            ('disbursement_date', '<=', dashboard.date_to)
                        ]
                        disbursements = self.env['loan.disbursement'].search(disbursement_domain)
                        if not disbursements and self._check_model_access('p2p.investment'):
                            dfrom_dt = datetime.combine(dashboard.date_from, datetime.min.time()) if dashboard.date_from else False
                            dto_dt = datetime.combine(dashboard.date_to, datetime.max.time()) if dashboard.date_to else False
                            inv_domain = ['|',
                                          '&', ('start_date', '>=', dashboard.date_from), ('start_date', '<=', dashboard.date_to),
                                          '&', ('create_date', '>=', dfrom_dt), ('create_date', '<=', dto_dt)]
                            disbursements = self.env['p2p.investment'].search(inv_domain)
                            if disbursements:
                                using_fallback = True
                except Exception as fe:
                    logger.info(f"Source selection for disbursements failed: {fe}")
                dashboard.total_disbursements = len(disbursements)
                dashboard.total_disbursed_amount = sum(getattr(d, 'amount', 0) or 0 for d in disbursements)
                
                # Thống kê theo trạng thái
                if not using_fallback:
                    dashboard.pending_disbursements = len(disbursements.filtered(lambda d: d.status in ['draft', 'pending', 'approved']))
                    dashboard.completed_disbursements = len(disbursements.filtered(lambda d: d.status == 'disbursed'))
                else:
                    # p2p.investment status: pending/active/completed/cancelled
                    dashboard.pending_disbursements = len([d for d in disbursements if getattr(d, 'status', '') in ['pending', 'active']])
                    dashboard.completed_disbursements = len([d for d in disbursements if getattr(d, 'status', '') in ['completed']])
                
                # Tỷ lệ thành công
                dashboard.disbursement_success_rate = (dashboard.completed_disbursements / dashboard.total_disbursements * 100) if dashboard.total_disbursements > 0 else 0
                
                # === BIỂU ĐỒ ===
                
                # 1. Trạng thái giải ngân
                status_counts = {}
                status_labels = {
                    'draft': 'Nháp',
                    'pending': 'Chờ phê duyệt',
                    'approved': 'Đã phê duyệt',
                    'processing': 'Đang xử lý',
                    'disbursed': 'Đã giải ngân',
                    'rejected': 'Từ chối',
                    'cancelled': 'Đã hủy'
                }
                
                for disbursement in disbursements:
                    st = getattr(disbursement, 'status', 'draft') or 'draft'
                    if using_fallback:
                        mapping = {
                            'pending': 'pending',
                            'active': 'approved',
                            'completed': 'disbursed',
                            'cancelled': 'cancelled',
                        }
                        status = mapping.get(st, st)
                    else:
                        status = st
                    status_counts[status] = status_counts.get(status, 0) + 1
                
                dashboard.chart_disbursement_status = json.dumps({
                    'labels': [status_labels.get(k, k) for k in status_counts.keys()],
                    'datasets': [{
                        'label': 'Số lượng giải ngân',
                        'data': list(status_counts.values()),
                        'backgroundColor': self._get_status_colors(list(status_counts.keys()))
                    }]
                })
                # Ghi nhận nguồn dữ liệu đã dùng
                dashboard.disb_data_source = 'Bridge (p2p.investment)' if using_fallback else 'Core (loan.disbursement)'
                
                # ĐÃ LOẠI BỎ: Phương thức giải ngân, trạng thái blockchain
                
            except Exception as e:
                logger.warning(f"_compute_disbursement_stats skipped due to: {e}")
                dashboard.total_disbursements = 0
                dashboard.total_disbursed_amount = 0
                dashboard.pending_disbursements = 0
                dashboard.completed_disbursements = 0
                dashboard.disbursement_success_rate = 0
                dashboard.chart_disbursement_status = json.dumps({'labels': [], 'datasets': []})
                dashboard.disb_data_source = ''
                # Các biểu đồ đã loại bỏ không cần reset

    # ĐÃ LOẠI BỎ: _compute_disbursement_trend_data

    @api.depends('date_from', 'date_to', 'prefer_bridge')
    def _compute_user_stats(self):
        """Thống kê người dùng từ P2P Lending Core"""
        for dashboard in self:
            try:
                # Kiểm tra quyền truy cập
                if not self._check_model_access('loan.application'):
                    raise Exception("No access to loan.application model")
                
                # Lấy tất cả hồ sơ vay trong khoảng thời gian
                applications = self.env['loan.application'].search([
                    ('application_date', '>=', dashboard.date_from), 
                    ('application_date', '<=', dashboard.date_to)
                ])
                using_fallback = False
                if not applications and self._check_model_access('p2p.loan'):
                    try:
                        dfrom_dt = datetime.combine(dashboard.date_from, datetime.min.time()) if dashboard.date_from else False
                        dto_dt = datetime.combine(dashboard.date_to, datetime.max.time()) if dashboard.date_to else False
                        loan_domain = ['|',
                                       '&', ('start_date', '>=', dashboard.date_from), ('start_date', '<=', dashboard.date_to),
                                       '&', ('create_date', '>=', dfrom_dt), ('create_date', '<=', dto_dt)]
                        applications = self.env['p2p.loan'].search(loan_domain)
                        if applications:
                            using_fallback = True
                    except Exception as fe:
                        logger.info(f"Fallback user stats p2p.loan failed: {fe}")
                
                # Tính unique borrowers
                if not using_fallback:
                    unique_borrowers = set(app.borrower_id.id for app in applications if getattr(app, 'borrower_id', False))
                else:
                    # p2p.loan.borrower_id trỏ tới p2p.borrower (khác model), chỉ đếm theo id
                    unique_borrowers = set(getattr(app, 'borrower_id', False).id for app in applications if getattr(app, 'borrower_id', False))
                dashboard.total_borrowers = len(unique_borrowers)
                
                # Người vay rủi ro cao (credit_score < 600)
                high_risk_count = 0
                total_credit_scores = []
                
                for app in applications:
                    # Nếu dùng bridge, lấy điểm tín dụng từ borrower
                    cs = getattr(app, 'credit_score', None)
                    if using_fallback and cs in (None, False):
                        try:
                            cs = getattr(getattr(app, 'borrower_id', None), 'credit_score', None)
                        except Exception:
                            cs = None
                    if cs is not None:
                        total_credit_scores.append(cs)
                        if cs < 600:
                            high_risk_count += 1
                
                dashboard.high_risk_borrowers = high_risk_count
                dashboard.average_credit_score = sum(total_credit_scores) / len(total_credit_scores) if total_credit_scores else 0
                
                # ĐÃ LOẠI BỎ: Các biểu đồ phân tích người dùng để tinh gọn
                
            except Exception as e:
                logger.warning(f"_compute_user_stats skipped due to: {e}")
                dashboard.total_borrowers = 0
                dashboard.high_risk_borrowers = 0
                dashboard.average_credit_score = 0
                # Không còn biểu đồ người dùng để reset

    @api.depends('date_from', 'date_to')
    def _compute_system_stats(self):
        """Thống kê hệ thống từ P2P Lending Core"""
        for dashboard in self:
            try:
                # Kiểm tra quyền truy cập
                if not self._check_model_access('p2p.wallet'):
                    raise Exception("No access to p2p.wallet model")
                
                # Thống kê ví điện tử từ P2P Wallet
                wallets = self.env['p2p.wallet'].search([])
                dashboard.total_wallets = len(wallets)
                dashboard.total_wallet_balance = sum(wallet.balance for wallet in wallets if wallet.balance)
                
                # Tỷ lệ đồng bộ thành công
                synced_wallets = wallets.filtered(lambda w: w.sync_status == 'synced')
                dashboard.sync_success_rate = (len(synced_wallets) / len(wallets) * 100) if wallets else 0
                
                # ĐÃ LOẠI BỎ: Các biểu đồ hệ thống
                
            except Exception as e:
                logger.warning(f"_compute_system_stats skipped due to: {e}")
                dashboard.total_wallets = 0
                dashboard.total_wallet_balance = 0
                dashboard.sync_success_rate = 0
                # Không còn biểu đồ hệ thống để reset

    # ĐÃ LOẠI BỎ: _compute_financial_analysis và các biểu đồ liên quan

    def _get_status_colors(self, statuses):
        """Trả về màu sắc cho các trạng thái"""
        color_map = {
            'draft': 'rgba(108, 117, 125, 0.6)',        # Gray
            'submitted': 'rgba(255, 193, 7, 0.6)',      # Yellow
            'under_review': 'rgba(255, 159, 64, 0.6)',  # Orange
            'approved': 'rgba(40, 167, 69, 0.6)',       # Green
            'rejected': 'rgba(220, 53, 69, 0.6)',       # Red
            'disbursed': 'rgba(23, 162, 184, 0.6)',     # Info
            'active': 'rgba(40, 167, 69, 0.6)',         # Green
            'completed': 'rgba(23, 162, 184, 0.6)',     # Info
            'defaulted': 'rgba(220, 53, 69, 0.6)',      # Red
            'pending': 'rgba(255, 193, 7, 0.6)',        # Yellow
            'processing': 'rgba(255, 159, 64, 0.6)',    # Orange
            'cancelled': 'rgba(108, 117, 125, 0.6)',    # Gray
        }
        
        return [color_map.get(status, 'rgba(108, 117, 125, 0.6)') for status in statuses]

    def _get_months_between(self, date_from, date_to):
        """Trả về danh sách các tháng giữa hai ngày"""
        months = []
        current_date = date_from.replace(day=1)
        
        while current_date <= date_to:
            # Ngày cuối tháng
            if current_date.month == 12:
                next_month = current_date.replace(year=current_date.year + 1, month=1)
            else:
                next_month = current_date.replace(month=current_date.month + 1)
            
            last_day = (next_month - timedelta(days=1)).day
            month_end = current_date.replace(day=last_day)
            
            # Định dạng tên tháng
            month_label = f"{current_date.month}/{current_date.year}"
            
            months.append((current_date, month_end, month_label))
            
            # Chuyển sang tháng tiếp theo
            current_date = next_month
        
        return months

    def _get_chart_colors(self, count):
        """Trả về danh sách màu cho biểu đồ"""
        colors = [
            'rgba(255, 99, 132, 0.6)',   # Đỏ
            'rgba(54, 162, 235, 0.6)',   # Xanh dương
            'rgba(255, 206, 86, 0.6)',   # Vàng
            'rgba(75, 192, 192, 0.6)',   # Xanh lá
            'rgba(153, 102, 255, 0.6)',  # Tím
            'rgba(255, 159, 64, 0.6)',   # Cam
            'rgba(199, 199, 199, 0.6)',  # Xám
            'rgba(83, 102, 255, 0.6)',   # Xanh tím
            'rgba(255, 99, 255, 0.6)',   # Hồng
            'rgba(34, 207, 207, 0.6)'    # Xanh ngọc
        ]
        
        border_colors = [
            'rgb(255, 99, 132)',   # Đỏ
            'rgb(54, 162, 235)',   # Xanh dương
            'rgb(255, 206, 86)',   # Vàng
            'rgb(75, 192, 192)',   # Xanh lá
            'rgb(153, 102, 255)',  # Tím
            'rgb(255, 159, 64)',   # Cam
            'rgb(199, 199, 199)',  # Xám
            'rgb(83, 102, 255)',   # Xanh tím
            'rgb(255, 99, 255)',   # Hồng
            'rgb(34, 207, 207)'    # Xanh ngọc
        ]
        
        # Lặp lại danh sách màu nếu cần nhiều hơn
        bg_colors = []
        border_color_list = []
        for i in range(count):
            bg_colors.append(colors[i % len(colors)])
            border_color_list.append(border_colors[i % len(border_colors)])
        
        return {
            'backgroundColor': bg_colors,
            'borderColor': border_color_list
        }

    def action_open_data_debug(self):
        """Mở Data Debug Checker"""
        self.ensure_one()
        
        # Tạo wizard debug
        wizard = self.env['p2p.data.debug.checker'].create({})
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Debug dữ liệu Dashboard',
            'res_model': 'p2p.data.debug.checker',
            'view_mode': 'form',
            'target': 'new',
            'res_id': wizard.id,
            'context': self.env.context,
        }

    def action_test_simple(self):
        """Test method đơn giản"""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Test method hoạt động!',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_auto_adjust_date_range(self):
        """Tự động điều chỉnh date range để bao gồm dữ liệu có sẵn"""
        self.ensure_one()
        
        try:
            # Tìm earliest và latest dates từ loan applications
            all_applications = self.env['loan.application'].search([])
            
            if all_applications:
                application_dates = [app.application_date for app in all_applications if app.application_date]
                if application_dates:
                    earliest_date = min(application_dates)
                    latest_date = max(application_dates)
                    self.write({
                        'date_from': earliest_date,
                        'date_to': latest_date
                    })
                    message = f"📅 Đã điều chỉnh date range từ {earliest_date} đến {latest_date} để bao gồm tất cả dữ liệu loan applications"
                    notification_type = "success"
                else:
                    message = "⚠️ Loan applications không có application_date"
                    notification_type = "warning"
            else:
                # Fallback: dùng p2p.loan nếu có
                if self._check_model_access('p2p.loan'):
                    loans = self.env['p2p.loan'].search([])
                    start_dates = [l.start_date for l in loans if getattr(l, 'start_date', False)]
                    create_dates = [l.create_date.date() for l in loans if getattr(l, 'create_date', False)]
                    all_dates = start_dates + create_dates
                    if all_dates:
                        earliest_date = min(all_dates)
                        latest_date = max(all_dates)
                        self.write({
                            'date_from': earliest_date,
                            'date_to': latest_date
                        })
                        message = f"📅 (Fallback) Đã điều chỉnh date range từ {earliest_date} đến {latest_date} theo dữ liệu p2p.loan"
                        notification_type = "success"
                    else:
                        message = "❌ Không tìm thấy ngày trong p2p.loan"
                        notification_type = "warning"
                else:
                    message = "❌ Không có loan applications nào trong hệ thống"
                    notification_type = "warning"
        
        except Exception as e:
            message = f"❌ Lỗi điều chỉnh date range: {str(e)}"
            notification_type = "danger"
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Auto Adjust Date Range',
                'message': message,
                'type': notification_type,
                'sticky': False,
            }
        }

    def action_check_permissions(self):
        """Kiểm tra quyền hạn để đọc data"""
        self.ensure_one()
        
        # Force recompute access status
        self._compute_access_status()
        
        if self.models_accessible:
            message = "✅ Tất cả quyền truy cập đều OK!\n\n" + self.access_status
            title = "Quyền hạn OK"
            notification_type = "success"
        else:
            message = "⚠️ Có vấn đề về quyền truy cập:\n\n" + self.access_status + "\n\n📋 Khuyến nghị:\n• Liên hệ Admin để cấp quyền\n• Kiểm tra module P2P Lending Core đã cài đặt chưa"
            title = "Vấn đề quyền hạn"
            notification_type = "warning"
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': notification_type,
                'sticky': True,
            }
        }

    def action_refresh_dashboard(self):
        """Làm mới dữ liệu bảng điều khiển"""
        self.ensure_one()
        # Force recompute all stats and charts fields
        self._compute_loan_application_stats()
        self._compute_disbursement_stats()
        self._compute_user_stats()
        self._compute_system_stats()
        # ĐÃ LOẠI BỎ: các compute biểu đồ không cần thiết
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thành công!',
                'message': '📊 Dashboard Core đã được cập nhật với dữ liệu mới nhất',
                'type': 'success',
                'sticky': False,
            }
        }
        
    def action_this_month(self):
        """Thiết lập khoảng thời gian là tháng hiện tại"""
        self.ensure_one()
        today = date.today()
        self.write({
            'date_from': today.replace(day=1),
            'date_to': today
        })
        return True
        
    def action_last_month(self):
        """Thiết lập khoảng thời gian là tháng trước"""
        self.ensure_one()
        today = date.today()
        
        # Tháng trước
        if today.month == 1:
            last_month_start = today.replace(year=today.year-1, month=12, day=1)
        else:
            last_month_start = today.replace(month=today.month-1, day=1)
            
        # Ngày cuối tháng trước
        if last_month_start.month == 12:
            last_month_end = last_month_start.replace(day=31)
        else:
            last_month_end = today.replace(day=1) - timedelta(days=1)
            
        self.write({
            'date_from': last_month_start,
            'date_to': last_month_end
        })
        return True
        
    def action_last_3_months(self):
        """Thiết lập khoảng thời gian là 3 tháng gần nhất"""
        self.ensure_one()
        today = date.today()
        three_months_ago = today - relativedelta(months=3)
        
        self.write({
            'date_from': three_months_ago,
            'date_to': today
        })
        return True
        
    def action_this_year(self):
        """Thiết lập khoảng thời gian là năm hiện tại"""
        self.ensure_one()
        today = date.today()
        
        self.write({
            'date_from': today.replace(month=1, day=1),
            'date_to': today
        })
        return True
        
    @api.model_create_multi
    def create(self, vals_list):
        """Ghi đè phương thức create để đảm bảo name luôn được tạo"""
        for vals in vals_list:
            if not vals.get('name'):
                today = fields.Date.today()
                vals['name'] = f"Bảng điều khiển P2P Core - {today.strftime('%d/%m/%Y')}"
        return super(P2PDashboard, self).create(vals_list)

    @api.model
    def get_default_dashboard(self):
        """Lấy hoặc tạo dashboard mặc định"""
        dashboard = self.search([], limit=1)
        if not dashboard:
            today = fields.Date.today()
            dashboard = self.create({
                'name': f"Dashboard P2P Core - {today.strftime('%d/%m/%Y')}",
                'date_from': today.replace(day=1),  # Đầu tháng
                'date_to': today
            })
        return dashboard

    @api.model
    def ensure_default_dashboard_exists(self):
        """Đảm bảo luôn có ít nhất 1 dashboard"""
        if not self.search_count([]):
            return self.get_default_dashboard()
        return True

    def action_clear_demo_data(self):
        """Xóa tất cả dữ liệu demo dashboard"""
        demo_dashboards = self.env['p2p.dashboard'].search([('name', 'ilike', 'mẫu')])
        count = len(demo_dashboards)
        demo_dashboards.unlink()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'Đã xóa {count} dashboard demo',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_reset_to_current_month(self):
        """Reset dashboard về tháng hiện tại"""
        self.ensure_one()
        today = fields.Date.today()
        self.write({
            'date_from': today.replace(day=1),
            'date_to': today
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Đã reset dashboard về tháng hiện tại',
                'type': 'success',
                'sticky': False,
            }
        }