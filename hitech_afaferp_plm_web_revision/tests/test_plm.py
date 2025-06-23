import logging
import datetime
from odoo import models
from odoo import Command
from odoo import fields
from odoo import api
from odoo import _
from odoo.tests import tagged
from odoo.exceptions import UserError
from datetime import timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tests.common import TransactionCase
from odoo.addons.plm.models.plm_mixin import RELEASED_STATUS
from odoo.addons.plm.models.plm_mixin import UNDER_MODIFY_STATUS
from odoo.addons.plm.models.plm_mixin import START_STATUS
from odoo.addons.plm.models.plm_mixin import CONFIRMED_STATUS
from odoo.addons.plm.models.plm_mixin import OBSOLATED_STATUS
from odoo.addons.plm.tests.entity_creator import PlmEntityCreator
#
#
# --test-tags=odoo_plm
#
#
DUMMY_CONTENT = b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="
#
@tagged('-standard', 'odoo_plm_web_revision')
class PlmDateBom(TransactionCase,PlmEntityCreator):
    
    def test_product_attachment_wk(self):
        product, document = self.create_product_document("test_product_attachment_wk")
        product.action_confirm()
        product.action_release()
        #
        wiz_obj = self.env['product.rev_wizard'].create({"reviseDocument":True})
        wiz_obj.with_context(active_id=product.id,
                             active_model='product.product').action_create_new_revision_by_server()
        #
        assert product.product_tmpl_id.get_latest_version().engineering_revision==1
        assert document.get_latest_version().engineering_revision==1                   
        
    def test_bom_wk(self):
        new_bom = self.create_bom_with_document("test_bom_wk")
        product = new_bom.product_id
        product.action_confirm()
        product.action_release()
        wiz_obj = self.env['product.rev_wizard'].create({"reviseDocument":True,
                                                         'reviseNbom':True})
        wiz_obj.with_context(active_id=product.id,
                             active_model='product.product').action_create_new_revision_by_server()
        
        