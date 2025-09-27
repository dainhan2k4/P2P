# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging
from datetime import date, timedelta
import json

logger = logging.getLogger(__name__)

class DataDebugChecker(models.TransientModel):
    _name = 'p2p.data.debug.checker'
    _description = 'P2P Data Debug Checker'

    result = fields.Html('Kết quả debug', readonly=True, default="Nhấn 'Debug ngay' để kiểm tra dữ liệu.")

    def debug_data_availability(self):
        """Debug dữ liệu có sẵn trong hệ thống (đơn giản, không tạo dữ liệu mới)"""
        self.ensure_one()
        results = []
        p = "<div style='font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, \"Liberation Mono\", \"Courier New\", monospace; padding: 12px; background: #fafafa; border: 1px solid #eee; border-radius: 6px;'>"
        results.append(p)
        results.append("<h3 style='color: #333; margin: 0 0 12px;'>P2P Dashboard Data Debug</h3>")

        # 1) Database snapshot
        results.append("<h4 style='color: #444; margin: 12px 0;'>Kiểm tra dữ liệu trong database</h4>")
        models_to_check = [
            ('loan.application', 'Hồ sơ vay (core)'),
            ('loan.disbursement', 'Giải ngân (core)'),
            ('p2p.loan', 'Khoản vay (bridge)'),
            ('p2p.investment', 'Đầu tư (bridge)'),
            ('loan.type', 'Loại vay'),
            ('p2p.wallet', 'Ví P2P'),
            ('p2p.borrower', 'Người vay'),
            ('p2p.investor', 'Nhà đầu tư'),
        ]
        total_records = 0
        for model_name, display_name in models_to_check:
            try:
                model = self.env[model_name]
                count = model.search_count([])
                total_records += count
                results.append(f"<div>{display_name}: <strong>{count}</strong></div>")
                if count:
                    sample = model.search([], limit=1)
                    if sample:
                        results.append(f"<div style='color: #666; padding-left: 8px;'>Sample: ID={sample.id}, Name={getattr(sample, 'name', 'N/A')}</div>")
            except Exception as e:
                results.append(f"<div style='color:#a33;'>Lỗi truy cập {display_name}: {str(e)}</div>")
        results.append(f"<div style='margin-top: 8px;'><strong>Tổng cộng: {total_records} bản ghi</strong></div>")

        # 2) Date range
        results.append("<h4 style='color: #444; margin: 12px 0;'>Kiểm tra khoảng ngày (Date Range)</h4>")
        try:
            dashboard = self.env['p2p.dashboard'].search([], limit=1)
            if not dashboard:
                results.append("<div style='color:#a33;'>Chưa có bản ghi Dashboard. Vào menu Dashboard để tạo một bản ghi trước.</div>")
            else:
                results.append(f"<div>From: <strong>{dashboard.date_from}</strong></div>")
                results.append(f"<div>To: <strong>{dashboard.date_to}</strong></div>")
                try:
                    loan_apps_in_range = self.env['loan.application'].search([
                        ('application_date', '>=', dashboard.date_from),
                        ('application_date', '<=', dashboard.date_to),
                    ])
                    results.append(f"<div>Loan applications trong range: <strong>{len(loan_apps_in_range)}</strong></div>")
                    if not loan_apps_in_range:
                        all_loans = self.env['loan.application'].search([])
                        if all_loans:
                            earliest_date = min(app.application_date for app in all_loans if app.application_date)
                            latest_date = max(app.application_date for app in all_loans if app.application_date)
                            results.append(f"<div>Dải ngày loan.application: {earliest_date} → {latest_date}</div>")
                            results.append("<div>Gợi ý: điều chỉnh date range để bao gồm dải ngày trên.</div>")
                        else:
                            all_bridge_loans = self.env['p2p.loan'].search([])
                            start_dates = [l.start_date for l in all_bridge_loans if getattr(l, 'start_date', False)]
                            create_dates = [l.create_date.date() for l in all_bridge_loans if getattr(l, 'create_date', False)]
                            all_dates = start_dates + create_dates
                            if all_dates:
                                earliest = min(all_dates)
                                latest = max(all_dates)
                                results.append(f"<div>Dải ngày p2p.loan: {earliest} → {latest}</div>")
                                results.append("<div>Dashboard hỗ trợ dùng p2p.loan khi core trống.</div>")
                            else:
                                results.append("<div>Không tìm thấy ngày trên p2p.loan</div>")
                except Exception as e:
                    results.append(f"<div style='color:#a33;'>Lỗi kiểm tra date range: {str(e)}</div>")
        except Exception as e:
            results.append(f"<div style='color:#a33;'>Lỗi kiểm tra dashboard: {str(e)}</div>")

        # 3) Compute methods
        results.append("<h4 style='color: #444; margin: 12px 0;'>Kiểm tra tính toán (compute)</h4>")
        try:
            dashboard = self.env['p2p.dashboard'].search([], limit=1)
            if dashboard:
                for method_name in [
                    '_compute_loan_application_stats',
                    '_compute_disbursement_stats',
                    '_compute_user_stats',
                    '_compute_system_stats',
                ]:
                    try:
                        getattr(dashboard, method_name)()
                        results.append(f"<div>{method_name}: thành công</div>")
                    except Exception as e:
                        results.append(f"<div style='color:#a33;'>{method_name}: lỗi - {str(e)}</div>")
                results.append("<div style='margin-top:6px;'><strong>Giá trị sau khi compute</strong></div>")
                results.append(f"<div>Total Loan Applications: {dashboard.total_loan_applications}</div>")
                results.append(f"<div>Total Disbursements: {dashboard.total_disbursements}</div>")
                results.append(f"<div>Total Borrowers: {dashboard.total_borrowers}</div>")
                results.append(f"<div>Total Wallets: {dashboard.total_wallets}</div>")
                results.append(f"<div>Loan Data Source: {dashboard.loan_data_source or ''}</div>")
                results.append(f"<div>Disbursement Data Source: {dashboard.disb_data_source or ''}</div>")
                results.append(f"<div>Loans By Type Label: {dashboard.loans_by_type_label or ''}</div>")
                results.append(f"<div>Loans By Purpose Label: {dashboard.loans_by_purpose_label or ''}</div>")
        except Exception as e:
            results.append(f"<div style='color:#a33;'>Lỗi test compute methods: {str(e)}</div>")

        # 4) Chart data
        results.append("<h4 style='color: #444; margin: 12px 0;'>Kiểm tra dữ liệu biểu đồ</h4>")
        try:
            dashboard = self.env['p2p.dashboard'].search([], limit=1)
            if dashboard:
                for chart_field in [
                    'chart_application_status',
                    'chart_loan_amount_by_status',
                    'chart_disbursement_status',
                    'chart_loans_by_type',
                    'chart_loans_by_purpose',
                    'chart_loans_by_credit_tier',
                ]:
                    chart_data = getattr(dashboard, chart_field, None)
                    if chart_data:
                        try:
                            parsed = json.loads(chart_data)
                            has_data = bool(parsed.get('labels') and parsed.get('datasets'))
                            results.append(f"<div>{chart_field}: {'có dữ liệu' if has_data else 'rỗng'}</div>")
                        except Exception:
                            results.append(f"<div style='color:#a33;'>{chart_field}: JSON không hợp lệ</div>")
                    else:
                        results.append(f"<div>{chart_field}: null</div>")
        except Exception as e:
            results.append(f"<div style='color:#a33;'>Lỗi kiểm tra chart data: {str(e)}</div>")

        # 5) Recommendations
        results.append("<h4 style='color: #444; margin: 12px 0;'>Khuyến nghị</h4>")
        if total_records == 0:
            results.append("<div style='background: #fff; border: 1px solid #eee; color: #333; padding: 12px; border-radius: 4px; margin: 8px 0;'>")
            results.append("<strong>Không có dữ liệu trong hệ thống.</strong><br/>")
            results.append("Vui lòng import dữ liệu thực hoặc kiểm tra lại quy trình đồng bộ:")
            results.append("<ul>")
            results.append("<li>Loan Types trong P2P Lending Core → Configuration</li>")
            results.append("<li>Borrowers và Investors</li>")
            results.append("<li>Loan Applications</li>")
            results.append("<li>Disbursements</li>")
            results.append("<li>Hoặc chạy migration từ hệ thống cũ</li>")
            results.append("</ul>")
            results.append("</div>")
        else:
            results.append("<div style='background: #fff; border: 1px solid #eee; color: #333; padding: 12px; border-radius: 4px; margin: 8px 0;'>")
            results.append("<strong>Hệ thống có dữ liệu.</strong><br/>")
            results.append("Nếu dashboard vẫn trống, tham khảo:")
            results.append("<ul>")
            results.append("<li>Điều chỉnh Date Range để bao gồm dữ liệu</li>")
            results.append("<li>Click Cập nhật dữ liệu để refresh</li>")
            results.append("<li>Kiểm tra computed fields có lỗi không</li>")
            results.append("<li>Clear browser cache và reload trang</li>")
            results.append("</ul>")
            results.append("</div>")

        results.append("</div>")
        self.result = ''.join(results)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'p2p.data.debug.checker',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }
