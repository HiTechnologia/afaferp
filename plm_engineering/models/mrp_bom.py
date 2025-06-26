from odoo import api, fields, models


class MrpBomExtension(models.Model):
    _inherit = 'mrp.bom'

    type = fields.Selection(
        selection_add=[('ebom', 'Engineering BoM')],
        ondelete={'ebom': 'cascade'}
    )
    ebom_source_id = fields.Integer('Source Ebom ID')

    @api.model
    def _get_in_bom(self, pid, sid=False, bom_types=[]):
        bom_l_type = self.env['mrp.bom.line']
        if not bom_types:
            bom_line_brws_list = bom_l_type.search([
                ('product_id', '=', pid),
                ('source_id', '=', sid),
                ('type', '=', 'ebom')
            ])
            if not bom_line_brws_list:
                bom_line_brws_list = bom_l_type.search([
                    ('product_id', '=', pid),
                    ('source_id', '=', sid),
                    ('type', '=', 'normal')
                ])
                if not bom_line_brws_list:
                    bom_line_brws_list = bom_l_type.search([
                        ('product_id', '=', pid),
                        ('source_id', '=', False),
                        ('type', '=', 'ebom')
                    ])
                if not bom_line_brws_list:
                    bom_line_brws_list = bom_l_type.search([
                        ('product_id', '=', pid),
                        ('source_id', '=', False),
                        ('type', '=', 'normal')
                    ])
                    if not bom_line_brws_list:
                        bom_line_brws_list = bom_l_type.search([
                            ('product_id', '=', pid),
                            ('type', '=', 'ebom')
                        ])
                    if not bom_line_brws_list:
                        bom_line_brws_list = bom_l_type.search([
                            ('product_id', '=', pid),
                            ('type', '=', 'normal')
                        ])
        else:
            bl_filter = [('product_id', '=', pid), ('type', 'in', bom_types)]
            if sid:
                bl_filter.append(('source_id', '=', sid))
            bom_line_brws_list = bom_l_type.search(bl_filter)
        return bom_line_brws_list

    @api.model
    def _get_bom(self, pid, sid=False):
        if sid is None:
            sid = False
        bom_brws_list = self.search([
            ('product_tmpl_id', '=', pid),
            ('source_id', '=', sid),
            ('type', '=', 'ebom')
        ])
        if not bom_brws_list:
            bom_brws_list = self.search([
                ('product_tmpl_id', '=', pid),
                ('source_id', '=', sid),
                ('type', '=', 'normal')
            ])
            if not bom_brws_list:
                bom_brws_list = self.search([
                    ('product_tmpl_id', '=', pid),
                    ('source_id', '=', False),
                    ('type', '=', 'ebom')
                ])
                if not bom_brws_list:
                    bom_brws_list = self.search([
                        ('product_tmpl_id', '=', pid),
                        ('source_id', '=', False),
                        ('type', '=', 'normal')
                    ])
                    if not bom_brws_list:
                        bom_brws_list = self.search([
                            ('product_tmpl_id', '=', pid),
                            ('type', '=', 'ebom')
                        ])
                        if not bom_brws_list:
                            bom_brws_list = self.search([
                                ('product_tmpl_id', '=', pid),
                                ('type', '=', 'normal')
                            ])
        return bom_brws_list

    @api.model
    def SaveStructure(self, relations, level=0, curr_level=0, kind_bom='ebom'):
        """
        Save EBom relations
        """
        return super(MrpBomExtension, self).SaveStructure(
            relations,
            level,
            curr_level,
            kind_bom='ebom'
        )
