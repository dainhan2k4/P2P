# -*- coding: utf-8 -*-
{
    "name": "P2P Lending",
    "version": "18.0.1.0.0",
    "category": "Finance",
    "summary": "Quản lý cho vay ngang hàng",
    "description": """
        Module quản lý các khoản vay và đầu tư P2P
    """,
    "author": "Your Company",
    "website": "https://www.yourcompany.com",
    "depends": ["base", "mail", "p2p_lending_core"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequences.xml",
        "views/borrower_views.xml",
        "views/loan_views.xml",
        "views/investor_views.xml",
        "views/investment_views.xml",
        "views/payment_views.xml",
        "views/investor_enhanced_views.xml",
        "views/investment_enhanced_views.xml",
        "views/menu_views.xml",
    ],
    "external_dependencies": {
        "python": ["pandas"]
    },
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}