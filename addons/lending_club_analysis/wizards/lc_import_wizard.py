# -*- coding: utf-8 -*-
import base64
import csv
import io
import re
import datetime as dt
from odoo import api, fields, models, _
from odoo.exceptions import UserError

try:
    from openpyxl import load_workbook  # type: ignore
except Exception:  # pragma: no cover
    load_workbook = None

LC_FIELDS = [
    # Core fields
    "loan_id","issue_d","term","int_rate","installment","grade","sub_grade",
    "emp_length","home_ownership","annual_inc","dti","delinq_2yrs","pub_rec",
    "fico_range_low","fico_range_high","purpose","addr_state","loan_amnt",
    "funded_amnt","total_pymnt","recoveries",
    # Extended dictionary
    "desc","lc_listing_id","member_id","application_type","verification_status","is_inc_v",
    "emp_title","zip_code","earliest_cr_line","open_acc","total_acc","revol_bal",
    "revol_util","loan_status","initial_list_status","policy_code","last_pymnt_d",
    "last_pymnt_amnt","next_pymnt_d","last_credit_pull_d","funded_amnt_inv","out_prncp",
    "out_prncp_inv","total_pymnt_inv","total_rec_prncp","total_rec_int","total_rec_late_fee",
    "pymnt_plan","collection_recovery_fee","collections_12_mths_ex_med","mths_since_last_delinq",
    "mths_since_last_record","mths_since_last_major_derog","open_acc_6m","open_il_6m",
    "open_il_12m","open_il_24m","mths_since_rcnt_il","total_bal_il","il_util",
    "open_rv_12m","open_rv_24m","max_bal_bc","all_util","total_rev_hi_lim","inq_last_6mths",
    "inq_fi","inq_last_12m","acc_now_delinq","tot_coll_amt","tot_cur_bal","total_cu_tl",
    "title","url","annual_inc_joint","dti_joint","verified_status_joint",
    "last_fico_range_low","last_fico_range_high",
]


