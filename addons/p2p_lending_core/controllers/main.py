# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class P2PLendingController(http.Controller):
    
    @http.route('/p2p/sync', type='http', auth='user', website=True)
    def sync_data(self, **kwargs):
        """Sync data from MongoDB"""
        try:
            # Get sync wizard
            wizard = request.env['p2p.sync.wizard'].create({
                'sync_type': 'all',
                'force_sync': False
            })
            
            result = wizard.action_sync()
            return result
            
        except Exception as e:
            _logger.error(f"Error in sync controller: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Lỗi',
                    'message': f'Lỗi đồng bộ: {str(e)}',
                    'type': 'danger',
                }
            }
    
    @http.route('/p2p/test-connection', type='http', auth='user', website=True)
    def test_connection(self, **kwargs):
        """Test MongoDB connection"""
        try:
            bridge = request.env['p2p.bridge']
            result = bridge.test_connection()
            return result
            
        except Exception as e:
            _logger.error(f"Error testing connection: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Lỗi',
                    'message': f'Lỗi test kết nối: {str(e)}',
                    'type': 'danger',
                }
            }
    
    @http.route('/p2p/statistics', type='http', auth='user', website=True)
    def get_statistics(self, **kwargs):
        """Get P2P statistics"""
        try:
            bridge = request.env['p2p.bridge']
            stats = bridge.get_statistics()
            return request.render('p2p_lending_core.statistics_template', {
                'stats': stats
            })
            
        except Exception as e:
            _logger.error(f"Error getting statistics: {e}")
            return request.render('p2p_lending_core.error_template', {
                'error': str(e)
            })
