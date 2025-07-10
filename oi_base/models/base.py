
from odoo.models import BaseModel
from odoo import models, api, fields,_
import datetime
import re
import uuid
import string
import random
from odoo.tools.misc import clean_context
import pytz
from odoo.tools import file_open

def get_report_code(path: str):
    with file_open(path) as f:
        content : str = f.read()
    idx = content.index("#")
    return content[idx:]
    
class Base(models.AbstractModel):
    _inherit ='base'
    
    def _get_report_source_code(self, path: str):
        return get_report_code(path)

    def _get_file_source_code(self, path: str):
        return self._get_report_source_code(path)

    @api.model
    def _base(self, model = 'base'):
        return type(self.env[model])
        
    def _create_external_id(self):
        ref = self.get_external_id().get(self.id)        
        if not ref:
            IrModelData = self.env['ir.model.data']
            if self._context.get('is_approval_setting'):
                vals = {'module' : '_workflow',
                        'name' : self._suggest_external_id(),
                        'noupdate' : True
                    }
            else:
                vals = {'module' : '_',
                        'name' : self._suggest_external_id()
                    }
            while IrModelData.search(self._dict_to_domain(vals)):
                vals['name'] = '%s_%s' % (vals['name'], uuid.uuid4().hex[:6])            
            vals.update({
                'model' : self._name,
                'res_id' : self.id
                })
            ref=IrModelData.create(vals).complete_name     
        return ref       

        
    def _read_field(self, field):
        """
        :param field name
        :return: dictionary mapping record id with field value
        """
        res = self.read([field])
        res = {record['id'] : record[field] for record in res}
        return res
    
        
    @api.model
    def _isinstance(self, model: str):
        if model not in self.pool:
            return False
        return isinstance(self, self.pool.get(model))
    
    @api.model
    def _dict_to_domain(self, vals):
        domain = []
        for key, value in vals.items():
            if isinstance(value, (dict,list,tuple )):
                value = str(value)
            domain.append((key, '=', value))
        return domain
    
    def get_title(self):        
        return '%s | %s' % (self.env['ir.model']._get(self._name).name, self.display_name) 
    
    def get_requester_name(self):        
        return '%s' % (self.employee_id.name if 'employee_id' in self._fields else self.create_uid.name)
    
    def get_form_url(self):        
        return f"/odoo/{self._name}/{self.id}"
        
    def _expand_group_all(self, records, domain, order):
        return records.search([], order = order)
    
    def _hierarchical_sort(self, parent_name = None):
        parent_name = parent_name or self._parent_name or 'parent_id'
        vals = {}
        for record in self:
            parent = record
            level = 0
            recursion_test = set()
            while parent[parent_name]:
                level +=1
                parent = parent[parent_name]
                if parent in recursion_test:
                    break
                recursion_test.add(parent)
            vals[record] = level
            
        return self.sorted(key = lambda record : (vals[record], record.display_name))
    
    def _selection_name(self, field_name):
        if not self:
            return False
        names = dict(self._fields[field_name]._description_selection(self.env))
        value = self[field_name]
        return names.get(value, value)   
    
    def _child_of(self, others, parent=None):
        "return True if self child of others"
        if not (isinstance(others, BaseModel) and others._name == self._name):
            raise TypeError("Comparing apples and oranges: %s._child_of(%s)" % (self, others))
        parent_name = parent or self._parent_name
        current = self
        while current:
            if current in others:
                return True
            current = current[parent_name]
            
    def _get_parent_record(self, level = -1, parent_name = None):
        """
        Retrieves a parent record at a specified level in the hierarchy.

        This method traverses up the hierarchy using the specified parent field name and returns
        the parent record at the requested level. If the level is negative, it counts from the
        top of the hierarchy (-1 being the topmost parent).

        Args:
            level (int, optional): The level of the parent to retrieve. Negative numbers count
                from the top of the hierarchy. Defaults to -1 (topmost parent).
            parent_name (str, optional): The field name used to reference the parent record.
                If not provided, uses the model's _parent_name attribute.

        Returns:
            recordset: The parent record at the specified level. Returns an empty recordset
                if the requested level is out of range.

        Example:
            # Get immediate parent
            parent = record._get_parent_record(1)
            # Get topmost parent
            top_parent = record._get_parent_record(-1)
            # Get parent using custom parent field
            custom_parent = record._get_parent_record(1, 'custom_parent_field')
        """
        parent_name = parent_name or self._parent_name
        current = self
        parents = self
        while current[parent_name]:
            current = current[parent_name]
            parents += current            
        try:
            return parents[level]        
        except IndexError:
            return self.browse()
               
    def _action_view_one2many(self, field_name):
        field = self._fields[field_name]
        assert field.type == 'one2many'
        return {
            'type' : 'ir.actions.act_window',
            'name' : self.env['ir.model.fields']._get(self._name, field.name).field_description,
            'res_model' : field.comodel_name, 
            'view_mode' : 'list,form',
            'domain' : [(field.inverse_name,'=', self.id)],
            'context' : {
                'default_' + field.inverse_name : self.id
                }
            }    
    
    def action_open_window(self, **kwargs) -> dict:
        action : dict = {
            'type' : 'ir.actions.act_window',
            'res_model' : self._name,
            }
        if len(self) == 1 and not kwargs.get('view_mode'):
            action.update({
                'view_mode' : 'form',
                'res_id' : self.id                        
                })        
        else:
            action.update({
                'view_mode' : 'list,form',
                'domain' : [('id','in', self.ids)],
                'name' : self._description,                  
                })       
        action.update(**kwargs)         
        return action
    
    def _add_users_to_groups(self, group_ext_ids:list, users):
        """ Adding users to groups

        :param group_ext_ids: list of string external ids for the groups
        :param users: users record set or ids
        """
        for group in group_ext_ids:
            for user in users:
                if not isinstance(user, int):
                    user = user.id
                self.env.ref(group).write({'users': [(4, user)]})

    def _random_password(self, length = 16, chars = None):
        chars = list(chars or (string.ascii_letters + string.digits + string.punctuation))
        random.shuffle(chars)
        res = []
        for _ in range(length):
            res.append(random.choice(chars))
        
        return ''.join(res)
    
    def get_group_emails(self, groups):
        if isinstance(groups, str):
            groups = groups.split(',')
            res = self.env['res.groups'].with_context(active_test = True)
            for xmlid in groups:
                res += self.env.ref(xmlid)
            groups = res        
        groups = groups or self.env['res.groups']
        return ','.join(groups.users.filtered('email').mapped('email_formatted'))

    def get_group_partners(self, groups):
        if isinstance(groups, str):
            groups = groups.split(',')
            res = self.env['res.groups'].with_context(active_test = True)
            for xmlid in groups:
                res += self.env.ref(xmlid)
            groups = res        
        groups = groups or self.env['res.groups']
        return ','.join(groups.users.mapped('name'))

                
    def _get_date_start(self, date: datetime.date, tz_name: str = None):
        """get start of a date on context timezone

        Args:
            date (datetime.date): date
            tz_name (str): timezone name
        Returns:
            datetime
        """
        tz_name = tz_name or self._context.get('tz') or self.env.user.tz
        tz = tz_name and pytz.timezone(tz_name) or pytz.UTC
        date = datetime.datetime.combine(date, datetime.time.min)
        return tz.localize(date.replace(tzinfo=None), is_dst=False).astimezone(pytz.UTC).replace(tzinfo=None)
    
    def _get_date_end(self, date: datetime.date, tz_name: str = None):
        """get end of a date on context timezone

        Args:
            date (datetime.date): date
            tz_name (str): timezone name
        Returns:
            datetime
        """
        return self._get_date_start(date, tz_name) + datetime.timedelta(hours=23, minutes=59, seconds=59, microseconds=9999)
    
    def _snapshot_copy_data(self, default = {}):        
        "copy all store fields except one2many"
        self.ensure_one()
        vals = {}
        for name,field in self._fields.items():
            if field.store and not field.automatic and not field.inherited and field.type not in ['one2many'] and name not in default:
                vals[name] = self[name]
        
        vals.update(default)
        
        vals = self._convert_to_write(vals)
        
        return vals
    
    def _snapshot_copy(self, default = {}):
        "copy all store fields except one2many"
        vals = self._snapshot_copy_data(default)
        return self.create(vals)
                
    def _load_file_data(self, field_name: str = 'raw', 
                   sheet_name : str | None = None, 
                   file_name : str | None = None,
                   file_type : str | None = None,
                   date_fields = [], 
                   datetime_fields = [], 
                   date_tz_convert = True) -> list[dict[str,any]]:                                                
        
        """
        Load and parse data from a file field into a structured format.
        This method takes file data (from an attachment or base64 encoded field) and converts it 
        into a list of dictionaries. Each dictionary represents a row from the file, with keys 
        derived from the column headers. The method can handle different file types (Excel, CSV, etc.)
        and provides special processing for date and datetime fields.
        Args:
            field_name (str, optional): The field name containing the file data. Defaults to 'raw'.
            sheet_name (str | None, optional): For Excel files, the sheet to read. Defaults to None (first sheet).
            file_name (str | None, optional): Name of the file. Defaults to None.
            file_type (str | None, optional): Type of the file. Defaults to None (auto-detect).
            date_fields (list, optional): List of field names to be parsed as dates. Defaults to empty list.
            datetime_fields (list, optional): List of field names to be parsed as datetimes. Defaults to empty list.
            date_tz_convert (bool, optional): Whether to convert datetime fields to UTC. Defaults to True.
        Returns:
            list[dict[str, any]]: A list of dictionaries, each representing a row from the file.
                                    Keys are normalized column names (lowercase, spaces replaced with underscores).
                                    
        Notes:
            - Column headers are normalized by converting to lowercase and replacing spaces with underscores
            - When timezone conversion is enabled, datetime fields are converted from user timezone to UTC
                                    
        Example:
            >>> attachment = self.env['ir.attachment'].browse(attachment_id)
            >>> data = attachment._load_file_data(sheet_name='Sheet1', date_fields=['birth_date'])
        """        
        import base64        
        from dateutil import parser
        
        if self._name == "ir.attachment" and field_name == "raw":
            file_data = self[field_name]
        else:
            file_data = base64.b64decode(self[field_name])
            
        base_import = self.env['base_import.import'].new({
            'file': file_data,
            'file_name' : file_name,
            'file_type' : file_type
        })
        
        total_rows, rows = base_import._read_file({'sheet' : sheet_name})
        total_rows = min(total_rows, len(rows))
        
        field_names = [col.strip().lower().replace(" ", "_") for col in rows[0]]
        data = []
        
        for row_idx in range(1, total_rows):
            row = rows[row_idx]
            vals = {}
            for col_idx, value in enumerate(row):
                field_name = field_names[col_idx]
                if field_name in date_fields or field_name in datetime_fields:
                    if isinstance(value, str):
                        try:
                            value = parser.parse(value)
                        except:
                            pass
                    if isinstance(value, datetime.datetime) and field_name in date_fields:
                        value = value.date()
                        
                    elif date_tz_convert and isinstance(value, datetime.datetime) and field_name in datetime_fields:
                        tz_name = self._context.get('tz') or self.env.user.tz
                        if tz_name:
                            tz = pytz.timezone(tz_name)
                            value = tz.localize(value).astimezone(pytz.UTC).replace(tzinfo=None)
                
                vals[field_name] = value
            data.append(vals)
        
        return data
        
    def _get_next_new_name(self, name: str) -> str:
        """
        Generate the next sequential name by incrementing the number suffix.

        This method checks if the name ends with a pattern "-n" where n is a number.
        If the pattern is found, it increments the number (e.g., "Document-1" becomes "Document-2").
        If the pattern is not found, it appends "-1" to the name (e.g., "Document" becomes "Document-1").

        Args:
            name (str): The original name to be processed.

        Returns:
            str: The next name in the sequence with an incremented number suffix.

        Examples:
            >>> self._get_next_new_name("Document-1")
            'Document-2'
            >>> self._get_next_new_name("Document")
            'Document-1'
        """
        name_match = re.search(r"(^.*)\-(\d+)$", name)
        return f"{name_match.group(1)}-{int(name_match.group(2)) + 1}" if name_match else name + "-1"