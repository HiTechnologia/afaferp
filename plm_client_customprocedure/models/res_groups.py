import logging
import tempfile
import os
import base64
from odoo import _, api, fields, models


class ResGroups(models.Model):
    _name = 'res.groups'
    _inherit = 'res.groups'

    custom_procedure = fields.Binary(string=_('Client CustomProcedure'))
    custom_procedure_fname = fields.Char(_("Custom Procedure File name"))
    custom_read_content = fields.Text('Custom Read Content')

    custom_multicad = fields.Binary(string=_('Client Multicad'))
    custom_multicad_fname = fields.Char(_("MultiCad File name"))
    custom_multicad_content = fields.Text('Custom Multicad Content')

    def write(self, vals):
        erase = self.env.context.get('erase_multicad', True)
        erase_custom = self.env.context.get('erase_customprocedure', True)
        if erase and 'custom_multicad_content' in vals:
            self.open_custom_multicad_save(vals)
        if erase_custom and 'custom_read_content' in vals:
            self.open_custommodule_save(vals)
        return super(ResGroups, self).write(vals)

    def open_custommodule_edit(self):
        ctx = self.env.context.copy()
        ctx['erase_customprocedure'] = False
        for groupBrws in self:
            if groupBrws.custom_procedure:
                fileReadableContent = base64.b64decode(groupBrws.custom_procedure)
                if self.custom_read_content:
                    fileReadableContent = ''
                self.with_context(ctx).custom_read_content = fileReadableContent

    def open_custom_multicad_edit(self):
        ctx = self.env.context.copy()
        ctx['erase_multicad'] = False
        for groupBrws in self:
            if groupBrws.custom_multicad:
                fileReadableContent = base64.b64decode(groupBrws.custom_multicad)
                if self.custom_multicad_content:
                    fileReadableContent = ''
                self.with_context(ctx).custom_multicad_content = fileReadableContent

    def open_custommodule_save(self, vals):
        for groupBrws in self:
            self.commonSave(vals,
                            'custom_procedure',
                            'custom_read_content',
                            groupBrws.custom_procedure_fname,
                            groupBrws.custom_procedure
                            )

    @api.model
    def open_custom_multicad_save(self, vals):
        for groupBrws in self:
            self.commonSave(vals,
                            'custom_multicad',
                            'custom_multicad_content',
                            groupBrws.custom_multicad_fname,
                            groupBrws.custom_multicad
                            )

    @api.model
    def commonSave(self, vals, binary_field, content_field, fname, custom_file):
        vals[binary_field] = base64.b64encode(vals.get(content_field, '').encode('utf-8'))
        tmpFolder = tempfile.gettempdir()
        if fname:
            customFilePath = os.path.join(tmpFolder, fname)
            with open(customFilePath, 'wb') as writeFile:
                writeFile.write(base64.b64decode(custom_file))
        vals[content_field] = ''

    def getCustomProcedure(self):
        """
        This method is used on customer side.
        """
        for groupBrws in self:
            logging.info(
                'Request CustomProcedure file for user %r and group %r-%r and id %r'
                % (groupBrws.env.uid, groupBrws.category_id.name,
                   groupBrws.name, groupBrws.id)
            )
            custom_procedure = groupBrws.custom_procedure
            if custom_procedure:
                return True, custom_procedure, groupBrws.custom_procedure_fname
        return False, '', groupBrws.custom_procedure_fname

    def getCustomMulticad(self):
        """
        This method is used on customer side.
        """
        for groupBrws in self:
            logging.info(
                'Request Multicad file for user %r and group %r-%r and id %r'
                % (groupBrws.env.uid, groupBrws.category_id.name,
                   groupBrws.name, groupBrws.id)
            )
            if groupBrws.custom_multicad:
                return True, groupBrws.custom_multicad, groupBrws.custom_multicad_fname
        return False, '', groupBrws.custom_multicad_fname
