# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api

logger = logging.getLogger(__name__)

class PermissionChecker(models.TransientModel):
    _name = 'p2p.permission.checker'
    _description = 'Kiểm tra quyền hạn P2P Dashboard'
    
    result = fields.Html('Kết quả kiểm tra', readonly=True)
    
    def check_all_permissions(self):
        """Kiểm tra tất cả quyền hạn cần thiết"""
        results = []
        
        # 1. Kiểm tra module P2P Lending Core đã cài đặt chưa
        try:
            module = self.env['ir.module.module'].search([('name', '=', 'p2p_lending_core')])
            if module and module.state == 'installed':
                results.append("✅ Module P2P Lending Core: ĐÃ CÀI ĐẶT")
            else:
                results.append("❌ Module P2P Lending Core: CHƯA CÀI ĐẶT")
                return self._show_results("\n".join(results))
        except Exception as e:
            results.append(f"❌ Lỗi kiểm tra module: {e}")
            return self._show_results("\n".join(results))
        
        # 2. Kiểm tra các model cần thiết
        models_to_check = [
            ('loan.application', 'Hồ sơ vay'),
            ('loan.disbursement', 'Giải ngân'),
            ('loan.type', 'Loại vay'),
            ('p2p.wallet', 'Ví P2P'),
            ('p2p.borrower', 'Người vay'),
            ('p2p.investor', 'Nhà đầu tư')
        ]
        
        for model_name, model_desc in models_to_check:
            try:
                model = self.env[model_name]
                model.check_access_rights('read')
                # Thử search 1 record để kiểm tra quyền thực tế
                count = model.search_count([])
                results.append(f"✅ {model_desc} ({model_name}): CÓ QUYỀN - {count} bản ghi")
            except Exception as e:
                results.append(f"❌ {model_desc} ({model_name}): KHÔNG CÓ QUYỀN - {e}")
        
        # 3. Kiểm tra các field quan trọng
        field_checks = [
            ('loan.application', ['application_date', 'amount', 'status', 'interest_rate', 'term_months']),
            ('loan.disbursement', ['disbursement_date', 'amount', 'status', 'disbursement_method']),
            ('p2p.wallet', ['balance', 'sync_status']),
        ]
        
        for model_name, field_list in field_checks:
            try:
                model = self.env[model_name]
                missing_fields = []
                for field_name in field_list:
                    if field_name not in model._fields:
                        missing_fields.append(field_name)
                
                if missing_fields:
                    results.append(f"⚠️ {model_name}: Thiếu fields {missing_fields}")
                else:
                    results.append(f"✅ {model_name}: Tất cả fields cần thiết đều có")
            except Exception as e:
                results.append(f"❌ Lỗi kiểm tra fields {model_name}: {e}")
        
        # 4. Thử tạo dashboard record để test
        try:
            dashboard = self.env['p2p.dashboard'].create({
                'name': 'Test Dashboard',
                'date_from': fields.Date.today(),
                'date_to': fields.Date.today(),
            })
            dashboard._compute_access_status()
            if dashboard.models_accessible:
                results.append("✅ Tạo dashboard thành công: TẤT CẢ QUYỀN OK")
            else:
                results.append("⚠️ Dashboard tạo được nhưng có vấn đề quyền hạn")
            dashboard.unlink()  # Xóa test record
        except Exception as e:
            results.append(f"❌ Lỗi tạo dashboard: {e}")
            
        return self._show_results("\n".join(results))
    
    def _show_results(self, results_text):
        """Hiển thị kết quả"""
        html_result = f"""
        <div style="font-family: monospace; background: #f8f9fa; padding: 15px; border-radius: 5px;">
            <h3>🔍 KẾT QUẢ KIỂM TRA QUYỀN HẠN</h3>
            <pre style="white-space: pre-wrap; font-size: 14px;">
{results_text}
            </pre>
            <hr/>
            <h4>📋 KHUYẾN NGHỊ:</h4>
            <ul>
                <li>Nếu có ❌: Liên hệ Admin để cấp quyền hoặc cài đặt module</li>
                <li>Nếu thiếu fields: Cập nhật module P2P Lending Core</li>
                <li>Nếu tất cả ✅: Dashboard đã sẵn sàng sử dụng!</li>
            </ul>
        </div>
        """
        
        self.result = html_result
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Kết quả kiểm tra quyền hạn',
            'res_model': 'p2p.permission.checker',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }