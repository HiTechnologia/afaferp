/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ViewButton } from "@web/views/view_button/view_button";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { Component } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";

export class ApprovalUserInfo extends Component {
    static template = "oi_workflow.ApprovalUserInfo";
}

patch(ViewButton.prototype, {
    setup() {
        super.setup(...arguments);
        this.is_approval_user_info = this.props.id === "approval_user_info";
        if (this.is_approval_user_info) {
            this.orm = useService("orm");
            this.approval_user_info_popover = usePopover(ApprovalUserInfo);
        }
        else if (this.props.clickParams.args || this.props.clickParams.validate_form) {
            const tooltip = JSON.parse(this.tooltip);
            tooltip.button.args = this.props.clickParams.args;
            tooltip.button.validate_form = this.props.clickParams.validate_form;
            this.tooltip = JSON.stringify(tooltip);    
        }
    },

    get hasBigTooltip() {
        if (this.is_approval_user_info) return false;
        return super.hasBigTooltip;
    },

    get hasSmallToolTip() {
        if (this.is_approval_user_info) return false;
        return super.hasSmallToolTip;
    },

    async onClickApprovalUserInfo(ev) {
        const {resId, resModel} = this.props.record;
        const specification = {
            approval_user_ids : {fields : {display_name : {}}},
            approval_done_user_ids: {fields : {display_name : {}}}
        };
        const [props] = await this.orm.webRead(resModel, [resId], {specification});        
        props.show_login_as = this.env.debug && user.isSystem;
        props.uid = user.userId;
        props.redirect = browser.location.pathname + browser.location.search + browser.location.hash;
        this.approval_user_info_popover.open(ev.target, props);
    },

    onClick(ev) {
        if (this.is_approval_user_info) {
            return this.onClickApprovalUserInfo(ev);
        }
        return super.onClick(...arguments);
    }
});
