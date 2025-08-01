from odoo_test_helper import FakeModelLoader

from odoo.tests import common


class TestBaseRevision(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.loader = FakeModelLoader(cls.env, cls.__module__)
        cls.loader.backup_registry()
        from .base_revision_tester import BaseRevisionTester

        cls.loader.update_registry((BaseRevisionTester,))

        cls.revision_model = cls.env[BaseRevisionTester._name]

    @classmethod
    def tearDownClass(cls):
        cls.loader.restore_registry()
        return super().tearDownClass()

    def _create_tester(self, vals_list=None):
        if not vals_list:
            vals_list = [{}]
        for vals in vals_list:
            if "name" not in vals:
                vals["name"] = "TEST0001"
        return self.revision_model.create(vals_list)

    @staticmethod
    def _revision_tester(tester):
        # Cancel the tester
        tester.action_cancel()
        # Create a new revision
        return tester.create_revision()

    def test_revision(self):
        """Check revision process"""
        # Create a Tester document
        tester_1 = self._create_tester()

        # Create a revision of the Tester
        self._revision_tester(tester_1)

        # Check the previous revision of the tester
        revision_1 = tester_1.current_revision_id
        self.assertEqual(tester_1.state, "cancel")

        # Check the current revision of the tester
        self.assertEqual(revision_1.unrevisioned_name, tester_1.name)
        self.assertEqual(revision_1.state, "draft")
        self.assertTrue(revision_1.active)
        self.assertEqual(revision_1.old_revision_ids, tester_1)
        self.assertEqual(revision_1.revision_number, 1)
        self.assertEqual(revision_1.name.endswith("-01"), True)
        self.assertEqual(revision_1.has_old_revisions, True)
        self.assertEqual(revision_1.revision_count, 1)

        # Create a new revision of the tester
        self._revision_tester(revision_1)
        revision_2 = revision_1.current_revision_id

        # Check the previous revision of the tester
        self.assertEqual(revision_1.state, "cancel")
        self.assertFalse(revision_1.active)

        # Check the current revision of the tester
        self.assertEqual(revision_2.unrevisioned_name, tester_1.name)
        self.assertEqual(revision_2, tester_1.current_revision_id)
        self.assertEqual(revision_2.state, "draft")
        self.assertTrue(revision_2.active)
        self.assertEqual(revision_2.old_revision_ids, tester_1 + revision_1)
        self.assertEqual(revision_2.revision_number, 2)
        self.assertEqual(revision_2.name.endswith("-02"), True)
        self.assertEqual(revision_2.has_old_revisions, True)
        self.assertEqual(revision_2.revision_count, 2)

    def test_simple_copy(self):
        """Check copy process"""
        # Create a tester
        tester_2 = self._create_tester()
        # Check the 'Order Reference' of the tester
        self.assertEqual(tester_2.name, tester_2.unrevisioned_name)

        # Copy the tester
        tester_3 = tester_2.copy({"name": "TEST0002"})
        # Check the 'Reference' of the copied tester
        self.assertEqual(tester_3.name, tester_3.unrevisioned_name)

    def test_create_multiple(self):
        """Check copy process"""
        # Create a tester
        tester_2 = self._create_tester([{"name": "TEST0001"}, {"name": "TEST0002"}])
        # Check the 'Order Reference' of the tester
        for tester in tester_2:
            self.assertEqual(tester.name, tester.unrevisioned_name)
