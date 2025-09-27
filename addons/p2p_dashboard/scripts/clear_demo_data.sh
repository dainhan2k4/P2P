#!/bin/bash

# Script xóa dữ liệu demo từ database
# Chạy trong container Odoo

echo "🗑️ Đang xóa dữ liệu demo dashboard..."

# Kết nối database và xóa records demo
docker exec odoo-18-docker-compose_web_1 python3 -c "
import odoo
from odoo import api

# Kết nối database
odoo.tools.config.parse_config(['-d', 'postgres'])
env = api.Environment.manage()

with env:
    with env['base'].env.cr.savepoint():
        # Xóa demo dashboard
        demo_dashboards = env['p2p.dashboard'].search([('name', 'ilike', 'mẫu')])
        print(f'Tìm thấy {len(demo_dashboards)} dashboard demo')
        demo_dashboards.unlink()
        
        # Xóa external ID liên quan
        external_ids = env['ir.model.data'].search([
            ('module', '=', 'p2p_dashboard'),
            ('name', '=', 'demo_p2p_dashboard')
        ])
        external_ids.unlink()
        
        print('✅ Đã xóa tất cả dữ liệu demo!')
"

echo "✅ Hoàn thành xóa dữ liệu demo"