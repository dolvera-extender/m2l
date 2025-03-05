/** @odoo-module **/
import { registry } from '@web/core/registry';
import { FormRenderer } from '@web/views/form/form_renderer';
import { formView } from "@web/views/form/form_view";
console.log(formView);
import { useService } from '@web/core/utils/hooks';

class IaBarcodeFormViewRenderer extends FormRenderer {
    setup() {
        super.setup();
        this.orm = useService("orm");
    }

    onKeyupPnrf(ev) {
        if (ev.key === 'Enter') {
            const inp = document.querySelector(".pnrf");
            if (inp) {
                inp.dispatchEvent(new Event('change', { bubbles: true }));
            }
        }
    }

    get events() {
        return {
            ...super.events,
            'keyup .pnrf': this.onKeyupPnrf.bind(this),
        };
    }
}

const IaBarcodeFormView = {
    ...formView, // Copiamos todas las propiedades de formView
    type: "form",
    display_name: "IA Barcode Form",
    Renderer: IaBarcodeFormViewRenderer, // Usamos nuestro renderer personalizado
};

registry.category("views").add("ia_barcodejs_form", IaBarcodeFormView);
