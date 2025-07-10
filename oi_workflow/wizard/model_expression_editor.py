from odoo import models, fields, api
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval

class ModelExpressionEditor(models.TransientModel):
    _name = 'model.expression.editor'
    _description = 'Model Expression Editor'
    
    model = fields.Char(required=True)
    domain = fields.Char()
    code = fields.Char(compute = "_compute_code", store = True, readonly = False)
    
    def _get_code(self, domain: str):
        domain = safe_eval(domain.strip())
        if not domain:
            return ""
        result = []
        for leaf in reversed(domain):
            if leaf == '|':
                result.append(f"({result.pop()}) or ({result.pop()})")
            elif leaf == '!':
                result.insert(0, "not ")
            elif leaf == '&':
                result.append(f"({result.pop()}) and ({result.pop()})")
            elif leaf == expression.TRUE_LEAF:
                result.append("True")
            elif leaf == expression.FALSE_LEAF:
                result.append("False")
            else:
                (key, comparator, value) = leaf
                if isinstance(value, bool):
                    add_not = (not value and comparator == "=") or (value and comparator == "!=")
                    result.append(f"{'not ' if add_not else ''}record.{key}")
                else:
                    if comparator=="=":
                        comparator = "=="
                    
                    if isinstance(self.env[self.model].mapped(key), models.Model):
                        key = f"{key}.id"
                    
                    result.append(f"record.{key} {comparator} " + repr(value))
    
        return " ".join(result)    
    
    @api.depends('domain')
    def _compute_code(self):
        for record in self:
            try:
                record.code = self._get_code(record.domain or "[]")
            except Exception as e:
                record.code = str(e)