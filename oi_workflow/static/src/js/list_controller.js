/** @odoo-module */

import { ListController } from '@web/views/list/list_controller';
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { user } from "@web/core/user";

patch(ListController.prototype, {

	setup() {
		super.setup();
		this.show_action_approve_all = this.archInfo.xmlDoc.getAttribute("show_action_approve_all") || false;
	},

	getStaticActionMenuItems() {
		const res = super.getStaticActionMenuItems();
		const actionOptions = {
			onClose : () => {
				this.model.root.load();
			}
		}
		Object.assign(res, {
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
							default_res_ids : await this.model.root.getResIds(true),
						}
					};
					this.env.services.action.doAction(action, actionOptions);
				}
			},
			approve: {
				isAvailable: () => this.show_action_approve_all,
				sequence: 110,
				icon: "fa fa-thumbs-up",
				description: _t("Approve"),
				callback: async () => {
					const dialogProps = {
						body: _t("Are you sure you want to approve selected documents?"),
						confirm: async () => {
							const ids = await this.model.root.getResIds(true);
							const action = await this.model.orm.call(this.model.root.resModel, "action_approve_all", [ids]);
							this.actionService.doAction(action, actionOptions);
						},
						cancel: () => {},
					}
					await this.dialogService.add(ConfirmationDialog, dialogProps);
				}
			},
			approve_log: {
				isAvailable: () => "user_can_approve" in this.model.root.fields && !this.model.root.fields.user_can_approve.related,
				sequence: 120,
				icon: "fa fa-arrows-h",
				description: _t("Approval Log"),
				callback: async () => {
					const ids = await this.model.root.getResIds(true);
					const action = {
					    name: _t('Approval Log'),
					    res_model: 'approval.log',
					    type: 'ir.actions.act_window',
					    views: [[false, 'list']],
					    view_mode: 'list',
					    domain : [
							['model','=', this.model.root.resModel],
							['record_id','in', ids],
						],					    
						context: {
							hide_record: false,
							hide_model: true
						}
					};
					this.env.services.action.doAction(action);
				}
			}

		});
		return res;
	},
});
