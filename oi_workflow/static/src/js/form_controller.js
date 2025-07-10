/** @odoo-module */

import { FormController } from '@web/views/form/form_controller';
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { evaluateBooleanExpr,evaluateExpr } from "@web/core/py_js/py";
import { user } from "@web/core/user";

patch(FormController.prototype, {

	async beforeExecuteActionButton(clickParams) {

		const validate_form = clickParams.validate_form && evaluateBooleanExpr(clickParams.validate_form);
		if (validate_form === false)
			return true;
		const record = this.model.root;		

		if (clickParams.name && clickParams.name.indexOf("approval")===0 && "approved_button_clicked" in record.activeFields) {			
			await record.update({approved_button_clicked: JSON.parse(clickParams.args || "[true]")[0]});
		}

		if (clickParams.approved_button_clicked !== undefined) {
			await record.update({approved_button_clicked: evaluateExpr(clickParams.approved_button_clicked)});
		}

		if (validate_form) {			
			const isFormValid = await record.checkValidity({displayNotification : true});
			if (!isFormValid) return false;
		}		
		return super.beforeExecuteActionButton(clickParams);
	},

	getStaticActionMenuItems() {
		const res = super.getStaticActionMenuItems();
		Object.assign(res, {
			approval_log: {
				isAvailable: () => "user_can_approve" in this.model.root.activeFields && !this.model.root.activeFields.user_can_approve.related,
				sequence: 100,
				icon: "fa fa-arrows-h",
				description: _t("Approval Log"),
				callback: async () => {
					const { resModel, resId } = this.model.root;
					const action = {
					    name: _t('Approval Log'),
					    res_model: 'approval.log',
					    type: 'ir.actions.act_window',
					    views: [[false, 'list']],
					    view_mode: 'list',
					    domain : [
							['model','=', resModel],
							['record_id','=', resId],
						],					    
						context: {
							hide_record: true,
							hide_model: true
						}
					};
					this.env.services.action.doAction(action);
				}
			},
			update_status : {
				isAvailable: () => "state" in this.model.root.activeFields && user.isSystem,
				sequence: 100,
				icon: "fa fa-code",
				description: _t("Update Status"),
				callback: async () => {
					const action = {
					    name: _t('Change Document Status'),
					    res_model: 'approval.state.update',
					    type: 'ir.actions.act_window',
					    views: [[false, 'form']],
					    view_mode: 'form',
					    target : 'new',					    
						context: {
							default_res_model : this.model.root.resModel,
							default_res_ids : [this.model.root.resId],
						}
					};
					const options = {
						onClose : () => {
							this.model.root.load();
						}
					}
					await this.env.services.action.doAction(action, options);
					
				}
			}
		});
		return res;
	},
});
