# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import json
import logging

_logger = logging.getLogger(__name__)

SCORE_RANGES = [
    ('excellent', 'Excellent (800-850)'),
    ('very_good', 'Very Good (740-799)'),
    ('good', 'Good (670-739)'),
    ('fair', 'Fair (580-669)'),
    ('poor', 'Poor (300-579)'),
]

class CreditScore(models.Model):
    _name = 'credit.score'
    _description = 'Credit Score'
    _order = 'create_date desc'
    
    name = fields.Char('Reference', readonly=True, copy=False, default=lambda self: _('New'))
    score = fields.Integer('Credit Score', help="Credit score from 300-850")
    score_range = fields.Selection(SCORE_RANGES, string='Score Range', compute='_compute_score_range', store=True)
    pd_value = fields.Float('Probability of Default', digits=(16, 6), help="Probability of Default (0-1)")
    ead_value = fields.Float('Exposure at Default', digits=(16, 2), help="Exposure at Default (currency)")
    lgd_value = fields.Float('Loss Given Default', digits=(16, 6), help="Loss Given Default (0-1)")
    expected_loss = fields.Float('Expected Loss', digits=(16, 2), compute='_compute_expected_loss', store=True,
                                help="Expected Loss = PD * EAD * LGD")
    
    # Relationships
    model_id = fields.Many2one('credit.model', string='Scoring Model', ondelete='restrict')
    borrower_id = fields.Many2one('p2p.borrower', string='Borrower', ondelete='cascade')
    loan_id = fields.Many2one('p2p.loan', string='Loan Application', ondelete='set null')
    
    # Input features used for scoring
    input_features = fields.Text('Input Features', help="JSON representation of features used for scoring")
    
    # Decision and recommendations
    recommendation = fields.Selection([
        ('approve', 'Approve'),
        ('review', 'Manual Review'),
        ('reject', 'Reject'),
    ], string='Recommendation', compute='_compute_recommendation', store=True)
    
    notes = fields.Text('Notes')
    create_date = fields.Datetime('Created On', readonly=True)
    create_uid = fields.Many2one('res.users', string='Created By', readonly=True)
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('credit.score') or _('New')
        return super(CreditScore, self).create(vals)
    
    @api.depends('score')
    def _compute_score_range(self):
        for record in self:
            if not record.score:
                record.score_range = False
            elif record.score >= 800:
                record.score_range = 'excellent'
            elif record.score >= 740:
                record.score_range = 'very_good'
            elif record.score >= 670:
                record.score_range = 'good'
            elif record.score >= 580:
                record.score_range = 'fair'
            else:
                record.score_range = 'poor'
    
    @api.depends('pd_value', 'ead_value', 'lgd_value')
    def _compute_expected_loss(self):
        for record in self:
            if all(v is not None for v in [record.pd_value, record.ead_value, record.lgd_value]):
                record.expected_loss = record.pd_value * record.ead_value * record.lgd_value
            else:
                record.expected_loss = 0.0
    
    @api.depends('score', 'pd_value')
    def _compute_recommendation(self):
        for record in self:
            # Get applicable credit policy
            policies = self.env['credit.policy'].search([
                ('model_id', '=', record.model_id.id),
                ('active', '=', True),
            ], order='min_score desc')
            
            recommendation = 'review'  # Default to manual review
            
            for policy in policies:
                if record.score and record.score >= policy.min_score:
                    if record.pd_value and record.pd_value <= policy.max_pd:
                        recommendation = policy.decision
                        break
            
            record.recommendation = recommendation
    
    def get_input_features_dict(self):
        """Convert the JSON input_features to a Python dictionary"""
        self.ensure_one()
        if not self.input_features:
            return {}
        try:
            return json.loads(self.input_features)
        except Exception as e:
            _logger.error(f"Error parsing input features: {e}")
            return {}