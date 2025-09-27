# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

DECISION_TYPES = [
    ('approve', 'Approve'),
    ('review', 'Manual Review'),
    ('reject', 'Reject'),
]

class CreditPolicy(models.Model):
    _name = 'credit.policy'
    _description = 'Credit Policy'
    _order = 'min_score desc'
    
    name = fields.Char('Policy Name', required=True)
    model_id = fields.Many2one('credit.model', string='Scoring Model', required=True, ondelete='cascade')
    min_score = fields.Integer('Minimum Score', required=True, help="Minimum credit score for this policy")
    max_pd = fields.Float('Maximum PD', digits=(16, 6), required=True, help="Maximum probability of default")
    decision = fields.Selection(DECISION_TYPES, string='Decision', required=True, default='review')
    interest_rate_adjustment = fields.Float('Interest Rate Adjustment (%)', digits=(5, 2), default=0.0,
                                         help="Adjustment to base interest rate in percentage points")
    max_loan_amount = fields.Float('Maximum Loan Amount', digits=(16, 2))
    max_loan_term = fields.Integer('Maximum Loan Term (months)')
    active = fields.Boolean('Active', default=True)
    notes = fields.Text('Notes')
    
    _sql_constraints = [
        ('min_score_uniq', 'unique(model_id, min_score)', 'Minimum score must be unique per model!')
    ]
    
    @api.constrains('min_score', 'max_pd')
    def _check_values(self):
        for record in self:
            if record.min_score < 300 or record.min_score > 850:
                raise models.ValidationError(_('Credit score must be between 300 and 850.'))
            if record.max_pd < 0 or record.max_pd > 1:
                raise models.ValidationError(_('Probability of default must be between 0 and 1.'))