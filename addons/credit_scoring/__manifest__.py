# -*- coding: utf-8 -*-
{
    "name": "Credit Scoring",
    "summary": "Chấm điểm tín dụng dựa trên mô hình PD, EAD, LGD",
    "version": "18.0.1.0.3",
    "category": "Finance",
    "author": "Your Company",
    "website": "",
    "license": "LGPL-3",
    "depends": ["base", "mail", "p2p_lending", "lending_club_analysis"],
    "data": [
        "security/ir.model.access.csv",
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}