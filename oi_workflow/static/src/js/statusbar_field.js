/** @odoo-module */

import { StatusBarField } from '@web/views/fields/statusbar/statusbar_field';
import { patch } from "@web/core/utils/patch";

patch(StatusBarField.prototype, {	
	
	getAllItems() {
		const { visibleSelection, name, record } = this.props;
		if (visibleSelection?.includes("WORKFLOW") && name ==="state") {			
			const currentValue = record.data[name];
			const workflow_states = record.data["workflow_states"];
			if (workflow_states) {
				let { selection } = this.field;
				selection = selection.filter(
					([value]) => value === currentValue || visibleSelection.includes(value) || workflow_states.includes(value)
				);
				return selection.map(([value, label]) => ({
					value,
					label,
					isFolded: false,
					isSelected: value === currentValue,
				}));	
			}
		}
		return super.getAllItems();
	}

});

