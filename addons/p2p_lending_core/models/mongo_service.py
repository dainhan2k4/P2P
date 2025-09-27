# -*- coding: utf-8 -*-

import requests
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

class MongoService:
    def __init__(self, env=None):
        # Lấy API URL từ config
        if env:
            try:
                config = env['loan.config'].search([], limit=1)
                if config:
                    # Fix Docker networking: use host.docker.internal instead of localhost
                    if config.server_api_url and 'localhost' in config.server_api_url:
                        self.base_url = config.server_api_url.replace('localhost', 'host.docker.internal')
                        _logger.info(f"Docker fix: Changed localhost to host.docker.internal: {self.base_url}")
                        # Auto-update config to use host.docker.internal
                        config.write({'server_api_url': self.base_url})
                    else:
                        self.base_url = config.server_api_url or "http://host.docker.internal:3000"
                    _logger.info(f"Using API URL from config: {self.base_url}")
                else:
                    self.base_url = "http://host.docker.internal:3000"
                    _logger.info(f"No config found, using default API URL: {self.base_url}")
            except Exception as e:
                self.base_url = "http://host.docker.internal:3000"
                _logger.error(f"Error getting config: {e}, using default API URL: {self.base_url}")
        else:
            self.base_url = "http://host.docker.internal:3000"
            _logger.info(f"No env provided, using default API URL: {self.base_url}")
            
        self.api_endpoints = {
            'loans': '/api/loan/odoo/export/loans',
            'investments': '/api/loan/odoo/export/investments', 
            'lenders': '/api/loan/odoo/export/lenders',
            'waiting_rooms': '/api/loan/odoo/export/waiting-rooms',
            'mark_loans_synced': '/api/loan/odoo/mark/loans-synced',
            'mark_investments_synced': '/api/loan/odoo/mark/investments-synced',
            'mark_waiting_rooms_synced': '/api/loan/odoo/mark/waiting-rooms-synced',
            'mark_lenders_synced': '/api/loan/odoo/mark/lenders-synced'
        }
        _logger.info(f"API service initialized with base_url: {self.base_url}")

    def _make_api_request(self, endpoint, method='GET', data=None):
        """Gọi API từ Node.js server"""
        try:
            url = f"{self.base_url}{endpoint}"
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Odoo-P2P-Sync/1.0'
            }
            
            # Thêm authentication nếu có
            if hasattr(self, 'api_key') and self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            _logger.info(f"Making API request: {method} {url}")
            _logger.info(f"Headers: {headers}")
            if data:
                _logger.info(f"Data: {data}")
            
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            _logger.info(f"Response status: {response.status_code}")
            _logger.info(f"Response headers: {dict(response.headers)}")
            
            response.raise_for_status()
            result = response.json()
            _logger.info(f"Response data: {result}")
            return result
        except requests.exceptions.ConnectionError as e:
            _logger.error(f"Connection error: {e}")
            return None
        except requests.exceptions.Timeout as e:
            _logger.error(f"Timeout error: {e}")
            return None
        except requests.exceptions.HTTPError as e:
            _logger.error(f"HTTP error: {e}")
            return None
        except Exception as e:
            _logger.error(f"API request error: {e}")
            return None

    def get_loans(self, limit=50, offset=0, force_sync=False):
        """Lấy danh sách loans từ API hoặc fallback data"""
        try:
            endpoint = f"{self.api_endpoints['loans']}?limit={limit}&offset={offset}"
            if force_sync:
                endpoint += "&force_sync=true"
            response = self._make_api_request(endpoint)
            if response and 'data' in response:
                return response['data'].get('loans', [])
            return []

        except Exception as e:
            _logger.error(f"Error getting loans: {e}")
            return []

    def get_investments(self, limit=50, offset=0, force_sync=False):
        """Lấy danh sách investments từ API hoặc fallback data"""
        try:
            endpoint = f"{self.api_endpoints['investments']}?limit={limit}&offset={offset}"
            if force_sync:
                endpoint += "&force_sync=true"
            response = self._make_api_request(endpoint)
            if response and 'data' in response:
                return response['data'].get('investments', [])
            
            # Fallback to sample data
            
        except Exception as e:
            _logger.error(f"Error getting investments: {e}")
            return []

    def get_investors(self, limit=200, offset=0, force_sync=False):
        """Lấy danh sách investor users từ API riêng"""
        try:
            endpoint = f"{self.api_endpoints['lenders']}?limit={limit}&offset={offset}&category=lender"
            if force_sync:
                endpoint += "&force_sync=true"
            response = self._make_api_request(endpoint)
            if response and 'data' in response:
                # chấp nhận cấu trúc { data: { investors: [...] }} hoặc { data: [...] }
                data_obj = response.get('data')
                if isinstance(data_obj, dict):
                    items = data_obj.get('lenders', data_obj.get('users', []))
                elif isinstance(data_obj, list):
                    items = data_obj
                else:
                    items = []
                # Lọc theo category = lender (phòng trường hợp API không filter)
                filtered = []
                for it in items:
                    cat = (it.get('category') or it.get('role') or it.get('type') or '').lower()
                    if cat in ('lender', 'investor'):
                        filtered.append(it)
                return filtered
            return []
        except Exception as e:
            _logger.error(f"Error getting lenders: {e}")
            return []

    def get_waiting_rooms(self, limit=50, offset=0):
        """Lấy danh sách waiting rooms từ API"""
        try:
            endpoint = f"{self.api_endpoints['waiting_rooms']}?limit={limit}&offset={offset}"
            response = self._make_api_request(endpoint)
            if response and 'data' in response:
                return response['data'].get('waiting_rooms', [])
            return []
        except Exception as e:
            _logger.error(f"Error getting waiting rooms: {e}")
            return []

    def mark_loans_synced(self, contract_ids):
        """Đánh dấu loans đã sync"""
        try:
            data = {'contractIds': contract_ids}
            response = self._make_api_request(self.api_endpoints['mark_loans_synced'], 'POST', data)
            return response
        except Exception as e:
            _logger.error(f"Error marking loans synced: {e}")
            return None

    def mark_investments_synced(self, contract_ids):
        """Đánh dấu investments đã sync"""
        try:
            data = {'contractIds': contract_ids}
            response = self._make_api_request(self.api_endpoints['mark_investments_synced'], 'POST', data)
            return response
        except Exception as e:
            _logger.error(f"Error marking investments synced: {e}")
            return None

    def mark_waiting_rooms_synced(self, room_ids):
        """Đánh dấu waiting rooms đã sync"""
        try:
            data = {'roomIds': room_ids}
            response = self._make_api_request(self.api_endpoints['mark_waiting_rooms_synced'], 'POST', data)
            return response
        except Exception as e:
            _logger.error(f"Error marking waiting rooms synced: {e}")
            return None

    def sync_all_data(self, env=None):
        """Đồng bộ tất cả dữ liệu từ API"""
        try:
            # Reinitialize with env to get correct API URL
            if env:
                self.__init__(env)
            
            _logger.info("=== STARTING SYNC ALL DATA ===")
            _logger.info(f"Using API URL: {self.base_url}")
            
            # Debug API response để xem dữ liệu thực tế
            self.debug_api_response()
            
            # Debug: Test một loan cụ thể
            loans = self.get_loans(limit=1)
            if loans:
                _logger.info("=== DEBUG LOAN DATA IN ODOO ===")
                _logger.info(f"Loan data: {loans[0]}")
                if loans[0].get('borrower'):
                    _logger.info(f"Borrower data: {loans[0]['borrower']}")
                    _logger.info(f"Borrower name: {loans[0]['borrower'].get('name', 'NO NAME')}")
                    _logger.info(f"Borrower email: {loans[0]['borrower'].get('email', 'NO EMAIL')}")
            
            # Test tạo 1 borrower trước
            test_result = self.test_create_borrower(env)
            if not test_result:
                _logger.error("❌ Failed to create test borrower")
                return False
            else:
                _logger.info("✅ Test borrower created successfully")
            
            # Đồng bộ loans với force sync
            _logger.info("=== FETCHING LOANS FROM API ===")
            loans = self.get_loans(limit=100, force_sync=True)
            _logger.info(f"Total loans received: {len(loans)}")
            
            if loans:
                _logger.info("=== DEBUG LOAN DATA IN ODOO ===")
                _logger.info(f"First loan data: {loans[0]}")
                if loans[0].get('borrower'):
                    _logger.info(f"Borrower data: {loans[0]['borrower']}")
                    _logger.info(f"Borrower name: {loans[0]['borrower'].get('name', 'NO NAME')}")
                    _logger.info(f"Borrower email: {loans[0]['borrower'].get('email', 'NO EMAIL')}")
                _logger.info(f"=== END DEBUG LOAN DATA ===")
                
                loan_contract_ids = []
                _logger.info(f"=== CREATING {len(loans)} LOAN RECORDS ===")
                for i, loan in enumerate(loans):
                    _logger.info(f"Processing loan {i+1}/{len(loans)}: {loan.get('id', 'NO ID')}")
                    result = self._create_loan_record(env, loan)
                    if result:
                        loan_contract_ids.append(loan.get('id'))
                        _logger.info(f"✅ Loan {loan.get('id')} created successfully")
                    else:
                        _logger.error(f"❌ Failed to create loan {loan.get('id')}")
                
                # Đánh dấu loans đã sync
                if loan_contract_ids:
                    _logger.info(f"=== MARKING {len(loan_contract_ids)} LOANS AS SYNCED ===")
                    self.mark_loans_synced(loan_contract_ids)
                    _logger.info("✅ Loans marked as synced successfully")
                else:
                    _logger.warning("⚠️ No loans to mark as synced")
            else:
                _logger.warning("⚠️ No loans received from API")
            
            # Đồng bộ investor users độc lập với investments
            _logger.info("=== FETCHING INVESTORS (USERS) FROM API ===")
            investors_users = self.get_investors(limit=500, force_sync=True)
            _logger.info(f"Total investor users received: {len(investors_users)}")
            if investors_users:
                try:
                    _logger.info(f"Sample investor user: {investors_users[0]}")
                except Exception:
                    pass
            if investors_users:
                created_cnt = 0
                updated_cnt = 0
                for user in investors_users:
                    res = self._upsert_investor_user(env, user)
                    if res == 'created':
                        created_cnt += 1
                    elif res == 'updated':
                        updated_cnt += 1
                _logger.info(f"✅ Investors upserted - created: {created_cnt}, updated: {updated_cnt}")
            else:
                _logger.warning("⚠️ No investor users received from API")
            
            # Đồng bộ investments
            _logger.info("=== FETCHING INVESTMENTS FROM API ===")
            investments = self.get_investments(limit=100, force_sync=True)
            _logger.info(f"Total investments received: {len(investments)}")
            
            if investments:
                investment_contract_ids = []
                _logger.info(f"=== CREATING {len(investments)} INVESTMENT RECORDS ===")
                for i, investment in enumerate(investments):
                    _logger.info(f"Processing investment {i+1}/{len(investments)}: {investment.get('id', 'NO ID')}")
                    result = self._create_investment_record(env, investment)
                    if result:
                        investment_contract_ids.append(investment.get('id'))
                        _logger.info(f"✅ Investment {investment.get('id')} created successfully")
                    else:
                        _logger.error(f"❌ Failed to create investment {investment.get('id')}")
                
                # Đánh dấu investments đã sync
                if investment_contract_ids:
                    _logger.info(f"=== MARKING {len(investment_contract_ids)} INVESTMENTS AS SYNCED ===")
                    self.mark_investments_synced(investment_contract_ids)
                    _logger.info("✅ Investments marked as synced successfully")
                else:
                    _logger.warning("⚠️ No investments to mark as synced")
            else:
                _logger.warning("⚠️ No investments received from API")
            
            _logger.info("=== SYNC ALL DATA COMPLETED SUCCESSFULLY ===")
            return True
        except Exception as e:
            _logger.error(f"❌ Error syncing all data: {e}")
            import traceback
            _logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def _upsert_investor_user(self, env, user_data):
        """Tạo/cập nhật investor từ dữ liệu user độc lập với investments"""
        try:
            info = user_data or {}
            # Hỗ trợ nhiều schema detail
            detail = (
                info.get('detail')
                or info.get('details')
                or info.get('user_detail')
                or info.get('userDetails')
                or info.get('profile')
                or {}
            )
            phone = info.get('phone') or detail.get('phone')
            email = info.get('email') or detail.get('email')
            name = info.get('name') or detail.get('name') or ''
            # một số API có thể đặt city/job ở profile
            city = detail.get('city') or info.get('city') or detail.get('location')
            job = detail.get('job') or info.get('job') or detail.get('occupation') or info.get('occupation')
            if not name or str(name).lower() == 'unknown':
                name = f"Nhà đầu tư {phone or (email or 'N/A')}"

            if not phone and not email:
                _logger.warning("⚠️ Skip investor user: missing both phone and email")
                return 'skipped'

            domain = [('phone', '=', phone)] if phone else [('email', '=', email)]
            existing = env['p2p.investor'].search(domain)

            vals = {}
            # Chỉ set các field khi có dữ liệu
            if name:
                vals['name'] = name
            if phone:
                vals['phone'] = phone
            if email and str(email).lower() != 'unknown':
                vals['email'] = email
            if info.get('status'):
                vals['status'] = info.get('status')
            # detail mở rộng
            if detail.get('identity_card'):
                vals['identity_card'] = detail.get('identity_card')
            if detail.get('address') or info.get('address'):
                vals['address'] = detail.get('address') or info.get('address')
            if detail.get('date_of_birth'):
                vals['date_of_birth'] = detail.get('date_of_birth')
            if detail.get('monthly_income') is not None:
                vals['monthly_income'] = detail.get('monthly_income')
            if detail.get('risk_tolerance'):
                vals['risk_tolerance'] = detail.get('risk_tolerance')
            if detail.get('investment_capacity') is not None:
                vals['investment_capacity'] = detail.get('investment_capacity')
            # map city, job_title nếu có
            if city:
                vals['city'] = city
            if job:
                vals['job_title'] = job

            if existing:
                # Chỉ cập nhật field còn thiếu để tránh phá dữ liệu hiện có
                updates = {}
                for key, value in vals.items():
                    if not getattr(existing[0], key) and value not in (None, ''):
                        updates[key] = value
                if updates:
                    _logger.info(f"Updating investor {existing[0].id} with: {updates}")
                    existing[0].write(updates)
                    return 'updated'
                return 'skipped'
            else:
                # Tạo mới
                if phone:
                    vals['user_id'] = f"investor_{phone}"
                elif email:
                    vals['user_id'] = f"investor_{email}"
                else:
                    vals['user_id'] = "investor_unknown"
                vals['status'] = vals.get('status') or 'active'
                _logger.info(f"Creating investor with: {vals}")
                env['p2p.investor'].create(vals)
                return 'created'
        except Exception as e:
            _logger.error(f"Error upserting investor user: {e}")
            return 'error'

    def test_create_borrower(self, env):
        """Test tạo 1 borrower record"""
        try:
            test_borrower = env['p2p.borrower'].create({
                'name': 'Test Borrower',
                'email': 'test@example.com',
                'phone': '0123456789',
                'user_id': 'test_123',
                'status': 'active',
            })
            return test_borrower
        except Exception as e:
            return None

    def debug_api_response(self):
        """Debug API response để xem dữ liệu thực tế"""
        try:
            _logger.info("=== DEBUG API RESPONSE START ===")
            
            # Test loans API
            _logger.info(f"Testing loans API: {self.base_url}{self.api_endpoints['loans']}")
            loans_response = self._make_api_request(self.api_endpoints['loans'])
            if loans_response:
                _logger.info("=== LOANS API RESPONSE ===")
                _logger.info(f"Response structure: {loans_response}")
                _logger.info(f"Total loans: {loans_response.get('total', 0)}")
                if loans_response.get('loans'):
                    first_loan = loans_response['loans'][0]
                    _logger.info(f"First loan: {first_loan}")
                    if first_loan.get('borrower'):
                        _logger.info(f"Borrower data: {first_loan['borrower']}")
                        _logger.info(f"Borrower name: {first_loan['borrower'].get('name', 'NO NAME')}")
                        _logger.info(f"Borrower email: {first_loan['borrower'].get('email', 'NO EMAIL')}")
                else:
                    _logger.warning("⚠️ No loans in API response")
            else:
                _logger.error("❌ Failed to get loans from API")
            
            # Test investments API
            _logger.info(f"Testing investments API: {self.base_url}{self.api_endpoints['investments']}")
            investments_response = self._make_api_request(self.api_endpoints['investments'])
            if investments_response:
                _logger.info("=== INVESTMENTS API RESPONSE ===")
                _logger.info(f"Response structure: {investments_response}")
                _logger.info(f"Total investments: {investments_response.get('total', 0)}")
                if investments_response.get('investments'):
                    first_investment = investments_response['investments'][0]
                    _logger.info(f"First investment: {first_investment}")
                    if first_investment.get('lender'):
                        _logger.info(f"Lender data: {first_investment['lender']}")
                        _logger.info(f"Lender name: {first_investment['lender'].get('name', 'NO NAME')}")
                        _logger.info(f"Lender email: {first_investment['lender'].get('email', 'NO EMAIL')}")
                else:
                    _logger.warning("⚠️ No investments in API response")
            else:
                _logger.error("❌ Failed to get investments from API")
            
            _logger.info("=== DEBUG API RESPONSE END ===")
            return True
        except Exception as e:
            _logger.error(f"Debug API response error: {e}")
            import traceback
            _logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def _create_loan_record(self, env, loan_data):
        """Tạo loan record trong Odoo từ API data"""
        try:
            # Check if loan already exists
            existing = env['p2p.loan'].search([('user_id', '=', str(loan_data.get('id', '')))])
            if existing:
                return existing

            # Extract data from API structure
            name = loan_data.get('id', 'Unknown Loan')
            amount = loan_data.get('amount', 0)
            interest_rate = loan_data.get('interest_rate', 0)
            term_months = loan_data.get('term_months', 0)
            
            # Debug borrower data
            _logger.info(f"=== DEBUG BORROWER DATA FOR LOAN {name} ===")
            _logger.info(f"Loan data: {loan_data}")
            if loan_data.get('borrower'):
                _logger.info(f"Borrower data: {loan_data['borrower']}")
                _logger.info(f"Borrower name: {loan_data['borrower'].get('name', 'NO NAME')}")
                _logger.info(f"Borrower email: {loan_data['borrower'].get('email', 'NO EMAIL')}")
                _logger.info(f"Borrower phone: {loan_data['borrower'].get('phone', 'NO PHONE')}")
            else:
                _logger.warning("⚠️ No borrower data in loan")
            _logger.info(f"=== END DEBUG BORROWER DATA ===")
            
            # Find or create borrower với thông tin từ UserDetails
            borrower_id = None
            borrower_info = loan_data.get('borrower', {}) or {}
            # Hỗ trợ nhiều key detail khác nhau: detail / details / user_detail / userDetails
            borrower_detail = (
                borrower_info.get('detail')
                or borrower_info.get('details')
                or borrower_info.get('user_detail')
                or borrower_info.get('userDetails')
                or {}
            )
            borrower_phone = borrower_info.get('phone') or borrower_detail.get('phone')

            if borrower_phone:
                borrower = env['p2p.borrower'].search([('phone', '=', borrower_phone)])
                if borrower:
                    # Cập nhật các trường còn thiếu nếu API có
                    existing = borrower[0]
                    updates = {}
                    if not existing.email and (borrower_info.get('email') or borrower_detail.get('email')):
                        updates['email'] = borrower_info.get('email') or borrower_detail.get('email')
                    if not existing.name and (borrower_info.get('name') or borrower_detail.get('name')):
                        updates['name'] = borrower_info.get('name') or borrower_detail.get('name')
                    if not existing.identity_card and borrower_detail.get('identity_card'):
                        updates['identity_card'] = borrower_detail.get('identity_card')
                    if not existing.address and (borrower_detail.get('address') or borrower_info.get('address')):
                        updates['address'] = borrower_detail.get('address') or borrower_info.get('address')
                    if not existing.date_of_birth and borrower_detail.get('date_of_birth'):
                        updates['date_of_birth'] = borrower_detail.get('date_of_birth')
                    if not existing.monthly_income and borrower_detail.get('monthly_income'):
                        updates['monthly_income'] = borrower_detail.get('monthly_income')
                    if not existing.credit_score and borrower_detail.get('credit_score'):
                        updates['credit_score'] = borrower_detail.get('credit_score')
                    if not existing.employment_status and borrower_detail.get('employment_status'):
                        updates['employment_status'] = borrower_detail.get('employment_status')
                    if updates:
                        existing.write(updates)
                    borrower_id = existing.id
                    _logger.info(f"✅ Found existing borrower: {existing.name}")
                else:
                    # Lấy thông tin user từ API response (đã được populate)
                    borrower_name = borrower_info.get('name') or borrower_detail.get('name') or ''
                    borrower_email = borrower_info.get('email') or borrower_detail.get('email') or ''
                    if not borrower_name or borrower_name == 'Unknown':
                        borrower_name = f"Người vay {borrower_phone}"

                    vals = {
                        'name': borrower_name,
                        'phone': borrower_phone or '',
                        'email': '' if borrower_email == 'Unknown' else borrower_email,
                        'user_id': f"borrower_{borrower_phone or ''}",
                        'status': 'active',
                    }
                    # Thêm detail nếu có
                    if borrower_detail.get('identity_card'):
                        vals['identity_card'] = borrower_detail.get('identity_card')
                    if borrower_detail.get('address') or borrower_info.get('address'):
                        vals['address'] = borrower_detail.get('address') or borrower_info.get('address')
                    if borrower_detail.get('date_of_birth'):
                        vals['date_of_birth'] = borrower_detail.get('date_of_birth')
                    if borrower_detail.get('monthly_income') is not None:
                        vals['monthly_income'] = borrower_detail.get('monthly_income')
                    if borrower_detail.get('credit_score') is not None:
                        vals['credit_score'] = borrower_detail.get('credit_score')
                    if borrower_detail.get('employment_status'):
                        vals['employment_status'] = borrower_detail.get('employment_status')

                    _logger.info(f"Creating new borrower: {borrower_name}, {vals.get('email','')}, {borrower_phone}")
                    borrower = env['p2p.borrower'].create(vals)
                    borrower_id = borrower.id
                    _logger.info(f"✅ Created new borrower: {borrower.name}")
            else:
                _logger.warning("⚠️ No borrower phone found")
            
            loan = env['p2p.loan'].create({
                'name': name,
                'amount': float(amount) if amount else 0,
                'interest_rate': float(interest_rate) if interest_rate else 0,
                'term_months': int(term_months) if term_months else 0,
                'status': 'active',
                'user_id': str(loan_data.get('id', '')),
                'borrower_id': borrower_id,
            })
            return loan
        except Exception as e:
            _logger.error(f"Error creating loan: {e}")
            import traceback
            _logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def _create_investment_record(self, env, investment_data):
        """Tạo investment record trong Odoo từ API data"""
        try:
            # Check if investment already exists
            existing = env['p2p.investment'].search([('user_id', '=', str(investment_data.get('id', '')))])
            if existing:
                # Cập nhật các trường info nếu trước đó chưa có/đang là 0
                updates = {}
                info_obj = (investment_data.get('info', {}) or {})
                top_monthly_income = investment_data.get('monthly_income')
                top_monthly_profit = investment_data.get('monthly_profit')
                if (not existing[0].monthly_income or existing[0].monthly_income == 0) and (top_monthly_income is not None or info_obj.get('monthlyIncome') is not None):
                    updates['monthly_income'] = float(top_monthly_income if top_monthly_income is not None else info_obj.get('monthlyIncome') or 0)
                if (not existing[0].monthly_profit or existing[0].monthly_profit == 0) and (top_monthly_profit is not None or info_obj.get('monthlyProfit') is not None):
                    updates['monthly_profit'] = float(top_monthly_profit if top_monthly_profit is not None else info_obj.get('monthlyProfit') or 0)
                if (not existing[0].monthly_principal_income or existing[0].monthly_principal_income == 0) and info_obj.get('monthlyPrincipalIncome') is not None:
                    updates['monthly_principal_income'] = float(info_obj.get('monthlyPrincipalIncome') or 0)
                if (not existing[0].monthly_interest_income or existing[0].monthly_interest_income == 0) and info_obj.get('monthlyInterestIncome') is not None:
                    updates['monthly_interest_income'] = float(info_obj.get('monthlyInterestIncome') or 0)
                if (not existing[0].entirely_profit or existing[0].entirely_profit == 0) and info_obj.get('entirelyProfit') is not None:
                    updates['entirely_profit'] = float(info_obj.get('entirelyProfit') or 0)
                if (not existing[0].num_notes or existing[0].num_notes == 0) and info_obj.get('numNotes') is not None:
                    updates['num_notes'] = int(info_obj.get('numNotes') or 0)
                if (not existing[0].service_fee or existing[0].service_fee == 0) and info_obj.get('serviceFee') is not None:
                    updates['service_fee'] = float(info_obj.get('serviceFee') or 0)
                if updates:
                    existing[0].write(updates)
                return existing
            
            # Extract data from API structure
            name = investment_data.get('id', 'Unknown Investment')
            amount = investment_data.get('amount', 0)
            interest_rate = investment_data.get('interest_rate', 0)
            term_months = investment_data.get('term_months', 0)
            
            # Find or create investor với thông tin chi tiết
            investor_id = None
            lender_info = investment_data.get('lender', {}) or {}
            lender_detail = (
                lender_info.get('detail')
                or lender_info.get('details')
                or lender_info.get('user_detail')
                or lender_info.get('userDetails')
                or {}
            )
            lender_phone = lender_info.get('phone') or lender_detail.get('phone')
            lender_email = (
                lender_info.get('email')
                or lender_detail.get('email')
                or investment_data.get('lender_email')
                or investment_data.get('email')
            )
            lender_name = (
                lender_info.get('name')
                or lender_detail.get('name')
                or investment_data.get('lender_name')
                or investment_data.get('name')
                or ''
            )

            if lender_phone:
                investor = env['p2p.investor'].search([('phone', '=', lender_phone)])
                if investor:
                    existing = investor[0]
                    updates = {}
                    if not existing.email and lender_email:
                        updates['email'] = lender_email
                    if not existing.name and lender_name:
                        updates['name'] = lender_name
                    if not existing.identity_card and lender_detail.get('identity_card'):
                        updates['identity_card'] = lender_detail.get('identity_card')
                    if not existing.address and (lender_detail.get('address') or lender_info.get('address')):
                        updates['address'] = lender_detail.get('address') or lender_info.get('address')
                    if not existing.date_of_birth and lender_detail.get('date_of_birth'):
                        updates['date_of_birth'] = lender_detail.get('date_of_birth')
                    if not existing.monthly_income and lender_detail.get('monthly_income'):
                        updates['monthly_income'] = lender_detail.get('monthly_income')
                    if updates:
                        existing.write(updates)
                    investor_id = existing.id
                else:
                    investor_name = lender_name or ''
                    if not investor_name or str(investor_name).lower() == 'unknown':
                        investor_name = f"Nhà đầu tư {lender_phone}"

                    vals = {
                        'name': investor_name,
                        'phone': lender_phone or '',
                        'email': '' if (lender_email and str(lender_email).lower() == 'unknown') else (lender_email or ''),
                        'user_id': f"investor_{lender_phone or ''}",
                        'status': 'active',
                    }
                    # Thêm detail nếu có
                    if lender_detail.get('identity_card'):
                        vals['identity_card'] = lender_detail.get('identity_card')
                    if lender_detail.get('address') or lender_info.get('address'):
                        vals['address'] = lender_detail.get('address') or lender_info.get('address')
                    if lender_detail.get('date_of_birth'):
                        vals['date_of_birth'] = lender_detail.get('date_of_birth')
                    if lender_detail.get('monthly_income') is not None:
                        vals['monthly_income'] = lender_detail.get('monthly_income')
                    if lender_detail.get('risk_tolerance'):
                        vals['risk_tolerance'] = lender_detail.get('risk_tolerance')
                    if lender_detail.get('investment_capacity') is not None:
                        vals['investment_capacity'] = lender_detail.get('investment_capacity')

                    investor = env['p2p.investor'].create(vals)
                    investor_id = investor.id
            
            investment = env['p2p.investment'].create({
                'name': name,
                'amount': float(amount) if amount else 0,
                'interest_rate': float(interest_rate) if interest_rate else 0,
                'term_months': int(term_months) if term_months else 0,
                'status': 'active',
                'user_id': str(investment_data.get('id', '')),
                'investor_id': investor_id,
                # map info từ API nếu có
                'monthly_income': investment_data.get('monthly_income', 0) or (investment_data.get('info', {}) or {}).get('monthlyIncome', 0),
                'monthly_profit': investment_data.get('monthly_profit', 0) or (investment_data.get('info', {}) or {}).get('monthlyProfit', 0),
                'monthly_principal_income': (investment_data.get('info', {}) or {}).get('monthlyPrincipalIncome', 0),
                'monthly_interest_income': (investment_data.get('info', {}) or {}).get('monthlyInterestIncome', 0),
                'entirely_profit': (investment_data.get('info', {}) or {}).get('entirelyProfit', 0),
                'num_notes': (investment_data.get('info', {}) or {}).get('numNotes', 0),
                'service_fee': (investment_data.get('info', {}) or {}).get('serviceFee', 0),
            })
            return investment
        except Exception as e:
            return None

    def test_connection(self):
        """Test kết nối API"""
        try:
            # Test basic connection
            try:
                response = requests.get(f"{self.base_url}/", timeout=5)
                if response.status_code != 200:
                    return False
            except Exception:
                return False
            
            # Test available endpoints
            test_endpoints = [
                '/api/loan/odoo/export/loans',
                '/api/loan/odoo/export/investments',
                '/api/loan/odoo/export/waiting-rooms',
                '/api/loan/odoo/mark/loans-synced',
                '/api/loan/odoo/mark/investments-synced',
                '/api/loan/odoo/mark/waiting-rooms-synced'
            ]
            
            working_endpoints = []
            for endpoint in test_endpoints:
                try:
                    response = requests.get(f"{self.base_url}{endpoint}", timeout=3)
                    if response.status_code == 200:
                        working_endpoints.append(endpoint)
                except Exception:
                    pass
            
            return len(working_endpoints) > 0
            
        except Exception:
            return False

    def clear_all_data(self, env):
        """Xóa toàn bộ dữ liệu P2P"""
        try:
            _logger.info("=== CLEARING ALL P2P DATA ===")
            
            # Xóa loans
            loans = env['p2p.loan'].search([])
            if loans:
                _logger.info(f"Deleting {len(loans)} loans")
                loans.unlink()
                _logger.info("✅ Loans deleted")
            
            # Xóa investments
            investments = env['p2p.investment'].search([])
            if investments:
                _logger.info(f"Deleting {len(investments)} investments")
                investments.unlink()
                _logger.info("✅ Investments deleted")
            
            # Xóa borrowers
            borrowers = env['p2p.borrower'].search([])
            if borrowers:
                _logger.info(f"Deleting {len(borrowers)} borrowers")
                borrowers.unlink()
                _logger.info("✅ Borrowers deleted")
            
            # Xóa investors
            investors = env['p2p.investor'].search([])
            if investors:
                _logger.info(f"Deleting {len(investors)} investors")
                investors.unlink()
                _logger.info("✅ Investors deleted")
            
            _logger.info("=== ALL P2P DATA CLEARED ===")
            return True
        except Exception as e:
            _logger.error(f"Error clearing data: {e}")
            return False