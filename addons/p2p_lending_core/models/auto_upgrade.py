# -*- coding: utf-8 -*-

from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

class IrModuleModule(models.Model):
    _inherit = 'ir.module.module'

    @api.model
    def auto_upgrade_p2p_core(self):
        """Tự động upgrade module p2p_lending_core"""
        try:
            # Tìm module p2p_lending_core
            module = self.env['ir.module.module'].search([
                ('name', '=', 'p2p_lending_core'),
                ('state', '=', 'installed')
            ], limit=1)
            
            if module:
                _logger.info("Auto upgrading p2p_lending_core module...")
                
                # Upgrade module
                module.button_immediate_upgrade()
                
                _logger.info("P2P Lending Core module upgraded successfully")
            else:
                _logger.warning("P2P Lending Core module not found or not installed")
                
        except Exception as e:
            _logger.error(f"Error auto upgrading p2p_lending_core: {str(e)}")
            
        return True
