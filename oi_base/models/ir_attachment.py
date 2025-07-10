from odoo import models
from odoo.tools.pdf import OdooPdfFileReader, OdooPdfFileWriter
from odoo.tools import pdf
import io

class IrAttachment(models.Model):
    _inherit = 'ir.attachment'
    
    def _merge_as_pdf(self):
        stream_list = []
        output_pdf = OdooPdfFileWriter()
        for attachment in self:
            attachment_stream = pdf.to_pdf_stream(attachment)
            if attachment_stream:
                attachment_reader = OdooPdfFileReader(attachment_stream, strict=False)
                output_pdf.appendPagesFromReader(attachment_reader)
                stream_list.append(attachment_stream)

        new_pdf_stream = io.BytesIO()
        output_pdf.write(new_pdf_stream)

        for stream in stream_list:
            stream.close()

        return new_pdf_stream.getvalue()