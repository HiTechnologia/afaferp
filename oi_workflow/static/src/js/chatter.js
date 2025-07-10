/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { Chatter } from "@mail/chatter/web_portal/chatter";

patch(Chatter.prototype, {

    get activities() {
        return super.activities.filter((a) => !a.hide_in_chatter);
    },    
    
});