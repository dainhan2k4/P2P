# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import numpy as np
import pandas as pd
import pickle
import base64
import logging

_logger = logging.getLogger(__name__)

MODEL_TYPES = [
    ('pd', 'Probability of Default (PD)'),
    ('ead', 'Exposure at Default (EAD)'),
    ('lgd', 'Loss Given Default (LGD)'),
]

class CreditModel(models.Model):
    _name = 'credit.model'
    _description = 'Credit Scoring Model'
    _order = 'name'
    _inherit = ['mail.thread']
    
    name = fields.Char('Model Name', required=True, tracking=True)
    model_type = fields.Selection(MODEL_TYPES, string='Model Type', required=True, tracking=True)
    description = fields.Text('Description')
    model_file = fields.Binary('Model File', attachment=True, help="Upload the pickled model file")
    model_filename = fields.Char('Model Filename')
    feature_importance = fields.Text('Feature Importance', help="JSON representation of feature importance")
    active = fields.Boolean('Active', default=True, tracking=True)
    version = fields.Char('Version', default='1.0', tracking=True)
    creation_date = fields.Date('Creation Date', default=fields.Date.today, tracking=True)
    write_date = fields.Datetime('Last Updated', readonly=True, tracking=True)
    
    # Fields for model statistics
    accuracy = fields.Float('Accuracy', help="Model accuracy metric")
    auc = fields.Float('AUC', help="Area Under the ROC Curve")
    gini = fields.Float('Gini Coefficient')
    ks_statistic = fields.Float('KS Statistic')
    
    # Fields for model parameters
    parameters = fields.Text('Model Parameters', help="JSON representation of model parameters")
    
    # Relationships
    credit_scores_ids = fields.One2many('credit.score', 'model_id', string='Credit Scores')
    credit_policy_ids = fields.One2many('credit.policy', 'model_id', string='Credit Policies')
    
    _sql_constraints = [
        ('name_model_type_uniq', 'unique(name, model_type)', 'Model name must be unique per model type!')
    ]
    
    @api.model
    def load_model(self, model_id):
        """Load the pickled model from the binary field"""
        model_record = self.browse(model_id)
        if not model_record.model_file:
            return False
        
        try:
            model_binary = base64.b64decode(model_record.model_file)
            model = pickle.loads(model_binary)
            return model
        except Exception as e:
            _logger.error(f"Error loading model: {e}")
            return False
    
    def predict(self, features):
        """Make predictions using the loaded model
        
        Args:
            features: pandas DataFrame with the features required by the model
            
        Returns:
            Prediction results based on model type
        """
        self.ensure_one()
        model = self.load_model(self.id)
        
        if not model:
            return False
        
        try:
            # Make prediction based on model type
            if self.model_type == 'pd':
                # For PD models, return probability of default
                if hasattr(model, 'predict_proba'):
                    result = model.predict_proba(features)[:, 1]  # Probability of positive class
                else:
                    result = model.predict(features)
            elif self.model_type in ['ead', 'lgd']:
                # For EAD and LGD models, return the predicted value
                result = model.predict(features)
            else:
                return False
                
            return result
        except Exception as e:
            _logger.error(f"Error making prediction: {e}")
            return False