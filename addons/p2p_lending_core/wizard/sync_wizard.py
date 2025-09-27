# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class P2PSyncWizard(models.TransientModel):
    """Wizard để đồng bộ dữ liệu từ MongoDB sang Odoo"""
    _name = 'p2p.sync.wizard'
    _description = 'P2P Sync Wizard'
    
    name = fields.Char(string='Tên đồng bộ', default='MongoDB Sync')
    sync_borrowers = fields.Boolean(string='Đồng bộ Borrowers', default=True)
    sync_loans = fields.Boolean(string='Đồng bộ Loans', default=True)
    sync_investors = fields.Boolean(string='Đồng bộ Investors', default=True)
    sync_investments = fields.Boolean(string='Đồng bộ Investments', default=True)
    
    # Kết quả đồng bộ
    result_borrowers = fields.Text(string='Kết quả Borrowers', readonly=True)
    result_loans = fields.Text(string='Kết quả Loans', readonly=True)
    result_investors = fields.Text(string='Kết quả Investors', readonly=True)
    result_investments = fields.Text(string='Kết quả Investments', readonly=True)
    
    # Trạng thái
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('running', 'Đang chạy'),
        ('done', 'Hoàn thành'),
        ('error', 'Lỗi')
    ], string='Trạng thái', default='draft')
    
    def action_sync_all(self):
        """Đồng bộ tất cả dữ liệu"""
        self.write({'state': 'running'})
        
        try:
            # Lấy mapping service
            mapping_service = self.env['p2p.mongodb.mapping'].search([('active', '=', True)], limit=1)
            if not mapping_service:
                mapping_service = self.env['p2p.mongodb.mapping'].create({
                    'name': 'Default MongoDB Mapping'
                })
            
            results = {}
            
            # Đồng bộ borrowers
            if self.sync_borrowers:
                try:
                    mongo_service = self.env['p2p.mongo.service']
                    borrowers_data = mongo_service.get_borrowers()
                    result = mapping_service.sync_borrowers_from_mongodb(borrowers_data)
                    results['borrowers'] = result
                    self.result_borrowers = f"Created: {result['created']}, Updated: {result['updated']}, Total: {result['total']}"
                except Exception as e:
                    self.result_borrowers = f"Error: {str(e)}"
                    _logger.error(f"Error syncing borrowers: {e}")
            
            # Đồng bộ loans
            if self.sync_loans:
                try:
                    mongo_service = self.env['p2p.mongo.service']
                    loans_data = mongo_service.get_loans()
                    result = mapping_service.sync_loans_from_mongodb(loans_data)
                    results['loans'] = result
                    self.result_loans = f"Created: {result['created']}, Updated: {result['updated']}, Total: {result['total']}"
                except Exception as e:
                    self.result_loans = f"Error: {str(e)}"
                    _logger.error(f"Error syncing loans: {e}")
            
            # Đồng bộ investors
            if self.sync_investors:
                try:
                    mongo_service = self.env['p2p.mongo.service']
                    investors_data = mongo_service.get_investors()
                    result = mapping_service.sync_investors_from_mongodb(investors_data)
                    results['investors'] = result
                    self.result_investors = f"Created: {result['created']}, Updated: {result['updated']}, Total: {result['total']}"
                except Exception as e:
                    self.result_investors = f"Error: {str(e)}"
                    _logger.error(f"Error syncing investors: {e}")
            
            # Đồng bộ investments
            if self.sync_investments:
                try:
                    mongo_service = self.env['p2p.mongo.service']
                    investments_data = mongo_service.get_investments()
                    result = mapping_service.sync_investments_from_mongodb(investments_data)
                    results['investments'] = result
                    self.result_investments = f"Created: {result['created']}, Updated: {result['updated']}, Total: {result['total']}"
                except Exception as e:
                    self.result_investments = f"Error: {str(e)}"
                    _logger.error(f"Error syncing investments: {e}")
            
            self.write({'state': 'done'})
            
            # Hiển thị kết quả
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'p2p.sync.wizard',
                'view_mode': 'form',
                'res_id': self.id,
                'target': 'new',
                'context': {'show_result': True}
            }
            
        except Exception as e:
            self.write({'state': 'error'})
            _logger.error(f"Error in sync wizard: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Lỗi đồng bộ',
                    'message': f'Có lỗi xảy ra: {str(e)}',
                    'type': 'danger'
                }
            }
    
    def action_view_results(self):
        """Xem kết quả đồng bộ"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'p2p.sync.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new'
        }