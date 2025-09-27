# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
from datetime import datetime, date
import json

_logger = logging.getLogger(__name__)

class MongoDBMappingService(models.Model):
    """Service để mapping dữ liệu từ MongoDB sang Odoo"""
    _name = 'p2p.mongodb.mapping'
    _description = 'MongoDB to Odoo Mapping Service'
    
    name = fields.Char(string='Tên mapping', required=True)
    active = fields.Boolean(default=True, string='Hoạt động')
    
    # Mapping configuration
    borrower_mapping = fields.Text(string='Borrower Mapping Config', 
                                 default=lambda self: self._get_default_borrower_mapping())
    loan_mapping = fields.Text(string='Loan Mapping Config',
                              default=lambda self: self._get_default_loan_mapping())
    investor_mapping = fields.Text(string='Investor Mapping Config',
                                 default=lambda self: self._get_default_investor_mapping())
    
    def _get_default_borrower_mapping(self):
        """Default mapping cho Borrower từ MongoDB sang Odoo"""
        return json.dumps({
            "mongodb_field": "odoo_field",
            "name": "name",
            "email": "email", 
            "phone": "phone",
            "dateOfBirth": "date_of_birth",
            "gender": "gender",
            "monthlyIncome": "monthly_income",
            "employmentStatus": "employment_status",
            "address": "address",
            "city": "city",
            "idNumber": "id_number",
            "creditScore": "credit_score_ml"
        }, indent=2)
    
    def _get_default_loan_mapping(self):
        """Default mapping cho Loan từ MongoDB sang Odoo"""
        return json.dumps({
            "mongodb_field": "odoo_field",
            "borrowerId": "borrower_id",
            "amount": "amount",
            "term": "term", 
            "interestRate": "interest_rate",
            "startDate": "start_date",
            "purpose": "purpose",
            "status": "state",
            "monthlyPayment": "monthly_payment"
        }, indent=2)
    
    def _get_default_investor_mapping(self):
        """Default mapping cho Investor từ MongoDB sang Odoo"""
        return json.dumps({
            "mongodb_field": "odoo_field",
            "name": "name",
            "email": "email",
            "phone": "phone", 
            "investmentCapacity": "investment_capacity",
            "riskTolerance": "risk_tolerance"
        }, indent=2)
    
    def sync_borrowers_from_mongodb(self, mongo_data_list):
        """Đồng bộ borrowers từ MongoDB sang Odoo"""
        mapping_config = json.loads(self.borrower_mapping)
        created_count = 0
        updated_count = 0
        
        for mongo_data in mongo_data_list:
            try:
                # Tìm borrower hiện tại
                existing_borrower = self.env['p2p.borrower'].search([
                    ('id_number', '=', mongo_data.get('idNumber'))
                ], limit=1)
                
                # Chuẩn bị dữ liệu cho Odoo
                odoo_data = self._map_mongodb_to_odoo(mongo_data, mapping_config)
                
                if existing_borrower:
                    # Cập nhật borrower hiện tại
                    existing_borrower.write(odoo_data)
                    updated_count += 1
                    _logger.info(f"Updated borrower: {existing_borrower.name}")
                else:
                    # Tạo borrower mới
                    borrower = self.env['p2p.borrower'].create(odoo_data)
                    created_count += 1
                    _logger.info(f"Created new borrower: {borrower.name}")
                    
            except Exception as e:
                _logger.error(f"Error syncing borrower {mongo_data.get('name', 'Unknown')}: {e}")
        
        return {
            'created': created_count,
            'updated': updated_count,
            'total': len(mongo_data_list)
        }
    
    def sync_loans_from_mongodb(self, mongo_data_list):
        """Đồng bộ loans từ MongoDB sang Odoo"""
        mapping_config = json.loads(self.loan_mapping)
        created_count = 0
        updated_count = 0
        
        for mongo_data in mongo_data_list:
            try:
                # Tìm borrower tương ứng
                borrower = self.env['p2p.borrower'].search([
                    ('id_number', '=', mongo_data.get('borrowerId'))
                ], limit=1)
                
                if not borrower:
                    _logger.warning(f"Borrower not found for loan: {mongo_data.get('id', 'Unknown')}")
                    continue
                
                # Tìm loan hiện tại
                existing_loan = self.env['p2p.loan'].search([
                    ('name', '=', mongo_data.get('id'))
                ], limit=1)
                
                # Chuẩn bị dữ liệu cho Odoo
                odoo_data = self._map_mongodb_to_odoo(mongo_data, mapping_config)
                odoo_data['borrower_id'] = borrower.id
                
                if existing_loan:
                    # Cập nhật loan hiện tại
                    existing_loan.write(odoo_data)
                    updated_count += 1
                    _logger.info(f"Updated loan: {existing_loan.name}")
                else:
                    # Tạo loan mới
                    loan = self.env['p2p.loan'].create(odoo_data)
                    created_count += 1
                    _logger.info(f"Created new loan: {loan.name}")
                    
            except Exception as e:
                _logger.error(f"Error syncing loan {mongo_data.get('id', 'Unknown')}: {e}")
        
        return {
            'created': created_count,
            'updated': updated_count,
            'total': len(mongo_data_list)
        }
    
    def sync_investors_from_mongodb(self, mongo_data_list):
        """Đồng bộ investors từ MongoDB sang Odoo"""
        mapping_config = json.loads(self.investor_mapping)
        created_count = 0
        updated_count = 0
        
        for mongo_data in mongo_data_list:
            try:
                # Tìm investor hiện tại
                existing_investor = self.env['p2p.investor'].search([
                    ('email', '=', mongo_data.get('email'))
                ], limit=1)
                
                # Chuẩn bị dữ liệu cho Odoo
                odoo_data = self._map_mongodb_to_odoo(mongo_data, mapping_config)
                
                if existing_investor:
                    # Cập nhật investor hiện tại
                    existing_investor.write(odoo_data)
                    updated_count += 1
                    _logger.info(f"Updated investor: {existing_investor.name}")
                else:
                    # Tạo investor mới
                    investor = self.env['p2p.investor'].create(odoo_data)
                    created_count += 1
                    _logger.info(f"Created new investor: {investor.name}")
                    
            except Exception as e:
                _logger.error(f"Error syncing investor {mongo_data.get('name', 'Unknown')}: {e}")
        
        return {
            'created': created_count,
            'updated': updated_count,
            'total': len(mongo_data_list)
        }
    
    def _map_mongodb_to_odoo(self, mongo_data, mapping_config):
        """Map dữ liệu từ MongoDB sang Odoo theo config"""
        odoo_data = {}
        
        for mongo_field, odoo_field in mapping_config.items():
            if mongo_field == "mongodb_field":  # Skip header
                continue
                
            if mongo_field in mongo_data:
                value = mongo_data[mongo_field]
                
                # Xử lý các trường đặc biệt
                if odoo_field == 'date_of_birth' and value:
                    if isinstance(value, str):
                        value = datetime.strptime(value, '%Y-%m-%d').date()
                    elif isinstance(value, datetime):
                        value = value.date()
                
                elif odoo_field == 'gender' and value:
                    gender_mapping = {
                        'male': 'male',
                        'female': 'female',
                        'M': 'male',
                        'F': 'female',
                        'Nam': 'male',
                        'Nữ': 'female'
                    }
                    value = gender_mapping.get(value, 'other')
                
                elif odoo_field == 'employment_status' and value:
                    employment_mapping = {
                        'employed': 'employed',
                        'self_employed': 'self_employed',
                        'business_owner': 'business_owner',
                        'unemployed': 'unemployed',
                        'Đang làm việc': 'employed',
                        'Tự kinh doanh': 'self_employed',
                        'Chủ doanh nghiệp': 'business_owner',
                        'Thất nghiệp': 'unemployed'
                    }
                    value = employment_mapping.get(value, 'unemployed')
                
                elif odoo_field == 'state' and value:
                    state_mapping = {
                        'draft': 'draft',
                        'pending': 'waiting_approval',
                        'approved': 'approved',
                        'disbursed': 'disbursed',
                        'active': 'in_progress',
                        'completed': 'paid',
                        'defaulted': 'defaulted',
                        'cancelled': 'cancelled',
                        'Nháp': 'draft',
                        'Chờ duyệt': 'waiting_approval',
                        'Đã duyệt': 'approved',
                        'Đã giải ngân': 'disbursed',
                        'Đang trả nợ': 'in_progress',
                        'Hoàn thành': 'paid',
                        'Quá hạn': 'defaulted',
                        'Đã hủy': 'cancelled'
                    }
                    value = state_mapping.get(value, 'draft')
                
                odoo_data[odoo_field] = value
        
        return odoo_data
    
    def sync_all_data_from_mongodb(self):
        """Đồng bộ tất cả dữ liệu từ MongoDB"""
        try:
            # Lấy dữ liệu từ MongoDB service
            mongo_service = self.env['p2p.mongo.service']
            
            # Sync borrowers
            borrowers_data = mongo_service.get_borrowers()
            borrower_result = self.sync_borrowers_from_mongodb(borrowers_data)
            
            # Sync loans
            loans_data = mongo_service.get_loans()
            loan_result = self.sync_loans_from_mongodb(loans_data)
            
            # Sync investors
            investors_data = mongo_service.get_investors()
            investor_result = self.sync_investors_from_mongodb(investors_data)
            
            return {
                'borrowers': borrower_result,
                'loans': loan_result,
                'investors': investor_result,
                'success': True
            }
            
        except Exception as e:
            _logger.error(f"Error syncing all data from MongoDB: {e}")
            return {
                'error': str(e),
                'success': False
            }
