from odoo import models, fields, api
from datetime import datetime
import base64
import io
import xlsxwriter

class EmployeeMovementReportWizard(models.TransientModel):
    _name = 'employee.movement.report.wizard'
    _description = 'Employee Movement Report Wizard'

    start_date = fields.Datetime("Start Date", required=True)
    end_date = fields.Datetime("End Date", required=True)
    include_no_geofence = fields.Boolean("Include Events Without Geofence", default=False)
    report_file = fields.Binary("Excel Report", readonly=True)
    filename = fields.Char("Filename", default="employee_movement.xlsx")

    def generate_report(self):
        # data = self.env['traccar.event.details'].search([
        #     ('event_time', '>=', self.start_date),
        #     ('event_time', '<=', self.end_date),
        #     ('geofence_id', '!=', False),
        # ], order='event_time')

        domain = [
            ('event_time', '>=', self.start_date),
            ('event_time', '<=', self.end_date),
        ]
        if not self.include_no_geofence:
            domain.append(('geofence_id', '!=', False))
        data = self.env['traccar.event.details'].search(domain)

        # Prepare Excel in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet("Employee Movement Report")

        # Styles
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'border': 1})
        bold = workbook.add_format({'bold': True})

        # Headers
        sheet.write('A1', 'Employee Movement Report', bold)
        sheet.write('A3', 'Date:', bold)
        sheet.write('B3', str(self.start_date))
        sheet.write('C3', '-', bold)
        sheet.write('D3', str(self.end_date))

        # Table headers
        headers = ['Staff Name', 'Ent Registration', 'Entry Time', 'Entry Geofence']
        for col, name in enumerate(headers):
            sheet.write(7, col, name, header_format)

        print("============= DATA ==========",data)
        # Data rows
        row = 8
        for rec in data:
            sheet.write(row, 0, rec.driver_id.name or '') # employee_code
            sheet.write(row, 1, rec.vehicle_id.license_plate or '') # Registration number
            sheet.write(row, 2, rec.event_time.strftime('%m/%d/%Y %H:%M') if rec.event_time else '')
            sheet.write(row, 3, str(rec.geofence_id or ''))  # You may also map this if you have geofence_name
            row += 1

        workbook.close()
        output.seek(0)

        self.write({
            'report_file': base64.b64encode(output.read()),
            'filename': f'employee_movement_{fields.Date.today()}.xlsx'
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'employee.movement.report.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
