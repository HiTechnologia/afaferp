import datetime
import logging
from datetime import datetime

from odoo import _
from odoo import api
from odoo import fields
#
from odoo import models
from odoo.exceptions import UserError, ValidationError

#
_logger = logging.getLogger(__name__)
#
START_STATUS = 'draft'
CONFIRMED_STATUS = 'confirmed'
RELEASED_STATUS = 'released'
OBSOLATED_STATUS = 'obsoleted'
UNDER_MODIFY_STATUS = 'undermodify'
USED_STATES = [(START_STATUS, _('Draft')),
               (CONFIRMED_STATUS, _('Confirmed')),
               (RELEASED_STATUS, _('Released')),
               (UNDER_MODIFY_STATUS, _('UnderModify')),
               (OBSOLATED_STATUS, _('Obsoleted'))]
#
RELEASED_STATUSES = [RELEASED_STATUS, UNDER_MODIFY_STATUS]
#
PLM_NO_WRITE_STATE = [CONFIRMED_STATUS,
                      RELEASED_STATUS,
                      UNDER_MODIFY_STATUS,
                      OBSOLATED_STATUS]
#
LOWERCASE_LETTERS = [chr(i) for i in range(ord('a'), ord('z') + 1)]
#
UPPERCASE_LETTERS = [
    chr(i) for i in range(ord('A'), ord('Z') + 1)
]
#
def convert_to_letter(l, n):
    n_o_w = len(l)
    if n > n_o_w - 1:
        out = l[n_o_w - 1]
        out += convert_to_letter(n - n_o_w, l)
    else:
        out = l[n]
    return out
