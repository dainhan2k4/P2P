# -*- coding: utf-8 -*-
{
    "name": "Lending Club - Phân tích tín dụng",
    "summary": "Nhập liệu Lending Club, tính điểm tín dụng, phân tích qua List/Graph/Pivot",
    "version": "18.0.1.0.0",
    "category": "Accounting/Finance",
    "author": "Your Company",
    "website": "",
    "license": "LGPL-3",
    "depends": ["base", "p2p_lending"],
    "data": [
        "security/ir.model.access.csv",
        "views/lc_loan_views.xml",
        "views/lc_import_wizard_views.xml",
        "views/lc_to_p2p_wizard_views.xml",
        "views/lending_loan_extension_views.xml",
        "views/train_models_wizard_views.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}

