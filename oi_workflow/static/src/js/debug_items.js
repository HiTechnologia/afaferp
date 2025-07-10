/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { editModelDebug } from "@web/core/debug/debug_utils";
const debugRegistry = registry.category("debug");

export function editWorkflow({env, action}) {
    const description = _t("Approval Settings");
    return {
        type: "item",
        description,
        callback: async () => {
            const res_id = await env.services.orm.search("approval.settings", [["model","=", action.res_model]]);
            if (res_id.length) {
                return editModelDebug(env, description, "approval.settings", res_id[0]);
            }

            env.services.action.doAction({
                res_model: "approval.settings",
                name: description,
                type: "ir.actions.act_window",
                views: [[false, "list"],[false, "form"]],
                view_mode: "list, form",
                target: "current",
            });
        },
        sequence: 222,
        section: "ui",
    };

}

debugRegistry.category("action").add("editWorkflow", editWorkflow);

