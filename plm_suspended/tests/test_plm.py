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
from odoo.addons.plm.models.plm_mixin import START_STATUS
from odoo.addons.plm.models.plm_mixin import CONFIRMED_STATUS
from odoo.addons.plm.models.plm_mixin import RELEASED_STATUS
from odoo.addons.plm.models.plm_mixin import UNDER_MODIFY_STATUS
from odoo.addons.plm.models.plm_mixin import OBSOLATED_STATUS

#
from odoo.addons.plm.tests.entity_creator import PlmEntityCreator

#
#
# --test-tags=odoo_plm
#
#
DUMMY_CONTENT = b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="
#
@tagged("-standard", "odoo_plm_suspended")
class PlmDateBom(TransactionCase, PlmEntityCreator):
    def perform_check_suspend(self, obj):
        obj.action_suspend()
        assert obj.engineering_state == suspended, (
            "wrong state %s" % product.engineering_state
        )
        obj.action_unsuspend()
        assert obj.engineering_state == START_STATUS, (
            "wrong state %s" % product.engineering_state
        )

    def test_product_attachment_wk(self):
        #
        # product
        #
        product = self.create_product_product("test_product_attachment_wk_p")
        self.perform_check_suspend(product)
        product.action_confirm()
        self.perform_check_suspend(product)
        product.action_release()
        self.perform_check_suspend(product)
        #
        # document
        #
        product = self.create_document("test_product_attachment_wk_d")
        self.perform_check_suspend(product)
        product.action_confirm()
        self.perform_check_suspend(product)
        product.action_release()
        self.perform_check_suspend(product)