#
class RevisionBaseMixin(models.AbstractModel):
    _name = 'revision.plm.mixin'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Revision Mixin'

    engineering_code = fields.Char(string="Engineering Code")
    engineering_revision = fields.Integer(string="Engineering Revision index",
                                          default=0)
    engineering_revision_letter = fields.Char(
        string="Engineering Revision letter",
        default="A"
    )
    engineering_branch_revision = fields.Integer(
        string="Engineering Branch index",
        default=0
    )
    engineering_branch_revision_letter = fields.Char(
        string="Engineering Sub Revision letter",
        default="A"
    )
    engineering_state = fields.Selection(
        USED_STATES,
        string="Engineering Status",
        default='draft',
        tracking=True
    )
    # workflow filed to manage revision information
    engineering_release_date = fields.Datetime(
        _('Release date'),
        tracking=True
    )
    engineering_release_user = fields.Many2one(
        'res.users',
        string=_("Release User")
    )
    engineering_workflow_date = fields.Datetime(
        _('Workflow date'),
        tracking=True
    )
    engineering_workflow_user = fields.Many2one(
        'res.users',
        string=_("Workflow User")
    )
    engineering_writable = fields.Boolean(
        'Writable',
        default=True
    )
    engineering_code_editable = fields.Boolean(
        "Engineering Code Editable",
        default=True
    )
    engineering_revision_user = fields.Many2one(
        'res.users',
        string=_("User Revision")
    )
    engineering_revision_date = fields.Datetime(
        string=_('Datetime Revision')
    )
    engineering_branch_parent_id = fields.Integer('Parent branch')
    engineering_sub_revision_letter = fields.Char("Sub revision path")
    engineering_revision_count = fields.Integer(compute='_engineering_revision_count')

    @api.constrains('engineering_code', 'engineering_revision')
    def _check_engineering_constraints(self):
        """method used checks eng code and eng revision both should not same value or duplicate combination."""
        for rec in self:

            # 2️⃣ Check for uniqueness across the table
            if rec.engineering_code:
                domain = [
                    ('engineering_code', '=', rec.engineering_code),
                    ('engineering_revision', '=', rec.engineering_revision),
                    ('id', '!=', rec.id)
                ]
                if self.search_count(domain):
                    raise ValidationError(
                        _("This Engineering Code and Revision combination already exists: '%s' - Rev %s") % (
                            rec.engineering_code, rec.engineering_revision))

    def init(self):
        """Ensure there is at most one active variant for each combination.

        There could be no variant for a combination if using dynamic attributes.
        """
        if self._name != 'revision.plm.mixin':
            sql = """
            CREATE UNIQUE INDEX IF NOT EXISTS {unique_name}
            ON {table_name} (engineering_code, engineering_revision)
            WHERE (engineering_code is not null or engineering_code not in ('-',''))
            """.format(unique_name="unique_index_%s" % self._table,
                       table_name=self._table)
            self.env.cr.execute(sql)

    def _engineering_revision_count(self):
        """
        get All version product_tempate based on this one
        """
        for obj in self:
            if obj.engineering_code:
                obj.engineering_revision_count = self.search_count([
                    ('engineering_code', '=', obj.engineering_code)
                ])
            else:
                obj.engineering_revision_count = 0

    def _mark_workflow_release_now(self):
        """
        mark the object to be released if is in the proper status
        """
        for obj in self:
            if obj.engineering_state == RELEASED_STATUS:
                obj.engineering_writable = False
                obj.engineering_release_date = datetime.now()
                obj.engineering_release_user = self.env.uid
            elif obj.engineering_state == OBSOLATED_STATUS:
                obj.engineering_writable = False
            else:
                obj.engineering_writable = True

    def _mark_worklow_user_date(self):
        for obj in self:
            obj.engineering_workflow_date = datetime.now()
            obj.engineering_workflow_user = self.env.uid
            obj._mark_workflow_release_now()

    def action_from_draft_to_confirmed(self):
        for obj in self:  # self:
            obj._mark_worklow_user_date()
            obj.engineering_state = CONFIRMED_STATUS

    def action_from_confirmed_to_draft(self):
        for obj in self:
            obj.engineering_state = START_STATUS
            obj._mark_worklow_user_date()

    def action_from_confirmed_to_released(self):
        for obj in self:
            obj.engineering_state = RELEASED_STATUS
            obj._mark_worklow_user_date()
            obj._mark_obsolete_previous()

    def action_un_release(self):
        if not self.env.user.has_group("plm.group_plm_admin_unrelease"):
            raise UserError(
                "You are not allowed to perform such an action ask to your PLM admin"
            )
        for obj in self:
            body = """
                FORCE draft action from super plm admin user !!!
                data could be not as expected !!!
            """
            obj.message_post(body=body)
            obj.with_context(check=False).engineering_state = START_STATUS

    def action_un_release_release(self):
        if not self.env.user.has_group("plm.group_plm_admin_unrelease"):
            raise UserError(
                "You are not allowed to perform such an action ask to your PLM admin"
            )
        for obj in self:
            body = """
                FORCE release action from super plm admin user !!!
                data could be not as expected !!!
            """
            obj.message_post(body=body)
            obj.with_context(check=False).engineering_state = RELEASED_STATUS

    def _mark_obsolare(self):
        for obj in self:
            obj.engineering_state = OBSOLATED_STATUS
            obj._mark_worklow_user_date()

    def _mark_under_modifie(self):
        for obj in self:
            obj.engineering_state = UNDER_MODIFY_STATUS
            obj._mark_worklow_user_date()

    def _mark_under_modifie_previous(self):
        for obj in self:
            if obj.engineering_revision in [False, 0]:
                continue
            obj_previus_version = obj.get_previus_version()
            obj_previus_version._mark_under_modifie()
            obj.message_post(
                body=_("New version created from Code %s Rev. %s" % (
                    obj_previus_version.engineering_code,
                    obj_previus_version.engineering_revision
                ))
            )

    def _mark_obsolete_previous(self):
        for obj in self:
            if obj.engineering_revision in [False, 0]:
                continue
            obj_previus_version = obj.get_previus_version()
            obj_previus_version._mark_obsolare()

    def before_move_to_state(self, from_state, to_state):
        """
        technical function for workflow customization
        :from_state state that came from
        :to_state state to go
        """
        self.ensure_one()

    def move_to_state(self, state):
        for obj in self:
            before_state = obj.engineering_state
            if before_state == state:
                logging.warning(
                    "[%s] Moving %s to %s nothing to perform" % (
                        obj.engineering_code,
                        state,
                        state
                    )
                )
                continue
            function_name = "action_from_%s_to_%s" % (before_state, state)
            try:
                obj.before_move_to_state(before_state, state)
            except Exception as ex:
                raise UserError("Error on custom function Before Move to state %s" % ex)
            f = getattr(obj, function_name)
            f()
            try:
                obj.after_move_to_state(before_state, state)
            except Exception as ex:
                raise UserError("Error on custom function After Move to state %s" % ex)

    def after_move_to_state(self, from_state, to_state):
        """
        technical function for workflow customization
        :from_state state that came from
        :to_state state to go
        """
        self.ensure_one()

    def is_released(self):
        self.ensure_one()
        return self.engineering_state in [RELEASED_STATUS, UNDER_MODIFY_STATUS]

    def is_releaseble(self):
        self.ensure_one()
        return self.engineering_state == RELEASED_STATUS

    def new_version(self):
        """
        create a new version
        """
        for obj in self:
            if not obj.is_releaseble():
                raise UserError(
                    _("Unable to revise a %s in status %s that different from released"
                      % (obj.engineering_code,
                         obj.engineering_revision)
                      )
                )
            obj_new = obj._new_version()
            obj_new._mark_under_modifie_previous()
            """
            "1" relased
            "2"
            #
            "1.0.3" released
            "1.0.4" draft mettere un campo che indica che una nuova versione e'
             stata fatta <div>
            "2"
            #
            "1.0.3" released
            "1.0.4" draft mettere un campo che indica che una nuova versione e'
             stata fatta <div>
            "2"
            "3"
            "3.0" ->release che deriva da 1.0.4 con replace del content del
            file o delle info ??

            """

    def _new_version(self):
        self.ensure_one()
        obj_latest = self.get_latest_version()
        new_revision_index = obj_latest.engineering_revision + 1
        write_context = {
            'name': self.name,
            'engineering_code': self.engineering_code,
            'engineering_revision': new_revision_index,
            'engineering_revision_letter': self.get_revision_letter(new_revision_index),
            'engineering_state': START_STATUS,
        }
        obj_new = self.with_context(copy_context=write_context).copy(write_context)
        return obj_new

    def new_branch(self):
        """
        Make a new branch of the current object
        es:
            product_1 -> revision branch 0
            to
            product_1 -> revision branch 0.0
        """
        self._new_branch()

    def new_branch_version(self):
        """
        make a new version branch of the current prduct
        es:
            product_1-> revision branch 0
            to
            product_1-> revision branch 1
        """
        self._new_branch_version()

    def _new_branch_version(self):
        self.ensure_one()
        obj_latest = self.get_latest_version()
        new_eng_revision = obj_latest.engineering_revision + 1
        new_branch_revision = self.get_latest_level_branch_revision(
        ).engineering_branch_revision + 1
        path = ".".join(self.engineering_sub_revision_letter.split(".")[:-1])
        return self.copy({
            'engineering_revision': new_eng_revision,
            'engineering_code': obj_latest.engineering_code,
            'engineering_branch_revision': new_branch_revision,
            'engineering_sub_revision_letter': "%s.%s" % (path, new_branch_revision),
            'engineering_state': START_STATUS,
        })

    def _new_branch(self):
        self.ensure_one()
        obj_new = self._new_version()
        obj_new.engineering_branch_revision = 0
        obj_new.engineering_branch_parent_id = self.id
        if not self.engineering_branch_parent_id:
            parnet_path = self.engineering_revision
        else:
            parnet_path = self.engineering_sub_revision_letter
        obj_new.engineering_sub_revision_letter = "%s.0" % parnet_path

    def get_engineering_branch_parent(self):
        self.ensure_one()
        return self.browse(self.engineering_branch_parent_id)

    def get_revision_letter(self, engineering_revision=False):
        self.ensure_one()
        if engineering_revision:
            return convert_to_letter(UPPERCASE_LETTERS, engineering_revision)
        return convert_to_letter(UPPERCASE_LETTERS, self.engineering_revision)

    def children_branch(self):
        self.ensure_one()
        return self.search([
            ('engineering_branch_parent_id', '=', self.id)
        ], order="engineering_branch_revision desc")

    def get_latest_level_branch_revision(self):
        if self.engineering_branch_parent_id:
            for children in self.search([
                ('engineering_branch_parent_id', '=', self.engineering_branch_parent_id)
            ],order="engineering_branch_revision desc"):
                return children
        return []

    def copy(self, default=None):
        default = default or {}
        if 'engineering_state' not in default:
            default['engineering_state'] = START_STATUS
        if 'engineering_code' not in default:
            default['engineering_code'] = False
        if 'engineering_revision' not in default:
            default['engineering_revision'] = 0
            default['engineering_revision_letter'] = self.get_revision_letter(0)
        return super(RevisionBaseMixin, self).copy(default)

    def get_latest_version(self):
        """
        get the latest version of this object
        """
        self.ensure_one()
        return self.search([
            ('engineering_code', '=', self.engineering_code)
        ], order='engineering_revision DESC', limit=1)

    def get_previus_version(self):
        self.ensure_one()
        return self.search([
            ('engineering_code', '=', self.engineering_code),
            ('engineering_revision', '=', self.engineering_revision - 1)
        ], limit=1)

    def get_next_version(self):
        self.ensure_one()
        return self.search([
            ('engineering_code', '=', self.engineering_code),
            ('engineering_revision', '=', self.engineering_revision + 1)
        ], limit=1)

    def get_released(self):
        self.ensure_one()
        return self.search([
            ('engineering_code', '=', self.engineering_code),
            ('engineering_state', 'in', [UNDER_MODIFY_STATUS, RELEASED_STATUS])
        ])

    def get_all_revision(self):
        self.ensure_one()
        return self.search([
            ('engineering_code', '=', self.engineering_code)
        ], order='engineering_revision DESC')

    def write(self, vals):
        if 'engineering_code' in vals and vals[
            'engineering_code'] not in [False, '-', '']:
            vals['engineering_code_editable'] = False
        else:
            for record in self:
                if record.engineering_code and record.engineering_code_editable == True:
                    vals['engineering_code_editable'] = False
        return super(RevisionBaseMixin, self).write(vals)

    @api.model_create_multi
    def create(self, vals):
        for record_val in vals:
            if 'engineering_code' in record_val and record_val[
                'engineering_code'] not in [False, '-', '']:
                record_val['engineering_code_editable'] = False
        return super(RevisionBaseMixin, self).create(vals)

    def get_display_notification(self, message):
        return {'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': message,
                    'sticky': False,
                    'type': 'info',
                }}

    def translate_plm_m2o_name(self, objs, field_name, field_value):
        if field_value:
            for obj in objs:
                field_def = obj.fields_get(field_name)
                relation = field_def.get(field_name, {}).get('relation', '')
                if not relation:
                    logging.warning(
                        "PLM Many2one relation on field %s not found" % field_name
                    )
                    continue
                object_browse_id = None
                for object_browse_id in self.env[relation].search([
                    ('name', '=', field_value)
                ]):
                    break
                if not object_browse_id:
                    object_browse_id = self.env[relation].create({
                        'name': field_value
                    })
                return object_browse_id.id
        return field_value

    @api.model
    def get_all_translation(self, object_id, fields):
        """
        get all field translated in all available languages
        """
        out = {}
        obj = self.env[self._name].search([('id', '=', object_id)])
        if obj:
            for field_name in fields:
                for code in self.env['res.lang'].search([
                    ('active', '=', True)
                ]).mapped("code"):
                    propKey = f"{field_name}@-@-@{code}"
                    out[propKey] = getattr(obj.with_context(lang=code), field_name)
        return out

    @api.model
    def get_possible_status(self):
        out = []
        for model_id in self.env['ir.model'].sudo().search([
            ('model', '=', self._name)
        ]):
            for filed_id in self.env['ir.model.fields'].sudo().search([
                ('model_id', '=', model_id.id),
                ('name', '=', 'engineering_state')
            ]):
                for ir_model_fields_selection in self.env[
                    'ir.model.fields.selection'].sudo().search([
                    ('field_id', '=', filed_id.id)]):

                    out.append((ir_model_fields_selection.name,
                                ir_model_fields_selection.value))
        return out
