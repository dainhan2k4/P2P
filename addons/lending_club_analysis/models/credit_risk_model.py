# -*- coding: utf-8 -*-
import os
import pickle
import logging
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, mean_squared_error
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class CreditRiskModel(models.Model):
    _name = 'credit.risk.model'
    _description = 'Credit Risk Model for PD, EAD, LGD'

    name = fields.Char(string='Model Name', required=True)
    model_type = fields.Selection([
        ('pd', 'Probability of Default (PD)'),
        ('ead', 'Exposure at Default (EAD)'),
        ('lgd', 'Loss Given Default (LGD)')
    ], string='Model Type', required=True)

    trained_date = fields.Datetime(string='Trained Date', readonly=True)
    accuracy_score = fields.Float(string='Accuracy Score', readonly=True)
    mse_score = fields.Float(string='MSE Score', readonly=True)
    model_file = fields.Char(string='Model File Path', readonly=True)

    is_active = fields.Boolean(string='Is Active', default=False)
    training_data_count = fields.Integer(string='Training Data Count', readonly=True)

    @api.model
    def create_pd_model(self):
        """Create and train PD (Probability of Default) model"""
        # Load historical data
        csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'loan_data_2007_2014.csv')
        if not os.path.exists(csv_path):
            raise ValueError("Historical loan data CSV file not found")

        df = pd.read_csv(csv_path)

        # Prepare features for PD model
        features = [
            'loan_amnt', 'int_rate', 'installment', 'annual_inc', 'dti',
            'delinq_2yrs', 'pub_rec', 'fico_range_low', 'fico_range_high',
            'open_acc', 'total_acc', 'revol_bal', 'revol_util',
            'inq_last_6mths', 'emp_length_num'
        ]

        # Convert emp_length to numeric
        df['emp_length_num'] = df['emp_length'].fillna('0').str.extract('(\d+)').fillna(0).astype(int)

        # Create target variable (1 if defaulted, 0 otherwise)
        default_statuses = ['Charged Off', 'Default', 'Late (31-120 days)', 'Late (16-30 days)']
        df['is_default'] = df['loan_status'].isin(default_statuses).astype(int)

        # Filter out current loans and prepare data
        df_model = df[df['loan_status'] != 'Current'].copy()
        df_model = df_model[features + ['is_default']].dropna()

        X = df_model[features]
        y = df_model['is_default']

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Train Random Forest model
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)

        # Evaluate model
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)

        # Save model
        model_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
        os.makedirs(model_dir, exist_ok=True)
        model_path = os.path.join(model_dir, 'pd_model.pkl')

        with open(model_path, 'wb') as f:
            pickle.dump(model, f)

        # Create model record
        model_record = self.create({
            'name': f'PD Model - {fields.Datetime.now().strftime("%Y%m%d_%H%M%S")}',
            'model_type': 'pd',
            'trained_date': fields.Datetime.now(),
            'accuracy_score': accuracy,
            'model_file': model_path,
            'training_data_count': len(X_train),
            'is_active': True
        })

        # Deactivate previous PD models
        self.search([('model_type', '=', 'pd'), ('id', '!=', model_record.id)]).write({'is_active': False})

        _logger.info(f"PD Model trained with accuracy: {accuracy:.4f}")
        return model_record

    @api.model
    def create_ead_model(self):
        """Create and train EAD (Exposure at Default) model"""
        csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'loan_data_2007_2014.csv')
        if not os.path.exists(csv_path):
            raise ValueError("Historical loan data CSV file not found")

        df = pd.read_csv(csv_path)

        # Prepare features for EAD model
        features = [
            'loan_amnt', 'int_rate', 'installment', 'annual_inc', 'dti',
            'delinq_2yrs', 'pub_rec', 'fico_range_low', 'fico_range_high',
            'open_acc', 'total_acc', 'revol_bal', 'revol_util',
            'inq_last_6mths', 'emp_length_num'
        ]

        # Convert emp_length to numeric
        df['emp_length_num'] = df['emp_length'].fillna('0').str.extract('(\d+)').fillna(0).astype(int)

        # Filter for defaulted loans only
        default_statuses = ['Charged Off', 'Default']
        df_defaulted = df[df['loan_status'].isin(default_statuses)].copy()

        # Calculate EAD as percentage of outstanding principal at default
        df_defaulted['ead_ratio'] = df_defaulted['out_prncp'] / df_defaulted['loan_amnt']
        df_defaulted['ead_ratio'] = df_defaulted['ead_ratio'].clip(0, 1)  # Ensure between 0 and 1

        # Prepare data
        df_model = df_defaulted[features + ['ead_ratio']].dropna()

        X = df_model[features]
        y = df_model['ead_ratio']

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Train Random Forest regressor
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)

        # Evaluate model
        y_pred = model.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)

        # Save model
        model_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
        os.makedirs(model_dir, exist_ok=True)
        model_path = os.path.join(model_dir, 'ead_model.pkl')

        with open(model_path, 'wb') as f:
            pickle.dump(model, f)

        # Create model record
        model_record = self.create({
            'name': f'EAD Model - {fields.Datetime.now().strftime("%Y%m%d_%H%M%S")}',
            'model_type': 'ead',
            'trained_date': fields.Datetime.now(),
            'mse_score': mse,
            'model_file': model_path,
            'training_data_count': len(X_train),
            'is_active': True
        })

        # Deactivate previous EAD models
        self.search([('model_type', '=', 'ead'), ('id', '!=', model_record.id)]).write({'is_active': False})

        _logger.info(f"EAD Model trained with MSE: {mse:.4f}")
        return model_record

    @api.model
    def create_lgd_model(self):
        """Create and train LGD (Loss Given Default) model"""
        csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'loan_data_2007_2014.csv')
        if not os.path.exists(csv_path):
            raise ValueError("Historical loan data CSV file not found")

        df = pd.read_csv(csv_path)

        # Prepare features for LGD model
        features = [
            'loan_amnt', 'int_rate', 'installment', 'annual_inc', 'dti',
            'delinq_2yrs', 'pub_rec', 'fico_range_low', 'fico_range_high',
            'open_acc', 'total_acc', 'revol_bal', 'revol_util',
            'inq_last_6mths', 'emp_length_num'
        ]

        # Convert emp_length to numeric
        df['emp_length_num'] = df['emp_length'].fillna('0').str.extract('(\d+)').fillna(0).astype(int)

        # Filter for defaulted loans only
        default_statuses = ['Charged Off', 'Default']
        df_defaulted = df[df['loan_status'].isin(default_statuses)].copy()

        # Calculate LGD as (1 - recovery rate)
        # Recovery rate = recoveries / (loan_amnt - recoveries) if recoveries > 0 else 0
        df_defaulted['recovery_rate'] = 0.0
        mask = df_defaulted['recoveries'] > 0
        df_defaulted.loc[mask, 'recovery_rate'] = (
            df_defaulted.loc[mask, 'recoveries'] /
            (df_defaulted.loc[mask, 'loan_amnt'] - df_defaulted.loc[mask, 'recoveries'])
        )
        df_defaulted['recovery_rate'] = df_defaulted['recovery_rate'].clip(0, 1)
        df_defaulted['lgd'] = 1 - df_defaulted['recovery_rate']

        # Prepare data
        df_model = df_defaulted[features + ['lgd']].dropna()

        X = df_model[features]
        y = df_model['lgd']

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Train Random Forest regressor
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)

        # Evaluate model
        y_pred = model.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)

        # Save model
        model_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
        os.makedirs(model_dir, exist_ok=True)
        model_path = os.path.join(model_dir, 'lgd_model.pkl')

        with open(model_path, 'wb') as f:
            pickle.dump(model, f)

        # Create model record
        model_record = self.create({
            'name': f'LGD Model - {fields.Datetime.now().strftime("%Y%m%d_%H%M%S")}',
            'model_type': 'lgd',
            'trained_date': fields.Datetime.now(),
            'mse_score': mse,
            'model_file': model_path,
            'training_data_count': len(X_train),
            'is_active': True
        })

        # Deactivate previous LGD models
        self.search([('model_type', '=', 'lgd'), ('id', '!=', model_record.id)]).write({'is_active': False})

        _logger.info(f"LGD Model trained with MSE: {mse:.4f}")
        return model_record

    @api.model
    def train_all_models(self):
        """Train all three risk models (PD, EAD, LGD)"""
        _logger.info("Starting training of all credit risk models")

        try:
            pd_model = self.create_pd_model()
            ead_model = self.create_ead_model()
            lgd_model = self.create_lgd_model()

            _logger.info("All credit risk models trained successfully")
            return {
                'pd_model': pd_model.id,
                'ead_model': ead_model.id,
                'lgd_model': lgd_model.id
            }
        except Exception as e:
            _logger.error(f"Error training models: {str(e)}")
            raise

    def get_active_model(self, model_type):
        """Get the active model for a specific type"""
        return self.search([('model_type', '=', model_type), ('is_active', '=', True)], limit=1)

    def predict_pd(self, features):
        """Predict Probability of Default using active PD model"""
        model_record = self.get_active_model('pd')
        if not model_record or not os.path.exists(model_record.model_file):
            raise ValueError("No active PD model found")

        with open(model_record.model_file, 'rb') as f:
            model = pickle.load(f)

        # Ensure features are in correct order
        feature_order = [
            'loan_amnt', 'int_rate', 'installment', 'annual_inc', 'dti',
            'delinq_2yrs', 'pub_rec', 'fico_range_low', 'fico_range_high',
            'open_acc', 'total_acc', 'revol_bal', 'revol_util',
            'inq_last_6mths', 'emp_length_num'
        ]

        features_df = pd.DataFrame([features])
        features_df = features_df[feature_order]

        return model.predict_proba(features_df)[0][1]  # Return probability of default

    def predict_ead(self, features):
        """Predict Exposure at Default using active EAD model"""
        model_record = self.get_active_model('ead')
        if not model_record or not os.path.exists(model_record.model_file):
            raise ValueError("No active EAD model found")

        with open(model_record.model_file, 'rb') as f:
            model = pickle.load(f)

        # Ensure features are in correct order
        feature_order = [
            'loan_amnt', 'int_rate', 'installment', 'annual_inc', 'dti',
            'delinq_2yrs', 'pub_rec', 'fico_range_low', 'fico_range_high',
            'open_acc', 'total_acc', 'revol_bal', 'revol_util',
            'inq_last_6mths', 'emp_length_num'
        ]

        features_df = pd.DataFrame([features])
        features_df = features_df[feature_order]

        return model.predict(features_df)[0]

    def predict_lgd(self, features):
        """Predict Loss Given Default using active LGD model"""
        model_record = self.get_active_model('lgd')
        if not model_record or not os.path.exists(model_record.model_file):
            raise ValueError("No active LGD model found")

        with open(model_record.model_file, 'rb') as f:
            model = pickle.load(f)

        # Ensure features are in correct order
        feature_order = [
            'loan_amnt', 'int_rate', 'installment', 'annual_inc', 'dti',
            'delinq_2yrs', 'pub_rec', 'fico_range_low', 'fico_range_high',
            'open_acc', 'total_acc', 'revol_bal', 'revol_util',
            'inq_last_6mths', 'emp_length_num'
        ]

        features_df = pd.DataFrame([features])
        features_df = features_df[feature_order]

        return model.predict(features_df)[0]