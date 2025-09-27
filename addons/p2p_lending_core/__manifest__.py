{
    'name': 'P2P Lending Core',
    'version': '1.0.0',
    'category': 'Finance',
    'summary': 'Hệ thống P2P Lending tổng hợp',
    'description': """
        Module tổng hợp cho hệ thống P2P Lending:
        - Cấu hình khoản vay và lãi suất
        - Quản lý giải ngân khoản vay
        - Bridge đồng bộ dữ liệu MongoDB
        - Quản lý wallet và blockchain
        - Workflow phê duyệt tự động
        - Báo cáo và thống kê
    """,
    'author': 'P2P Lending Team',
    'website': 'https://www.p2plending.com',
    'depends': ['base', 'mail', 'web'],
    'data': [
        # Security
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        
        # Views
        'views/loan_config_views.xml',
        'views/disbursement_views.xml',
        'views/p2p_wallet_view.xml',
        'views/borrower_views.xml',
        'views/investor_views.xml',
        'views/loan_views.xml',
        
        # Wizards
        'wizard/sync_wizard_view.xml',
        
        # Menus (after wizards)
        'views/menu_views.xml',
        'views/custom_templates.xml',
        
        # Data
        'data/loan_type_data.xml',
        'data/disbursement_sequence.xml',
        'data/ir_cron.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
