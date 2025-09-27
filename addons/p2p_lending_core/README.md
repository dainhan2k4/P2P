# P2P Lending Core

## Tổng quan

Module tổng hợp cho hệ thống P2P Lending, kết hợp 3 module chính:
- **Loan Configuration**: Cấu hình khoản vay và lãi suất
- **Loan Disbursement**: Quản lý giải ngân khoản vay  
- **P2P Bridge**: Đồng bộ dữ liệu MongoDB

## Tính năng chính

### 1. Cấu hình hệ thống
- Cấu hình loại khoản vay
- Cấu hình lãi suất theo thời hạn
- Cấu hình phí dịch vụ
- Cấu hình blockchain

### 2. Quản lý giải ngân
- Workflow phê duyệt giải ngân
- Tích hợp blockchain
- Báo cáo giải ngân
- Quản lý trạng thái

### 3. Bridge đồng bộ
- Đồng bộ dữ liệu từ MongoDB
- Quản lý wallet
- Cron job tự động
- Tool test kết nối

## Cấu trúc module

```
p2p_lending_core/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── loan_config_models.py
│   ├── disbursement_models.py
│   └── p2p_bridge_models.py
├── controllers/
│   ├── __init__.py
│   └── main.py
├── wizard/
│   ├── __init__.py
│   └── sync_wizard.py
├── views/
│   ├── loan_config_views.xml
│   ├── disbursement_views.xml
│   ├── p2p_wallet_view.xml
│   ├── borrower_views.xml
│   ├── investor_views.xml
│   ├── menu_views.xml
│   └── custom_templates.xml
├── security/
│   ├── ir.model.access.csv
│   └── security_groups.xml
└── data/
    ├── loan_type_data.xml
    ├── disbursement_sequence.xml
    └── ir_cron.xml
```

## Cài đặt

1. Copy module vào thư mục addons
2. Restart Odoo
3. Cài đặt module "P2P Lending Core"
4. Cấu hình kết nối MongoDB trong Settings

## Sử dụng

1. **Cấu hình**: Vào P2P Lending > Configuration
2. **Giải ngân**: Vào P2P Lending > Disbursement  
3. **Đồng bộ**: Vào P2P Lending > Bridge > Sync Data
4. **Báo cáo**: Vào P2P Lending > Reports

## Lưu ý

- Module này thay thế cho 3 module riêng lẻ
- Cần cấu hình kết nối MongoDB trước khi sử dụng
- Cron job sẽ chạy tự động mỗi 5 phút để đồng bộ dữ liệu
