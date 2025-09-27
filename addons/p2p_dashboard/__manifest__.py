# -*- coding: utf-8 -*-
{
    "name": "P2P Lending Core Dashboard",
        "version": "18.0.2.5.0",
    "category": "Finance",
    "summary": "Bảng điều khiển và thống kê cho P2P Lending Core System",
    "description": """
        Module cung cấp bảng điều khiển và các chức năng phân tích dữ liệu cho hệ thống P2P Lending Core.
        
    🚀 **TÍNH NĂNG:**
        - Phân tích hồ sơ vay (Loan Applications)
        - Thống kê giải ngân (Disbursements) 
        - Phân tích người dùng và rủi ro
        - Hiệu suất hệ thống và ví điện tử
        - Phân tích tài chính và doanh thu
        
    📊 **BIỂU ĐỒ VÀ THỐNG KÊ (tinh gọn):**
    - Trạng thái hồ sơ vay và giá trị theo trạng thái
    - Trạng thái giải ngân
        
        🔗 **TÍCH HỢP:**
        - Sử dụng dữ liệu từ P2P Lending Core
        - Loan Applications, Disbursements, Wallets
        - Loan Types, Configurations
        - Real-time data visualization
    """,
    "author": "Your Company",
    "website": "https://www.yourcompany.com",
    "depends": ["base", "web", "p2p_lending_core"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/permission_checker_views.xml",
        "views/data_debug_views.xml", 
        "views/dashboard_views.xml",
        "views/menu_views.xml",
        "data/demo_data.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
    "assets": {
        "web.assets_backend": [
            # Stylesheets - tải trước theo thứ tự ưu tiên
            "p2p_dashboard/static/src/css/dashboard.css",
            "p2p_dashboard/static/src/css/dashboard_stats.css",
            "p2p_dashboard/static/src/css/dashboard_enhanced.css",
            # Chart.js (UMD) - cần trước khi load widget
            "p2p_dashboard/static/lib/chartjs/chart.umd.min.js",
            # JavaScript - tải các files theo đúng thứ tự
            "p2p_dashboard/static/src/js/dashboard_graph_renderer_utf8.js",
            "p2p_dashboard/static/src/js/dashboard_graph_widget_registry.js",
            "p2p_dashboard/static/src/js/chart_debug_helper.js",
        ],
        "web.assets_qweb": [
            "p2p_dashboard/static/src/xml/dashboard_graph_renderer.xml",
        ],
    }
}