# -*- coding: utf-8 -*-
from odoo import api, fields, models


class LendingLoanExtension(models.Model):
    _inherit = "p2p.loan"

    # Tích hợp với Lending Club Analysis
    lc_loan_ids = fields.One2many('lc.loan', 'p2p_loan_id', string="Lịch sử khoản vay Lending Club",
                                  help="Các bản ghi Lending Club liên quan đến khoản vay này")

    @api.depends('lc_loan_ids')
    def _compute_lc_loan_count(self):
        """Tính số lượng LC Loan liên quan"""
        for loan in self:
            loan.lc_loan_count = len(loan.lc_loan_ids)

    # Override field để thêm compute
    lc_loan_count = fields.Integer(string="Số lượng LC Loan", compute="_compute_lc_loan_count")

    def action_view_lc_loans(self):
        """Xem các LC Loan liên quan"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lịch sử khoản vay Lending Club',
            'res_model': 'lc.loan',
            'view_mode': 'list,form',
            'domain': [('p2p_loan_id', '=', self.id)],
            'context': {'default_p2p_loan_id': self.id},
            'target': 'current',
        }
