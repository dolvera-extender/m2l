/** @odoo-module **/

import {registry} from '@web/core/registry';
import {useState} from '@odoo/owl';
import {useBus, useService} from "@web/core/utils/hooks";


import {session} from '@web/session';
import { _t } from "@web/core/l10n/translation";

import * as BarcodeScanner from "@web/webclient/barcode/barcode_scanner";
import {Component, onWillStart} from "@odoo/owl";
import {serializeDate, today} from "@web/core/l10n/dates";

class MainMenu extends Component {
    setup() {
        const displayDemoMessage = this.props.action.params.message_demo_barcodes;
        const user = useService('user');
        this.orm = useService("orm");
        this.actionService = useService('action');
        this.dialogService = useService('dialog');
        this.home = useService("home_menu");
        this.notification = useService("notification");
        this.rpc = useService('rpc');
        this.state = useState({displayDemoMessage});
        this.barcodeService = useService('barcode');
        useBus(this.barcodeService.bus, "barcode_scanned", (ev) => this._onBarcodeScanned(ev.detail.barcode));
        const orm = useService('orm');

        this.mobileScanner = BarcodeScanner.isBarcodeScannerSupported();

        onWillStart(async () => {
            this.locationsEnabled = await user.hasGroup('stock.group_stock_multi_locations');
            this.packagesEnabled = await user.hasGroup('stock.group_tracking_lot');
            const args = [
                ["user_id", "=?", session.uid],
                ["location_id.usage", "in", ["internal", "transit"]],
                ["inventory_date", "<=", serializeDate(today())],
            ]
            this.quantCount = await orm.searchCount("stock.quant", args);
        });

    }

    async onClickBarcode() {
        console.log("CHECANDO ANDO .. ");
        const barcode = await BarcodeScanner.scanBarcode(this.env);
        console.log("ESCANEANDO ... ", barcode);
        if (barcode) {
            this._onBarcodeScanned(barcode);
            if ('vibrate' in window.navigator) {
                window.navigator.vibrate(100);
            }
        } else {
            this.displayNotification(_t("Por favor, escanea de nuevo"))
        }
    }

    displayNotification(text){
        this.notification.add(text, { type: "warning" });
    }

    _onBarcodeScanned(barcode) {

        this.orm.call('ia.packages.audit.wizard', 'obtain_action',[], {
            barcode: barcode,
        }).then(result => {
            if (result.action) {
                this.actionService.doAction(result.action);
            } else if (result.warning) {
                this.displayNotification(_t(result.warning))
            }
        });
    }
}

MainMenu.template = "ia_main_menu";


// Registrar la acción correctamente en Odoo 17
registry.category("actions").add("inventory_audit.ia_getlocation_barcode_main_menu", MainMenu);
