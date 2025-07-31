# controllers/main.py
from odoo import http
from odoo.http import request
import io
import xlsxwriter
import datetime

class CrmExportController(http.Controller):
    @http.route('/web/content/crm.lead/export_excel', type='http', auth='user')
    def download_excel_file(self, ids, **kw):
        record_ids = [int(x) for x in ids.split(',')] if ids else []
        leads = request.env['crm.lead'].browse(record_ids)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet("CRM Report")

        # Define formats (as provided in the previous full solution)
        bold = workbook.add_format({'bold': True, 'bg_color': '#FFF200', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        cell_format = workbook.add_format({'border': 1})
        date_format = workbook.add_format({'border': 1, 'num_format': 'yyyy-mm-dd'})
        amount_format = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})

        # Set column widths (as provided in the previous full solution)
        sheet.set_column('A:A', 15)
        sheet.set_column('B:B', 15)
        sheet.set_column('C:C', 25)
        sheet.set_column('D:D', 25)
        sheet.set_column('E:E', 30)
        sheet.set_column('F:F', 15)
        sheet.set_column('G:G', 40)
        sheet.set_column('H:H', 20)
        sheet.set_column('I:I', 15)

        headers = [
            "Quotation No", "Quotation Date", "Consultant", "Main Contractor",
            "Client", "Plot No.", "Project Details", "Quotation Amount (AED)", "Status"
        ]
        for col, header in enumerate(headers):
            sheet.write(0, col, header, bold)

        for row, lead in enumerate(leads, start=1):
            sheet.write(row, 0, lead.name or '', cell_format)
            sheet.write(row, 1, lead.create_date.strftime('%Y-%m-%d') if lead.create_date else '', date_format)
            sheet.write(row, 2, ', '.join(lead.consultant.mapped('name')) or '', cell_format)
            sheet.write(row, 3, ', '.join(lead.contractor_line_ids.mapped('contractor_id.name')) or '', cell_format)
            sheet.write(row, 4, lead.partner_id.name or '', cell_format)
            sheet.write(row, 5, lead.project_plot or '', cell_format)
            sheet.write(row, 6, lead.project_detail or '', cell_format)
            sheet.write(row, 7, lead.expected_revenue or 0.0, amount_format)
            quoted_label = dict(lead._fields['ht_type'].selection).get(lead.ht_type, '')
            sheet.write(row, 8, quoted_label, cell_format)

        workbook.close()
        output.seek(0)

        response = request.make_response(
            output.read(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', 'attachment; filename="crm_quotation_report.xlsx"')
            ]
        )
        return response