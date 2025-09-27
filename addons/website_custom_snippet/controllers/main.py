from odoo import http
from odoo.http import request
import logging
_logger = logging.getLogger(__name__)

class WebsiteLoanController(http.Controller):
    @http.route(['/loans'], type='http', auth='public', website=True)
    def loan_list(self, **kwargs):
        # Lấy dữ liệu từ P2P Lending Core bridge model
        loan_records = request.env['p2p.loan'].sudo().search([], limit=10)
        _logger.info(f"[DEBUG] Loans found: {len(loan_records)}")
        
        # Map loan data to match template expectations
        mapped_loans = []
        for loan in loan_records:
            loan_dict = {
                'id': loan.id,
                'name': loan.name or f"Loan-{loan.id}",
                'contractId': loan.user_id or loan.name or f"LOAN_{loan.id}",
                'amount': loan.amount,
                'capital': loan.amount,  # Map amount to capital for template compatibility
                'interest_rate': loan.interest_rate,
                'term_months': loan.term_months,
                'borrower_id': loan.borrower_id.name if loan.borrower_id else 'Unknown Borrower',
                'create_date': loan.create_date,
                'created_date': loan.create_date,  # Map for template compatibility
                'status': loan.status,
            }
            # Convert dict to object so template can access with dot notation
            mapped_loan = type('LoanData', (), loan_dict)()
            mapped_loans.append(mapped_loan)
            _logger.info(f"[DEBUG] Mapped Loan: {mapped_loan.contractId} - {mapped_loan.capital} - {mapped_loan.status}")
        
        if not mapped_loans:
            _logger.warning("[DEBUG] Không có khoản vay nào được tìm thấy!")
            
        return request.render('website_custom_snippet.loan_list_template', {
            'loans': mapped_loans
        })