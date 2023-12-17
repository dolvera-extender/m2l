odoo.define('inventory_audit.IaBarcodeReaderFormView', function (require) {
    "use strict";
    
    var FormRenderer = require('web.FormRenderer');
    var FormView = require('web.FormView');
    var viewRegistry = require('web.view_registry');
    var BarcodeScanner = require('@web_enterprise/webclient/barcode/barcode_scanner')[Symbol.for("default")];
    
    
    var IaBarcodeFormViewRenderer = FormRenderer.extend({
        events: _.extend({}, FormRenderer.prototype.events, {
            'document ready': function (){
                $(".pnrf").focus();
            },
            'keyup .pnrf':'_onKeyupPnrf'
        }),
        init: function () {
            this._super.apply(this, arguments);
            console.log("THIS INIT 1");
            console.log(this);
            // var isMobileBcScanner = BarcodeScanner.isBarcodeScannerSupported();
            // console.log(isMobileBcScanner);
            
        },
        _onKeyupPnrf: function (e){
            if(e.key === 'Enter'){
                var inp = $(".pnrf");
                inp.change();            
            }
        }

    });
    
    var IaBarcodeFormView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Renderer: IaBarcodeFormViewRenderer,
        }),
    });
    
    viewRegistry.add('ia_barcodejs_form', IaBarcodeFormView);
    
    return {
        IaBarcodeFormViewRenderer: IaBarcodeFormViewRenderer,
        IaBarcodeFormView: IaBarcodeFormView,
    };
    });
    