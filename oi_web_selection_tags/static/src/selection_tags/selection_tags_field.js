
/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { TagsList } from "@web/core/tags_list/tags_list";
import { useSpecialData } from "@web/views/fields/relational_utils";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { useTagNavigation } from "@web/core/record_selectors/tag_navigation_hook";
import { evaluateExpr } from "@web/core/py_js/py";

export function tryEvaluateExpr (value, context = {}) {
    if (value === "state") return value;
    try {
        return evaluateExpr(value, context);
    }
    catch {};
    return value;            
}

export class SelectionTagsField extends Component {
    static template = "oi_web_selection_tags.SelectionTagsField";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
        required: { type: Boolean, optional: true },        
        autosave: { type: Boolean, optional: true },        
        selection_model: { type: String, optional: false },
        selection_field: { type: String, optional: false },
    }
    static components = {
        TagsList
    };

    setup() {
        this.type = this.props.record.fields[this.props.name].type;
        this.fieldService = useService("field");
        this.specialData = useSpecialData((orm, props) => {
            const selection_model = tryEvaluateExpr(props.selection_model, props.record.evalContext);
            const selection_field = tryEvaluateExpr(props.selection_field, props.record.evalContext);
            if (!selection_model || !selection_field) return null;            
            return this.fieldService.loadFields(selection_model, {fieldNames: [selection_field], attributes : ["selection"]})
        });
        this.onTagKeydown = useTagNavigation(
            "selectionTagsField",
            this.deleteTagByIndex.bind(this)
        );
    }

    get selection() {
        const selection_field = tryEvaluateExpr(this.props.selection_field, this.props.record.evalContext);
        const fieldInfo = this.specialData.data?.[selection_field];
        return fieldInfo === undefined ? [] : [...fieldInfo.selection];        
    }

    get options() {
        return this.selection.filter(sel => !this.values.includes(sel[0])).map(s => this.getOption(s));
    }

    get values() {
        const value = this.props.record.data[this.props.name];
        if (typeof value === "string") {
            return value.split(",");
        }
        if (Array.isArray(value)) {
            return value;
        }
        return [];
    }

    getOptionString(value) {
        const {options} = this.options;
        if (!options) return value;
        return this.options.find((o) => o[0] === v)[1] || value;
    }

    get string() {
        //const res = [];
        //this.values.forEach(v => res.push(this.options.find((o) => o[0] === v)[1]));
        //return res.join(",");
        return this.values.map((s) => this.getOptionString(s)).join(",");
    }

	get tags() {
		return this.selection.filter(sel => this.values.includes(sel[0])).map(s => this.getTagProps(s));
	}

    stringify(value) {
        return JSON.stringify(value);
    }
	
    getOption(option) {
        if (this.env.debug) {
            return [option[0], `${option[1]} (${option[0]})`];
        }
        return option;
    }
    
    getTagProps(selection) {
        const debug = this.env.debug;
        return {
            id: selection[0],
            resId: selection[0],
            text: debug ? `${selection[1]} (${selection[0]})` : selection[1],
            colorIndex: undefined,
            onDelete: !this.props.readonly ? () => this.deleteTag(selection[0]) : undefined,
            onKeydown: (ev) => {
                if (this.props.readonly) {
                    return;
                }
                this.onTagKeydown(ev);
            },
        };
    }

    async deleteTagByIndex(index) {
        const { id } = this.tags[index] || {};
        this.deleteTag(id);
    }

    async deleteTag(value) {
		this.update({remove_value: value});
	}

    async update({add_value, remove_value}) {
        let value = this.values;
        if (add_value) value.push(add_value);
        if (remove_value) value = value.filter(v => v != remove_value);
        if (this.type === "char") {
            value = value.join(",");
        }
        await this.props.record.update({ [this.props.name]: value }, { save: this.props.autosave });
    }

    onChange(ev) {
		const value = JSON.parse(ev.target.value);
		if (value) {
			this.update({add_value: value});
		}
	}		
}

export const selectionTagsField = {
    component: SelectionTagsField,
    supportedTypes: ["char", "json"],
    extractProps({ attrs, viewType, options }, dynamicInfo) {
        const props = {
            autosave: viewType === "kanban",
            placeholder: attrs.placeholder,
            required: dynamicInfo.required,
            selection_model: attrs.selection_model || options.selection_model,
            selection_field: attrs.selection_field || options.selection_field,
        };
        if (viewType === "kanban") {
            props.readonly = dynamicInfo.readonly;
        };
        return props;
    },
};

registry.category("fields").add("selection_tags", selectionTagsField);
registry.category("fields").add("kanban.selection_tags", selectionTagsField);
