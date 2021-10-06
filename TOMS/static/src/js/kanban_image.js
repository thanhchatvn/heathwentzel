odoo.define('TOMS.KanBanImage', function (require) {
    "use strict";

    var ControlPanelMixin = require('web.ControlPanelMixin');
    var AbstractAction = require('web.AbstractAction');
    var Widget = require('web.Widget');
    var rpc = require('web.rpc');
    var view_dialogs = require('web.view_dialogs');
    var rpc = require('web.rpc');
    var session = require('web.session');
    var core = require('web.core');
    var Dialog = require('web.Dialog');
    var dialogs = require('web.view_dialogs');
    var ListRenderer = require('web.ListRenderer');
    var KanbanRecord = require('web.KanbanRecord')

    var QWeb = core.qweb;
    var _t = core._t;
    var ajax = require('web.ajax');


    KanbanRecord.include({
        init: function (parent, state, options) {
            var self = this;
            this._super.apply(this, arguments);
        },

        _openRecord: function (events) {
            if (this.$el.hasClass('o_currently_dragged')) {
            // this record is currently being dragged and dropped, so we do not
            // want to open it.
                return;
            }
            if (this.$el.hasClass('oe_kanban_image_zoom')){
                 var src = this.$el.find('img').attr('src')
                 var params  = 'width='+screen.width;
                 params += ', height='+screen.height;
                 params += ', top=0, left=0'
                 params += ', fullscreen=yes';
                 window.open(src,  null, params);

            }
            else{
                var editMode = this.$el.hasClass('oe_kanban_global_click_edit');
                this.trigger_up('open_record', {
                    id: this.db_id,
                    mode: editMode ? 'edit' : 'readonly',
                });
            }
        },

    });
});