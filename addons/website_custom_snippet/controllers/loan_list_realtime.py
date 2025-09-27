from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class LoanListRealtimeController(http.Controller):
    @http.route(['/loan_list/realtime', '/loan_list/realtime/'], type='http', auth='public', website=True, csrf=False)
    def loan_list_realtime(self, **kwargs):
        _logger.info("[loan_list_realtime] Rendering HTML partial for loan list")
        loans_records = request.env['p2p.loan'].sudo().search([], limit=10)
        _logger.info("[loan_list_realtime] Loans fetched: %s", len(loans_records))
        
        # Map loan data to match template expectations
        mapped_loans = []
        for loan in loans_records:
            # Create a simple object with all the required fields
            loan_dict = {
                'id': loan.id,
                'name': loan.name or f"Loan-{loan.id}",
                'contractId': loan.user_id or loan.name or f"LOAN_{loan.id}",
                'loan_id': loan.user_id or loan.name or f"LOAN_{loan.id}",  # Fallback for template
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
        
        # Render only the template content without wrapping website layout
        html = request.env['ir.ui.view']._render_template(
            'website_custom_snippet.loan_list_table_partial', {'loans': mapped_loans}
        )
        return request.make_response(html, headers=[('Content-Type', 'text/html; charset=utf-8')])

    @http.route(['/loan_list/realtime/data', '/loan_list/realtime/data/'], type='json', auth='public', website=True, csrf=False)
    def loan_list_realtime_json(self, **kwargs):
        """JSON endpoint for loan list data with proper field mapping"""
        _logger.info("[loan_list_realtime_json] Returning JSON for loan list")
        loans = request.env['p2p.loan'].sudo().search([], limit=10)
        return {
            'count': len(loans),
            'items': [
                {
                    'name': l.name or f"Loan-{l.id}",
                    'contractId': l.user_id or l.name or f"LOAN_{l.id}",  # Map to contractId for template compatibility
                    'borrower': l.borrower_id.name if l.borrower_id else 'Unknown',
                    'amount': l.amount,
                    'capital': l.amount,  # Map amount to capital for template compatibility  
                    'interest_rate': l.interest_rate,
                    'term': l.term_months,
                    'term_months': l.term_months,
                    'start_date': str(l.create_date) if l.create_date else None,
                    'created_date': str(l.create_date) if l.create_date else None,  # Map for template compatibility
                }
                for l in loans
            ],
        }

    @http.route(['/loan_list/realtime/ping'], type='http', auth='public', website=False, csrf=False)
    def loan_list_realtime_ping(self):
        return http.Response("OK", status=200, content_type='text/plain')
