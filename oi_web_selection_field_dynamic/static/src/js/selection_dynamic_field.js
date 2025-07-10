/** @odoo-module **/
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { SelectionField,selectionField } from "@web/views/fields/selection/selection_field";
import { useSpecialData } from "@web/views/fields/relational_utils";
import { useService } from "@web/core/utils/hooks";
import { evaluateExpr } from "@web/core/py_js/py";

export function tryEvaluateExpr (value, context = {}) {
    if (value === "state") return value;
    try {
        return evaluateExpr(value, context);
    }
    catch {};
    return value;            
}

export class SelectionFieldDynamic extends SelectionField {
    static props = {
        ...SelectionField.props,
        selection_model: { type: String, optional: true },
        selection_field: { type: String, optional: true },
        selection_value_field: { type: String, optional: true },
        visible_selections: { optional: true },
    }

    setup() {
        this.type = "selection";
        this.fieldService = useService("field");
        this.specialData = useSpecialData((orm, props) => {
            const selection_model = props.selection_model ? tryEvaluateExpr(props.selection_model, props.record.evalContext) : props.record.resModel;
            const selection_field = props.selection_field ? tryEvaluateExpr(props.selection_field, props.record.evalContext) : props.name; 
            if (!selection_model || !selection_field) return null;            
            return this.fieldService.loadFields(selection_model, {fieldNames: [selection_field], attributes : ["selection"]})
        });
    }

    get options() {
        let {_options} = this;
        let {visible_selections, record} = this.props;
        if (visible_selections) {
            visible_selections = tryEvaluateExpr(visible_selections, record.evalContext);
            if (typeof visible_selections== "string")
                visible_selections = visible_selections.split(",");
            _options = _options.filter((s) => visible_selections.includes(s[0]));
        }
        return _options.map(s => this.getOption(s));
    }

    getOption(option) {
        if (this.env.debug) {
            return [option[0], `${option[1]} (${option[0]})`];
        }
        return option;
    }

    get _options() {
        if (this.props.selection_value_field !== undefined) {
            let selections= this.props.record.data[this.props.selection_value_field];
            if (typeof selections ==="string") {
                selections = JSON.parse(selections);
            }
            return selections || [];
        }
        const selection_field = tryEvaluateExpr(this.props.selection_field, this.props.record.evalContext);
        const fieldInfo = this.specialData.data?.[selection_field];
        return fieldInfo === undefined ? [] : [...fieldInfo.selection];
    }

    get string() {
        const rawValue = this.props.record.data[this.props.name];
        if (!rawValue) return "";
        const item = this._options.find((o) => o[0] === rawValue);
        return item && item[1] || "";
    }

    get value() {
        return this.props.record.data[this.props.name];
    }
}

export const selectionFieldDynamic = {
    ...selectionField,
    component: SelectionFieldDynamic,
    supportedTypes: ["char"],
    extractProps({ attrs, viewType, options }, dynamicInfo) {
        const props = {
            autosave: viewType === "kanban",
            placeholder: attrs.placeholder,
            required: dynamicInfo.required,
            domain: dynamicInfo.domain(),
            selection_model: attrs.selection_model || options.selection_model,
            selection_field: attrs.selection_field || options.selection_field,
            selection_value_field: attrs.selection_value_field || options.selection_value_field,
            visible_selections : attrs.visible_selections || options.visible_selections
        };
        if (viewType === "kanban") {
            props.readonly = dynamicInfo.readonly;
        };
        return props;
    },
};

registry.category("fields").add("selection_dynamic", selectionFieldDynamic);
registry.category("fields").add("kanban.selection_dynamic", selectionFieldDynamic);
