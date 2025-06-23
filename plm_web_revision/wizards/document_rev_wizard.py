import logging
from odoo import _, models
from odoo.exceptions import UserError


class PlmDocumentExtended(models.TransientModel):
    _name = "document.rev_wizard"
    _description = "Document Revision Wizard"

    def new_document_revision_by_server(self):
        document_id = self.env.context.get("default_document_id", False)
        if not document_id:
            logging.error(
                "[new_document_revision_by_server] Cannot revise because"
                " document_id is %r" % (document_id)
            )
            raise UserError(_("Current document cannot be revised!"))
        plmDocEnv = self.env["ir.attachment"]
        docBrws = plmDocEnv.browse(document_id)
        if docBrws.document_type != "other":
            raise UserError(
                _(
                    "Document cannot be revised because the document"
                    "type is a CAD type document!"
                )
            )
        if self.stateAllows(docBrws, "Document"):
            newID, _newIndex = docBrws.NewRevision(docBrws.id)
            if not newID:
                logging.error("[new_document_revision_by_server] newID: %r" % (newID))
                raise UserError(
                    _("Something wrong happens during new document revision process.")
                )
            return {
                "name": _("Revised Document"),
                "view_type": "list,form",
                "view_mode": "form",
                "res_model": "ir.attachment",
                "res_id": newID,
                "type": "ir.actions.act_window",
            }

    def stateAllows(self, brwsObj, objType):
        if brwsObj.engineering_state != "released":
            logging.error(
                "[new_document_revision_by_server:stateAllows] Cannot revise"
                " obj %s, Id: %r because state is %r"
                % (objType, brwsObj.id, brwsObj.engineering_state)
            )
            raise UserError(
                _("%s cannot be revised because the state isn't released!" % (objType))
            )
        return True
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
