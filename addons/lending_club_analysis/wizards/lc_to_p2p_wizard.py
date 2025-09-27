# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class LcToP2pWizard(models.TransientModel):
    _name = "lc.to.p2p.wizard"
    _description = "Chuyển đổi LC Loan sang P2P Loan"

    lc_loan_ids = fields.Many2many('lc.loan', string="Khoản vay Lending Club", 
                                   help="Chọn các khoản vay LC để chuyển đổi sang P2P")
    filter_criteria = fields.Selection([
        ('all', 'Tất cả'),
        ('no_p2p', 'Chưa có P2P Loan'),
        ('grade_filter', 'Theo hạng tín dụng'),
        ('amount_filter', 'Theo số tiền'),
    ], string="Tiêu chí lọc", default='no_p2p')
    
    grade_filter = fields.Selection([
        ('A', 'Chỉ hạng A'),
        ('AB', 'Hạng A và B'),
        ('ABC', 'Hạng A, B, C'),
    ], string="Lọc theo hạng")
    
    min_amount = fields.Float(string="Số tiền tối thiểu")
    max_amount = fields.Float(string="Số tiền tối đa")
    
    create_mode = fields.Selection([
        ('draft', 'Tạo ở trạng thái Nháp'),
        ('active', 'Tạo ở trạng thái Hoạt động'),
        ('auto', 'Tự động theo trạng thái LC'),
    ], string="Chế độ tạo", default='auto')
    
    @api.onchange('filter_criteria')
    def _onchange_filter_criteria(self):
        """Cập nhật domain cho lc_loan_ids dựa trên tiêu chí lọc"""
        domain = []
        
        if self.filter_criteria == 'no_p2p':
            domain = [('p2p_loan_id', '=', False)]
        elif self.filter_criteria == 'grade_filter':
            if self.grade_filter == 'A':
                domain = [('grade', '=', 'A')]
            elif self.grade_filter == 'AB':
                domain = [('grade', 'in', ['A', 'B'])]
            elif self.grade_filter == 'ABC':
                domain = [('grade', 'in', ['A', 'B', 'C'])]
        elif self.filter_criteria == 'amount_filter':
            if self.min_amount:
                domain.append(('loan_amnt', '>=', self.min_amount))
            if self.max_amount:
                domain.append(('loan_amnt', '<=', self.max_amount))
        
        return {'domain': {'lc_loan_ids': domain}}
    
    def action_convert_to_p2p(self):
        """Chuyển đổi các LC Loan đã chọn sang P2P Loan"""
        if not self.lc_loan_ids:
            raise UserError(_("Vui lòng chọn ít nhất một khoản vay Lending Club để chuyển đổi."))

        created_loans = self.env['p2p.loan']
        errors = []

        for lc_loan in self.lc_loan_ids:
            try:
                if lc_loan.p2p_loan_id:
                    continue  # Bỏ qua nếu đã có P2P loan

                # Chuẩn bị dữ liệu
                p2p_vals = lc_loan._prepare_p2p_loan_data()

                # Điều chỉnh trạng thái theo create_mode
                if self.create_mode == 'draft':
                    p2p_vals['state'] = 'draft'
                elif self.create_mode == 'active':
                    p2p_vals['state'] = 'active'
                # create_mode == 'auto' thì giữ nguyên logic trong _prepare_p2p_loan_data

                # Tạo P2P loan
                p2p_loan = self.env['p2p.loan'].create(p2p_vals)

                # Liên kết
                lc_loan.p2p_loan_id = p2p_loan.id

                created_loans |= p2p_loan

            except Exception as e:
                errors.append(f"LC Loan {lc_loan.loan_id}: {str(e)}")
        
        # Hiển thị kết quả
        message = f"Đã tạo thành công {len(created_loans)} khoản vay P2P."
        if errors:
            message += f"\n\nLỗi ({len(errors)}):\n" + "\n".join(errors)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Kết quả chuyển đổi'),
                'message': message,
                'type': 'success' if not errors else 'warning',
                'sticky': True,
            }
        }
    
    def action_preview_selection(self):
        """Xem trước các khoản vay sẽ được chuyển đổi"""
        domain = []
        
        if self.filter_criteria == 'no_p2p':
            domain = [('p2p_loan_id', '=', False)]
        elif self.filter_criteria == 'grade_filter':
            if self.grade_filter == 'A':
                domain = [('grade', '=', 'A')]
            elif self.grade_filter == 'AB':
                domain = [('grade', 'in', ['A', 'B'])]
            elif self.grade_filter == 'ABC':
                domain = [('grade', 'in', ['A', 'B', 'C'])]
        elif self.filter_criteria == 'amount_filter':
            if self.min_amount:
                domain.append(('loan_amnt', '>=', self.min_amount))
            if self.max_amount:
                domain.append(('loan_amnt', '<=', self.max_amount))
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Xem trước khoản vay sẽ chuyển đổi',
            'res_model': 'lc.loan',
            'view_mode': 'list',
            'domain': domain,
            'target': 'new',
        }
