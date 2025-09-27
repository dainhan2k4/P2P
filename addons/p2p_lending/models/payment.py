from odoo import models, fields, api
from datetime import datetime, timedelta

class LoanPayment(models.Model):
    _name = 'p2p.loan.payment'
    _description = 'Loan Payment Schedule'
    _order = 'payment_date'
    
    loan_id = fields.Many2one('p2p.loan', string='Khoản vay', ondelete='cascade', required=True, index=True)
    payment_date = fields.Date(string='Ngày thanh toán', required=True)
    amount = fields.Float(string='Số tiền', required=True)
    principal = fields.Float(string='Gốc', required=True)
    interest = fields.Float(string='Lãi', required=True)
    balance = fields.Float(string='Dư nợ còn lại')
    state = fields.Selection([
        ('unpaid', 'Chưa thanh toán'),
        ('paid', 'Đã thanh toán'),
        ('late', 'Quá hạn'),
    ], string='Trạng thái', default='unpaid', tracking=True)
    payment_date_actual = fields.Date(string='Ngày thanh toán thực tế')


class InvestmentPayment(models.Model):
    _name = 'p2p.investment.payment'
    _description = 'Investment Payment Schedule'
    _order = 'payment_date'
    
    investment_id = fields.Many2one('p2p.investment', string='Đầu tư', ondelete='cascade', required=True, index=True)
    loan_id = fields.Many2one('p2p.loan', string='Khoản vay', related='investment_id.loan_id', store=True, index=True)
    payment_date = fields.Date(string='Ngày thanh toán', required=True)
    amount = fields.Float(string='Số tiền', required=True)
    principal = fields.Float(string='Gốc', required=True)
    interest = fields.Float(string='Lãi', required=True)
    state = fields.Selection([
        ('unpaid', 'Chưa thanh toán'),
        ('paid', 'Đã thanh toán'),
        ('late', 'Quá hạn'),
    ], string='Trạng thái', default='unpaid', tracking=True)
    payment_date_actual = fields.Date(string='Ngày thanh toán thực tế')
