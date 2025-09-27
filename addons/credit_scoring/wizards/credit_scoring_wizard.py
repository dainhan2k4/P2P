# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import pandas as pd
import numpy as np
import json
import logging

_logger = logging.getLogger(__name__)

class CreditScoringWizard(models.TransientModel):
    _name = 'credit.scoring.wizard'
    _description = 'Credit Scoring Wizard'
    
    borrower_id = fields.Many2one('p2p.borrower', string='Borrower', required=True)
    loan_id = fields.Many2one('p2p.loan', string='Loan Application')
    pd_model_id = fields.Many2one('credit.model', string='PD Model', domain=[('model_type', '=', 'pd')], required=True)
    ead_model_id = fields.Many2one('credit.model', string='EAD Model', domain=[('model_type', '=', 'ead')])
    lgd_model_id = fields.Many2one('credit.model', string='LGD Model', domain=[('model_type', '=', 'lgd')])
    
    # Loan information
    loan_amount = fields.Float('Loan Amount', related='loan_id.amount', readonly=True)
    loan_term = fields.Integer('Loan Term (months)', related='loan_id.term', readonly=True)
    loan_purpose = fields.Selection([
        ('debt_consolidation', 'Trả nợ'),
        ('home_improvement', 'Cải tạo nhà'),
        ('business', 'Kinh doanh'),
        ('education', 'Giáo dục'),
        ('medical', 'Y tế'),
        ('other', 'Khác')
    ], string='Loan Purpose', related='loan_id.purpose', readonly=True)
    
    # Borrower information
    monthly_income = fields.Float('Monthly Income', related='borrower_id.monthly_income', readonly=True)
    employment_length = fields.Selection([
        ('employed', 'Đang làm việc'),
        ('self_employed', 'Tự kinh doanh'),
        ('student', 'Sinh viên'),
        ('unemployed', 'Đang thất nghiệp')
    ], string='Employment Status', related='borrower_id.employment_status', readonly=True)
    dti_ratio = fields.Float('DTI Ratio', compute='_compute_dti_ratio', readonly=True)
    
    # Results
    score = fields.Integer('Credit Score', readonly=True)
    pd_value = fields.Float('Probability of Default', digits=(16, 6), readonly=True)
    ead_value = fields.Float('Exposure at Default', digits=(16, 2), readonly=True)
    lgd_value = fields.Float('Loss Given Default', digits=(16, 6), readonly=True)
    expected_loss = fields.Float('Expected Loss', digits=(16, 2), readonly=True)
    recommendation = fields.Selection([
        ('approve', 'Approve'),
        ('review', 'Manual Review'),
        ('reject', 'Reject'),
    ], string='Recommendation', readonly=True)
    
    state = fields.Selection([
        ('input', 'Input'),
        ('result', 'Result'),
    ], default='input', string='State')
    
    @api.onchange('borrower_id')
    def _onchange_borrower_id(self):
        if self.borrower_id:
            loans = self.env['p2p.loan'].search([
                ('borrower_id', '=', self.borrower_id.id),
                ('state', '=', 'draft'),
            ], limit=1)
            if loans:
                self.loan_id = loans[0].id
    
    def action_calculate_score(self):
        self.ensure_one()
        
        if not self.pd_model_id:
            raise UserError(_('PD Model is required for credit scoring.'))
        
        # Prepare features for PD model
        pd_features = self._prepare_pd_features()
        
        # Calculate PD
        pd_model = self.pd_model_id.load_model(self.pd_model_id.id)
        if not pd_model:
            raise UserError(_('Failed to load PD model.'))
        
        try:
            # Get PD prediction
            pd_value = self.pd_model_id.predict(pd_features)[0]
            
            # Calculate credit score based on PD
            # Using a simple transformation: score = 850 - 550 * pd_value
            # This maps PD=0 to score=850 and PD=1 to score=300
            score = int(850 - 550 * pd_value)
            score = max(300, min(850, score))  # Ensure score is between 300-850
            
            self.pd_value = pd_value
            self.score = score
            
            # Calculate EAD if model is provided
            if self.ead_model_id:
                ead_features = self._prepare_ead_features()
                ead_factor = self.ead_model_id.predict(ead_features)[0]
                self.ead_value = self.loan_amount * ead_factor
            else:
                self.ead_value = self.loan_amount  # Default to full loan amount
            
            # Calculate LGD if model is provided
            if self.lgd_model_id:
                lgd_features = self._prepare_lgd_features()
                self.lgd_value = self.lgd_model_id.predict(lgd_features)[0]
            else:
                self.lgd_value = 0.5  # Default to 50% loss
            
            # Calculate expected loss
            self.expected_loss = self.pd_value * self.ead_value * self.lgd_value
            
            # Determine recommendation based on credit policies
            self._compute_recommendation()
            
            # Create credit score record
            self._create_credit_score()
            
            self.state = 'result'
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'credit.scoring.wizard',
                'view_mode': 'form',
                'res_id': self.id,
                'target': 'new',
                'context': {'form_view_initial_mode': 'edit'},
            }
            
        except Exception as e:
            _logger.error(f"Error in credit scoring: {e}")
            raise UserError(_(f"Error in credit scoring calculation: {e}"))
    
    def _prepare_pd_features(self):
        """Prepare features for PD model"""
        features = {
            'loan_amount': self.loan_amount,
            'term': self.loan_term,
            'monthly_income': self.monthly_income,
            'employment_status': self.employment_length,
        }
        
        # Convert to DataFrame
        df = pd.DataFrame([features])
        return df
        
    def _prepare_ead_features(self):
        """Prepare features for EAD model"""
        features = {
            'loan_amount': self.loan_amount,
            'term': self.loan_term,
            'monthly_income': self.monthly_income,
        }
        
        # Convert to DataFrame
        df = pd.DataFrame([features])
        return df
        
    def _prepare_lgd_features(self):
        """Prepare features for LGD model"""
        features = {
            'loan_amount': self.loan_amount,
            'term': self.loan_term,
            'monthly_income': self.monthly_income,
        }
        
        # Convert to DataFrame
        df = pd.DataFrame([features])
        return df
        
    @api.depends('monthly_income', 'loan_amount', 'loan_term')
    def _compute_dti_ratio(self):
        for record in self:
            if record.monthly_income and record.loan_amount and record.loan_term:
                monthly_payment = (record.loan_amount * 0.1) / (1 - (1 + 0.1) ** -record.loan_term)  # Example calculation
                record.dti_ratio = (monthly_payment / record.monthly_income) * 100 if record.monthly_income else 0
            else:
                record.dti_ratio = 0
    
    def _compute_recommendation(self):
        """Determine recommendation based on credit policies"""
        policies = self.env['credit.policy'].search([
            ('model_id', '=', self.pd_model_id.id),
            ('active', '=', True),
        ], order='min_score desc')
        
        recommendation = 'review'  # Default to manual review
        
        for policy in policies:
            if self.score >= policy.min_score and self.pd_value <= policy.max_pd:
                recommendation = policy.decision
                break
        
        self.recommendation = recommendation
    
    def _create_credit_score(self):
        """Create a credit score record"""
        # Prepare input features as JSON
        input_features = {
            'loan_amount': self.loan_amount,
            'term': self.loan_term,
            'monthly_income': self.monthly_income,
            'employment_status': self.employment_length,
            'loan_purpose': self.loan_purpose,
        }
        
        # Create credit score record
        self.env['credit.score'].create({
            'model_id': self.pd_model_id.id,
            'borrower_id': self.borrower_id.id,
            'loan_id': self.loan_id.id if self.loan_id else False,
            'score': self.score,
            'pd_value': self.pd_value,
            'ead_value': self.ead_value,
            'lgd_value': self.lgd_value,
            'input_features': json.dumps(input_features),
        })
    
    def action_apply_to_loan(self):
        """Apply credit scoring results to loan"""
        self.ensure_one()
        
        if not self.loan_id:
            raise UserError(_('No loan application selected.'))
        
        if self.recommendation == 'approve':
            self.loan_id.write({
                'state': 'approved',
                'notes': f"{self.loan_id.notes or ''}\nCredit score: {self.score}, Recommendation: Approved",
            })
        elif self.recommendation == 'reject':
            self.loan_id.write({
                'state': 'rejected',
                'notes': f"{self.loan_id.notes or ''}\nCredit score: {self.score}, Recommendation: Rejected",
            })
        
        return {'type': 'ir.actions.act_window_close'}