class LcImportWizard(models.TransientModel):
    _name = "lc.import.wizard"
    _description = "Nhập lịch sử khoản vay Lending Club từ CSV/XLSX"

    data_file = fields.Binary(string="File lịch sử khoản vay (CSV/XLSX)", required=True)
    filename = fields.Char(string="File Name")
    delimiter = fields.Selection(
        [(",", ", (comma)"), (";", "; (semicolon)")],
        string="Delimiter",
        default=",",
        required=True,
        help="Chỉ áp dụng khi nhập CSV",
    )
    encoding = fields.Selection(
        [("utf-8", "UTF-8"), ("latin-1", "Latin-1")],
        string="Encoding",
        default="utf-8",
        required=True,
        help="Chỉ áp dụng khi nhập CSV",
    )

    @api.model
    def _is_excel(self, filename, content_head):
        if filename and str(filename).lower().endswith((".xlsx", ".xlsm")):
            return True
        # ZIP signature for xlsx
        return content_head.startswith(b"PK")

    @api.model
    def _norm(self, s):
        if s is None:
            return ""
        return (
            str(s)
            .strip()
            .replace("/", " ")
            .replace("-", " ")
            .replace("(", " ")
            .replace(")", " ")
            .lower()
            .replace(" ", "_")
        )

    @api.model
    def _parse_emp_length(self, v):
        if v is None:
            return 0
        s = str(v).strip().lower()
        if s in ("n/a", "na", "none", "", "nan"):
            return 0
        if "<" in s:
            return 0
        # examples: "10+ years", "9 years", "1 year"
        digits = "".join(ch for ch in s if ch.isdigit())
        return int(digits) if digits else 0

    @api.model
    def _to_float(self, v):
        if v is None or v == "":
            return 0.0
        if isinstance(v, (int, float)):
            return float(v)
        v = str(v).replace("%", "").strip()
        try:
            return float(v)
        except Exception:
            return 0.0

    @api.model
    def _to_int(self, v):
        if v is None or v == "":
            return 0
        if isinstance(v, (int, float)):
            return int(v)
        try:
            return int(float(str(v).strip()))
        except Exception:
            return 0

    @api.model
    def _to_date(self, v):
        if not v:
            return False
        if isinstance(v, (dt.date, dt.datetime)):
            d = v.date() if isinstance(v, dt.datetime) else v
            return d.strftime("%Y-%m-%d")
        s = str(v).strip()
        # Accept YYYY-MM-DD
        if len(s) == 10 and s[4] == "-" and s[7] == "-":
            return s
        # Accept MM/YYYY
        if "/" in s and len(s) <= 7:
            parts = s.split("/")
            if len(parts) == 2:
                mm, yyyy = parts
                return f"{yyyy}-{mm.zfill(2)}-01"
        # Accept Mon-YYYY like "Oct-2013" and Mon-YY like "Dec-11"
        for fmt in ("%b-%Y", "%b-%y"):
            try:
                parsed_date = dt.datetime.strptime(s, fmt)
                return parsed_date.strftime("%Y-%m-01")
            except Exception:
                pass

        # Handle specific case for Mon-YY format with manual mapping
        if re.match(r'^[A-Za-z]{3}-\d{2}$', s):
            month_map = {
                'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
                'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
                'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
            }
            try:
                month, year = s.split('-')
                if month in month_map:
                    # Assume years 00-30 are 2000s, 31-99 are 1900s
                    year_int = int(year)
                    full_year = 2000 + year_int if year_int <= 30 else 1900 + year_int
                    return f"{full_year}-{month_map[month]}-01"
            except (ValueError, KeyError):
                pass

        return False

    @api.model
    def _to_bool(self, v):
        if isinstance(v, bool):
            return v
        s = str(v or "").strip().lower()
        if s in ("y", "yes", "true", "1", "t"):  # common truthy tokens
            return True
        if s in ("n", "no", "false", "0", "f", ""):  # empty defaults to False
            return False
        return False

    def action_import(self):
        self.ensure_one()
        if not self.data_file:
            raise UserError(_("Hãy chọn file lịch sử khoản vay (CSV/XLSX)."))
        try:
            content = base64.b64decode(self.data_file or b"")
        except Exception as e:
            raise UserError(_("Không đọc được file: %s") % e)

        Loan = self.env["lc.loan"]
        created = 0
        updated = 0

        def iter_rows():
            if self._is_excel(self.filename, content[:2]):
                if not load_workbook:
                    raise UserError(
                        _("Thiếu thư viện openpyxl. Hãy thêm 'openpyxl' vào etc/requirements.txt và khởi động lại container.")
                    )
                wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
                ws = wb.active
                rows = ws.iter_rows(values_only=True)
                try:
                    headers = next(rows)
                except StopIteration:
                    return
                headers = [self._norm(h) for h in headers]
                for r in rows:
                    row = {headers[i]: r[i] for i in range(min(len(headers), len(r)))}
                    yield row
            else:
                text = content.decode(self.encoding or "utf-8", errors="ignore")
                sio = io.StringIO(text)
                reader = csv.reader(sio, delimiter=self.delimiter or ",")
                try:
                    headers_raw = next(reader)
                except StopIteration:
                    return
                headers = [self._norm(h) for h in headers_raw]
                desc_idx = headers.index("desc") if "desc" in headers else -1
                for cols in reader:
                    # Hợp nhất các cột thừa vào 'desc' nếu gặp CSV không có quote cho desc
                    if desc_idx != -1 and len(cols) > len(headers):
                        tail_count = len(headers) - desc_idx - 1
                        if tail_count < 0:
                            tail_count = 0
                        prefix = cols[:desc_idx]
                        # phần giữa (desc) có thể trống nếu không đủ cột
                        middle_end = len(cols) - tail_count if tail_count > 0 else len(cols)
                        desc_val = ",".join(cols[desc_idx:middle_end])
                        suffix = cols[middle_end:]
                        cols = prefix + [desc_val] + suffix
                    # Chuẩn hóa độ dài
                    if len(cols) < len(headers):
                        cols = cols + [""] * (len(headers) - len(cols))
                    if len(cols) > len(headers):
                        cols = cols[: len(headers)]
                    row = {headers[i]: cols[i] for i in range(len(headers))}
                    yield row

        for row in iter_rows():
            # Debug: print first few rows to see what's happening
            loan_id_raw = row.get("loan_id") or row.get("id") or ""
            if isinstance(loan_id_raw, str):
                loan_id = loan_id_raw.strip()
            else:
                loan_id = str(loan_id_raw or "")

            # Skip rows without loan_id
            if not loan_id:
                continue

            vals = {
                # core
                "loan_id": loan_id,
                "issue_d": self._to_date(row.get("issue_d")),
                "term": (row.get("term") or "").strip() if isinstance(row.get("term"), str) else (row.get("term") or ""),
                "int_rate": self._to_float(row.get("int_rate")),
                "installment": self._to_float(row.get("installment")),
                "grade": ((row.get("grade") or "").strip()[:1] if isinstance(row.get("grade"), str) else (row.get("grade") or "")) or False,
                "sub_grade": (row.get("sub_grade") or "").strip() if isinstance(row.get("sub_grade"), str) else (row.get("sub_grade") or ""),
                "emp_length": (row.get("emp_length") or "").strip() if isinstance(row.get("emp_length"), str) else (row.get("emp_length") or ""),
                "home_ownership": ((row.get("home_ownership") or "RENT").strip().upper() if isinstance(row.get("home_ownership"), str) else (row.get("home_ownership") or "RENT")) or "RENT",
                "annual_inc": self._to_float(row.get("annual_inc")),
                "dti": self._to_float(row.get("dti")),
                "delinq_2yrs": self._to_float(row.get("delinq_2yrs")),
                "pub_rec": self._to_float(row.get("pub_rec")),
                "fico_range_low": self._to_float(row.get("fico_range_low")),
                "fico_range_high": self._to_float(row.get("fico_range_high")),
                "purpose": (row.get("purpose") or "").strip() if isinstance(row.get("purpose"), str) else (row.get("purpose") or ""),
                "addr_state": (row.get("addr_state") or "").strip() if isinstance(row.get("addr_state"), str) else (row.get("addr_state") or ""),
                "loan_amnt": self._to_float(row.get("loan_amnt")),
                "funded_amnt": self._to_float(row.get("funded_amnt")),
                "total_pymnt": self._to_float(row.get("total_pymnt")),
                "recoveries": self._to_float(row.get("recoveries")),
                # extended
                "lc_listing_id": (row.get("lc_listing_id") or row.get("listing_id") or "").strip() if isinstance(row.get("lc_listing_id") or row.get("listing_id"), str) else (row.get("lc_listing_id") or row.get("listing_id") or ""),
                "member_id": (row.get("member_id") or "").strip() if isinstance(row.get("member_id"), str) else (row.get("member_id") or ""),
                "application_type": (row.get("application_type") or "").strip().upper() if isinstance(row.get("application_type"), str) else (row.get("application_type") or ""),
                "verification_status": (row.get("verification_status") or "").strip() if isinstance(row.get("verification_status"), str) else (row.get("verification_status") or ""),
                "is_inc_v": (row.get("is_inc_v") or "").strip() if isinstance(row.get("is_inc_v"), str) else (row.get("is_inc_v") or ""),
                "emp_title": (row.get("emp_title") or "").strip() if isinstance(row.get("emp_title"), str) else (row.get("emp_title") or ""),
                "zip_code": (row.get("zip_code") or "").strip() if isinstance(row.get("zip_code"), str) else (row.get("zip_code") or ""),
                "earliest_cr_line": self._to_date(row.get("earliest_cr_line")),
                "open_acc": self._to_float(row.get("open_acc")),
                "total_acc": self._to_float(row.get("total_acc")),
                "revol_bal": self._to_float(row.get("revol_bal")),
                "revol_util": self._to_float(row.get("revol_util")),
                "loan_status": (row.get("loan_status") or "").strip() if isinstance(row.get("loan_status"), str) else (row.get("loan_status") or ""),
                "initial_list_status": ((row.get("initial_list_status") or "").strip()[:1].upper() if isinstance(row.get("initial_list_status"), str) else (row.get("initial_list_status") or "")) or False,
                "policy_code": self._to_float(row.get("policy_code")),
                "last_pymnt_d": self._to_date(row.get("last_pymnt_d")),
                "last_pymnt_amnt": self._to_float(row.get("last_pymnt_amnt")),
                "next_pymnt_d": self._to_date(row.get("next_pymnt_d")),
                "last_credit_pull_d": self._to_date(row.get("last_credit_pull_d")),
                "funded_amnt_inv": self._to_float(row.get("funded_amnt_inv")),
                "out_prncp": self._to_float(row.get("out_prncp")),
                "out_prncp_inv": self._to_float(row.get("out_prncp_inv")),
                "total_pymnt_inv": self._to_float(row.get("total_pymnt_inv")),
                "total_rec_prncp": self._to_float(row.get("total_rec_prncp")),
                "total_rec_int": self._to_float(row.get("total_rec_int")),
                "total_rec_late_fee": self._to_float(row.get("total_rec_late_fee")),
                "pymnt_plan": (row.get("pymnt_plan") or "").strip() if isinstance(row.get("pymnt_plan"), str) else (row.get("pymnt_plan") or ""),

                "collection_recovery_fee": self._to_float(row.get("collection_recovery_fee")),
                "collections_12_mths_ex_med": self._to_float(row.get("collections_12_mths_ex_med")),
                "mths_since_last_delinq": self._to_float(row.get("mths_since_last_delinq")),
                "mths_since_last_record": self._to_float(row.get("mths_since_last_record")),
                "mths_since_last_major_derog": self._to_float(row.get("mths_since_last_major_derog")),
                "open_acc_6m": self._to_float(row.get("open_acc_6m")),
                "open_il_6m": self._to_float(row.get("open_il_6m")),
                "open_il_12m": self._to_float(row.get("open_il_12m")),
                "open_il_24m": self._to_float(row.get("open_il_24m")),
                "mths_since_rcnt_il": self._to_float(row.get("mths_since_rcnt_il")),
                "total_bal_il": self._to_float(row.get("total_bal_il")),
                "il_util": self._to_float(row.get("il_util")),
                "open_rv_12m": self._to_float(row.get("open_rv_12m")),
                "open_rv_24m": self._to_float(row.get("open_rv_24m")),
                "max_bal_bc": self._to_float(row.get("max_bal_bc")),
                "all_util": self._to_float(row.get("all_util")),
                "total_rev_hi_lim": self._to_float(row.get("total_rev_hi_lim")),
                "inq_last_6mths": self._to_float(row.get("inq_last_6mths")),
                "inq_fi": self._to_float(row.get("inq_fi")),
                "inq_last_12m": self._to_float(row.get("inq_last_12m")),
                "acc_now_delinq": self._to_float(row.get("acc_now_delinq")),
                "tot_coll_amt": self._to_float(row.get("tot_coll_amt")),
                "tot_cur_bal": self._to_float(row.get("tot_cur_bal")),
                "total_cu_tl": self._to_float(row.get("total_cu_tl")),
                "annual_inc_joint": self._to_float(row.get("annual_inc_joint")),
                "dti_joint": self._to_float(row.get("dti_joint")),
                "verified_status_joint": (row.get("verified_status_joint") or "").strip() if isinstance(row.get("verified_status_joint"), str) else (row.get("verified_status_joint") or ""),
                "last_fico_range_low": self._to_float(row.get("last_fico_range_low")),
                "last_fico_range_high": self._to_float(row.get("last_fico_range_high")),
                "desc": (row.get("desc") or "").strip() if isinstance(row.get("desc"), str) else (row.get("desc") or ""),
            }
            if not vals["loan_id"]:
                continue
            existing = Loan.search([("loan_id", "=", vals["loan_id"])], limit=1)
            if existing:
                existing.write(vals)
                updated += 1
            else:
                Loan.create(vals)
                created += 1

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Nhập lịch sử khoản vay hoàn tất"),
                "message": _("Tạo mới: %s, Cập nhật: %s") % (created, updated),
                "sticky": False,
            },
        }

