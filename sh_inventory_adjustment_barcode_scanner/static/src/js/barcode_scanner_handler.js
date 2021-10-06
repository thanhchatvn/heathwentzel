odoo.define('sh_inventory_adjustment_barcode_scanner.sh_stock_adjust_bar_scan', function (require) 
{"use strict";
	var AbstractField = require('web.AbstractField');
	var core = require('web.core');
	var field_registry = require('web.field_registry');
	var field_utils = require('web.field_utils');
	var Class = require('web.Class');
	var utils = require('web.utils');
	var barcode_fields=require('barcodes.field');
	var barcode_form_view = require('barcodes.FormView');

	var QWeb = core.qweb;

	var BarcodeEvents = require('barcodes.BarcodeEvents'); // handle to trigger barcode on bus
	var concurrency = require('web.concurrency');
	var core = require('web.core');
	var Dialog = require('web.Dialog');
	var FormController = require('web.FormController');
	var FormRenderer = require('web.FormRenderer');

	var _t = core._t;

var sh_barcode = FormController.include({
    _barcodeScanned: function (barcode, target) {
        var url = window.location.href;
        //to get the id
        url=url.match(new RegExp('id=' + "(.*)" + '&'));
        url=String(url);
        var start_pos = url.indexOf('=') + 1;
        var end_pos = url.indexOf('&',start_pos);
        var id = url.substring(start_pos,end_pos);

        //to get the model name
        url=url.match('model=' + "(.*)" + '&');
        url=String(url);
        var start_pos = url.indexOf('=') + 1;
        var end_pos = url.indexOf('&',start_pos);
        var model = url.substring(start_pos,end_pos);

        //to finds the model in string
        var models = ["stock.inventory"];
        var is_model_found = models.indexOf(model);

        //check whether record Saved or Not
        if(is_model_found != -1 && id == false)
        {
        	alert("Please Select Partner And Save/Confirm");
        }
        //check conditon to match in our critearea than call the function
        if(is_model_found != -1 && id !=false && barcode !=false  ){
            var self = this;
            this._rpc({
                model: model,
                method: 'sh_on_barcode_scanned',
                args: [parseInt(id),barcode],
            }).then(function () {
                self.trigger_up('reload');
            });
        }
        if (is_model_found != 0 && model != 'stock.inventory'){
            var self = this;
            return this.barcodeMutex.exec(function () {
            var prefixed = _.any(BarcodeEvents.ReservedBarcodePrefixes,
                    function (reserved) {return barcode.indexOf(reserved) === 0;});
            var hasCommand = false;
            var defs = [];
            for (var k in self.activeBarcode) {
                var activeBarcode = self.activeBarcode[k];
                // Handle the case where there are several barcode widgets on the same page. Since the
                // event is global on the page, all barcode widgets will be triggered. However, we only
                // want to keep the event on the target widget.
                if (! $.contains(target, self.el)) {
                    continue;
                }

                var methods = self.activeBarcode[k].commands;
                var method = prefixed ? methods[barcode] : methods.barcode;
                if (method) {
                    if (prefixed) {
                        hasCommand = true;
                    }
                    defs.push(self._barcodeActiveScanned(method, barcode, activeBarcode));
                }
            }
            if (prefixed && !hasCommand) {
                self.do_warn(_t('Error : Barcode command is undefined'), barcode);
            }
            return self.alive($.when.apply($, defs)).then(function () {
                if (!prefixed) {
                    // redraw the view if we scanned a real barcode (required if
                    // we manually apply the change in JS, e.g. incrementing the
                    // quantity)
                    self.update({}, {reload: false});
                }
            });
        });
        }
    },
});


field_registry.add('sh_stock_adjust_bar_scan', sh_barcode);

});
