from . import base
from . import plm_mixin
from . import product_product_document_rel
from . import plm_treatment
from . import plm_finishing
from . import plm_material
from . import product_template
from . import plm_descriptions             # Has to be before "product_product_extension" due to related field
from . import product_product              # Has to be before "ir_attachment" due to related field
from . import ir_attachment                # Has to be before "ir_attachment_relations" due to related field
from . import ir_attachment_relations
from . import product_product_kanban
from . import product_category
from . import plm_backup_document
from . import plm_checkout
from . import res_config_settings
from . import mrp_bom
from . import mrp_bom_line
from . import report_on_document
from . import plm_temporary
from . import plm_dbthread
from . import res_users
from . import plm_cad_open
from . import ir_ui_view
from . import plm_cad_open_bck
from . import mail_activity_type
from . import plm_client
from . import res_groups
from . import utils
from . import stock_move
