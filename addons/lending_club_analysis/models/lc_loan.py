# -*- coding: utf-8 -*-
from odoo import api, fields, models


class LcLoan(models.Model):
    _name = "lc.loan"
    _description = "Lending Club Loan Record"
    _rec_name = "loan_id"

    # Các trường phổ biến của Lending Club dataset (rút gọn)
    loan_id = fields.Char(string="Loan ID", required=True, index=True)
    issue_d = fields.Date(string="Issue Date")
    term = fields.Char(string="Term")  # e.g. 36 months
    int_rate = fields.Float(string="Interest Rate (%)")
    installment = fields.Float(string="Installment")
    grade = fields.Selection(
        [(g, g) for g in list("ABCDEFG")],
        string="Grade",
    )
    sub_grade = fields.Char(string="Sub Grade")

    emp_length = fields.Char(string="Emp Length (years)")
    home_ownership = fields.Selection(
        [
            ("RENT", "RENT"),
            ("MORTGAGE", "MORTGAGE"),
            ("OWN", "OWN"),
            ("OTHER", "OTHER"),
        ],
        string="Home Ownership",
        default="RENT",
    )
    annual_inc = fields.Float(string="Annual Income")

    dti = fields.Float(string="DTI")
    delinq_2yrs = fields.Float(string="Delinq (2yrs)")
    pub_rec = fields.Float(string="Public Records")

    fico_range_low = fields.Float(string="FICO Low")
    fico_range_high = fields.Float(string="FICO High")

    purpose = fields.Char(string="Purpose")
    addr_state = fields.Char(string="State")

    loan_amnt = fields.Float(string="Loan Amount")
    funded_amnt = fields.Float(string="Funded Amount")
    total_pymnt = fields.Float(string="Total Payment")
    recoveries = fields.Float(string="Recoveries")

    # Thông tin mở rộng từ Data Dictionary
    lc_listing_id = fields.Char(string="LC Listing ID", index=True)
    member_id = fields.Char(string="Member ID")
    application_type = fields.Selection(
        [("INDIVIDUAL", "INDIVIDUAL"), ("JOINT", "JOINT")], string="Application Type"
    )
    verification_status = fields.Selection(
        [
            ("Verified", "Verified"),
            ("Not Verified", "Not Verified"),
            ("Source Verified", "Source Verified"),
        ],
        string="Verification Status",
    )
    is_inc_v = fields.Char(string="Income Verification (raw)")
    emp_title = fields.Char(string="Employment Title")
    zip_code = fields.Char(string="ZIP Code (first 3)")

    earliest_cr_line = fields.Date(string="Earliest Credit Line")
    open_acc = fields.Float(string="Open Accounts")
    total_acc = fields.Float(string="Total Accounts")
    revol_bal = fields.Float(string="Revolving Balance")
    revol_util = fields.Float(string="Revolving Utilization (%)")

    loan_status = fields.Char(string="Loan Status")
    initial_list_status = fields.Selection([("W", "W"), ("F", "F")], string="Initial List Status")
    policy_code = fields.Float(string="Policy Code")

    last_pymnt_d = fields.Date(string="Last Payment Date")
    last_pymnt_amnt = fields.Float(string="Last Payment Amount")
    next_pymnt_d = fields.Date(string="Next Payment Date")
    last_credit_pull_d = fields.Date(string="Last Credit Pull Date")

    funded_amnt_inv = fields.Float(string="Funded Amount (Investors)")
    out_prncp = fields.Float(string="Outstanding Principal")
    out_prncp_inv = fields.Float(string="Outstanding Principal (Investors)")

    total_pymnt_inv = fields.Float(string="Total Payment (Investors)")
    total_rec_prncp = fields.Float(string="Total Received Principal")
    total_rec_int = fields.Float(string="Total Received Interest")
    total_rec_late_fee = fields.Float(string="Total Received Late Fee")

    pymnt_plan = fields.Char(string="Payment Plan")
    collection_recovery_fee = fields.Float(string="Collection Recovery Fee")
    collections_12_mths_ex_med = fields.Float(string="Collections 12m (ex medical)")

    mths_since_last_delinq = fields.Float(string="Months Since Last Delinquency")
    mths_since_last_record = fields.Float(string="Months Since Last Public Record")
    mths_since_last_major_derog = fields.Float(string="Months Since Last Major Derog")

    open_acc_6m = fields.Float(string="Open Accounts 6m")
    open_il_6m = fields.Float(string="Open Installment 6m")
    open_il_12m = fields.Float(string="Open Installment 12m")
    open_il_24m = fields.Float(string="Open Installment 24m")
    mths_since_rcnt_il = fields.Float(string="Months Since Recent Installment")

    total_bal_il = fields.Float(string="Total Balance Installment")
    il_util = fields.Float(string="Installment Utilization (%)")

    open_rv_12m = fields.Float(string="Open Revolving 12m")
    open_rv_24m = fields.Float(string="Open Revolving 24m")
    max_bal_bc = fields.Float(string="Max Balance Bankcard")
    all_util = fields.Float(string="All Utilization (%)")
    total_rev_hi_lim = fields.Float(string="Total Revolving High Credit/Limit")

    inq_last_6mths = fields.Float(string="Inquiries Last 6m")
    inq_fi = fields.Float(string="Finance Inquiries")
    inq_last_12m = fields.Float(string="Inquiries Last 12m")

    acc_now_delinq = fields.Float(string="Accounts Now Delinquent")
    tot_coll_amt = fields.Float(string="Total Collection Amount")
    tot_cur_bal = fields.Float(string="Total Current Balance")
    total_cu_tl = fields.Float(string="Total Credit Union Trades")

    title = fields.Char(string="Title")
    desc = fields.Text(string="Description")
    url = fields.Char(string="URL")

    # Joint application fields
    annual_inc_joint = fields.Float(string="Annual Income (Joint)")
    dti_joint = fields.Float(string="DTI (Joint)")
    verified_status_joint = fields.Char(string="Verification Status (Joint)")

    last_fico_range_low = fields.Float(string="Last FICO Low")
    last_fico_range_high = fields.Float(string="Last FICO High")


    # Trường phân tích nội bộ
    score = fields.Float(string="Credit Score (Rule-based)", compute="_compute_score", store=True)
    grade_rb = fields.Selection(
        [(g, g) for g in list("ABCDEFG")],
        string="Grade (Rule-based)",
        compute="_compute_score",
        store=True,
    )

    @api.depends(
        "dti",
        "fico_range_low",
        "fico_range_high",
        "annual_inc",
        "emp_length",
        "home_ownership",
        "delinq_2yrs",
        "pub_rec",
    )
    def _compute_score(self):
        for rec in self:
            score = 0
            
            # Simple scoring based on FICO score (60% weight)
            if rec.fico_range_high >= 800:
                score += 60
            elif rec.fico_range_high >= 740:
                score += 50
            elif rec.fico_range_high >= 670:
                score += 40
            elif rec.fico_range_high >= 580:
                score += 30
            else:
                score += 20
                
            # DTI impact (20% weight)
            if rec.dti <= 20:
                score += 20
            elif rec.dti <= 35:
                score += 15
            elif rec.dti <= 50:
                score += 10
            else:
                score += 5
                
            # Home ownership (10% weight)
            if rec.home_ownership == 'OWN':
                score += 10
            elif rec.home_ownership == 'MORTGAGE':
                score += 8
            elif rec.home_ownership == 'RENT':
                score += 5
            else:
                score += 3
                
            # Delinquencies (10% weight)
            if rec.delinq_2yrs == 0 and rec.pub_rec == 0:
                score += 10
            elif rec.delinq_2yrs <= 1 and rec.pub_rec == 0:
                score += 7
            else:
                score += 3
                
            # Cap the score at 100
            score = min(score, 100)
            
            # Set the score and grade
            rec.score = score
            
            # Simple grade mapping based on score
            if score >= 90:
                rec.grade_rb = 'A'
            elif score >= 80:
                rec.grade_rb = 'B'
            elif score >= 70:
                rec.grade_rb = 'C'
            elif score >= 60:
                rec.grade_rb = 'D'
            elif score >= 50:
                rec.grade_rb = 'E'
            else:
                rec.grade_rb = 'F'

    # Tích hợp với P2P Lending
    p2p_loan_id = fields.Many2one('p2p.loan', string="P2P Loan", readonly=True,
                                  help="Khoản vay P2P được tạo từ lịch sử khoản vay Lending Club này")

    def action_create_p2p_loan(self):
        """Tạo khoản vay P2P từ lịch sử khoản vay Lending Club"""
        self.ensure_one()

        if self.p2p_loan_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Khoản vay P2P',
                'res_model': 'p2p.loan',
                'res_id': self.p2p_loan_id.id,
                'view_mode': 'form',
                'target': 'current',
            }

        # Chuyển đổi lịch sử khoản vay
        p2p_vals = self._prepare_p2p_loan_data()

        # Tạo khoản vay P2P
        p2p_loan = self.env['p2p.loan'].create(p2p_vals)

        # Liên kết
        self.p2p_loan_id = p2p_loan.id

        return {
            'type': 'ir.actions.act_window',
            'name': 'Khoản vay P2P đã tạo',
            'res_model': 'p2p.loan',
            'res_id': p2p_loan.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _prepare_p2p_loan_data(self):
        """Chuẩn bị lịch sử khoản vay để tạo khoản vay P2P"""
        # Chuyển đổi term từ text sang số tháng
        term_months = 36  # mặc định
        if self.term:
            import re
            match = re.search(r'(\d+)', str(self.term))
            if match:
                term_months = int(match.group(1))

        # Tạo hoặc tìm borrower
        borrower_name = f'Lending Club Borrower {self.loan_id}'
        borrower = self.env['p2p.borrower'].search([('name', '=', borrower_name)], limit=1)
        if not borrower:
            # Tạo partner trước
            partner = self.env['res.partner'].create({
                'name': borrower_name,
                'email': f'lc_{self.loan_id}@lendingclub.local',
                'phone': '0000000000',  # Placeholder
            })

            # Map home_ownership
            home_ownership_mapping = {
                'RENT': 'rent',
                'MORTGAGE': 'mortgage',
                'OWN': 'own',
                'OTHER': 'other',
            }
            p2p_home_ownership = home_ownership_mapping.get(self.home_ownership, 'rent')

            borrower = self.env['p2p.borrower'].create({
                'name': borrower_name,
                'partner_id': partner.id,
                'date_of_birth': '1990-01-01',  # Placeholder
                'gender': 'other',  # Placeholder
                'phone': '0000000000',  # Placeholder
                'email': f'lc_{self.loan_id}@lendingclub.local',
                'address': 'Unknown',  # Placeholder
                'city': 'Unknown',  # Placeholder
                'district': 'Unknown',  # Placeholder
                'ward': 'Unknown',  # Placeholder
                'employment_status': 'employed',  # Placeholder
                'monthly_income': (self.annual_inc or 0) / 12,
                'home_ownership': p2p_home_ownership,
                'delinquent_accounts': int(self.delinq_2yrs or 0),
                'public_records': int(self.pub_rec or 0),
            })

        # Map purpose to P2P purpose
        purpose_mapping = {
            'debt_consolidation': 'debt_consolidation',
            'home_improvement': 'home_improvement',
            'business': 'business',
            'education': 'education',
            'medical': 'medical',
            'car': 'other',
            'house': 'home_improvement',
            'vacation': 'other',
            'moving': 'other',
            'renewable_energy': 'other',
            'wedding': 'other',
            'major_purchase': 'other',
            'small_business': 'business',
            'credit_card': 'debt_consolidation',
        }
        p2p_purpose = purpose_mapping.get(self.purpose, 'other')

        return {
            'name': self.loan_id or f'LC-{self.id}',
            'borrower_id': borrower.id,
            'amount': self.loan_amnt or 0,
            'interest_rate': self.int_rate or 0,
            'term': term_months,
            'purpose': p2p_purpose,
            'state': 'draft',  # Always start as draft, let wizard decide
        }
