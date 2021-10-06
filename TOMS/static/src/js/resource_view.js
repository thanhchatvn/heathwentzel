odoo.define('TOMS.resource_view', function (require) {
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

        var QWeb = core.qweb;
        var _t = core._t;
        var ajax = require('web.ajax');

        var AppointmentRosterView = AbstractAction.extend(ControlPanelMixin, {
            title: core._t('Appointment Roster View'),
            template: 'ResourceViewId',

            custom_events: _.extend({}, AbstractAction.prototype.custom_events, {
                changeDate: '_onChangeDate',
                openEvent:'_onOpenEvent',
            }),
            init: function (parent, params) {
                this._super.apply(this, arguments);
                var self = this;
                this.action_manager = parent;
                this.params = params;
                this.optometrist = Array();
                this.optometristList = Array();
                this.optometristFinalList = Array();
                this.optometristUserList = Array();
                this.context = this.params.context;
                this.moment_date = moment();
                this.availableTags = [];
            },
            _onChangeDate: function (event) {
                this.moment_date = event.data.date
                this.loadEvents();
            },
            _onOpenEvent: function (event) {
                var self = this;
                var id = event.data.id;
    //            var timezone = Intl.DateTimeFormat().resolvedOptions().timeZone
                event.data.start.add(-this.getSession().getTZOffset(event.data.start), 'minutes')
                event.data.end.add(-this.getSession().getTZOffset(event.data.end), 'minutes')
                var context = {
                    'default_start':event.data.start.format("YYYY-MM-DD HH:mm:SS"),
                    'default_stop':event.data.end.format("YYYY-MM-DD HH:mm:SS"),
                    'default_optometrist_id':parseInt(event.data.resourceId),
                }
                var open_dialog = function (readonly) {
                    var options = {
                        res_model: 'calendar.event',
                        res_id: parseInt(id) || null,
                        context: context || self.context,
                        title: _t("Open: ") + event.data.title,
                        on_saved: function (el) {
                            var res_id = el.res_id
                            setTimeout(function(){
                                rpc.query({
                                    model: 'calendar.event',
                                    method: 'getEventList',
                                    args: [[parseInt(res_id)], {'date':moment(self.moment_date).format('YYYY-MM-DD'),'timezone':Intl.DateTimeFormat().resolvedOptions().timeZone}]
                                }, {async: false}).then(function (res) {
                                    self.eventList = res
                                    self.$el.find('#backend_resource_view').fullCalendar('removeEvents')
                                    self.$el.find('#backend_resource_view').fullCalendar('renderEvents',res);
                                });
                            },200);
                        },
                    };
                    self.dialog = new dialogs.FormViewDialog(self, options).open();
                };
                open_dialog(true);
            },
            start: function () {
                this._super.apply(this, arguments);
                this.set("title", this.title);
                this.update_control_panel({search_view_hidden: true}, {clear: true});
                var self = this;
            },
            events:_.extend({}, AbstractAction.prototype.events, {
                 'change .optometrist_checkbox':'filter_optometrist',
                 'click .remove_optometrist_from_favourite':'remove_optometrist_from_favourite',
                 'focus #user_autocomplete':'prepare_autocomplete_list',
            }),
            remove_optometrist_from_favourite:function(event){
                var self = this;
                var id = $(event.currentTarget).attr('data-id');
                this._rpc({
                model: 'optometrist.user',
                    method: 'remove_optometrist',
                    args: [[parseInt(self.context.uid)], parseInt(id)],
                })
                .then(function() {
                    self.optometrist = Array();
                    self.optometristList = Array();
                    self.renderElement();
                });
            },
            prepare_autocomplete_list: function(){
                var self = this;
                self.availableTags = [];
                rpc.query({
                    model: 'res.users',
                    method: 'prepare_auto_complete',
                    args:[self.context.uid],
                }, {async: false}).then(function (res) {
                    for (var i in res) {
                        self.availableTags.push({label: res[i].name, value: res[i].name, id: res[i].id, calendar_bg_color: res[i].calendar_bg_color, calendar_text_color:res[i].calendar_text_color, image: res[i].image});
                    }
                });
                if (self.$el.find('#user_autocomplete').hasClass('ui-autocomplete')) {
                   self.$el.find('#user_autocomplete').autocomplete('destroy')
                }
                self.$el.find('#user_autocomplete').autocomplete({
                    source: self.availableTags,
                    delay: 400,
                    minChars: 0,
                    minLength: 0,
                    select: function (eve, ui) {
                        self._rpc({
                            model: 'optometrist.user',
                            method: 'add_optometrist',
                            args: [[parseInt(self.context.uid)], parseInt(ui.item.id)],
                        })
                        .then(function() {
                            self.optometrist = Array();
                            self.optometristList = Array();
                            self.renderElement();
                        });
                    }
                }).focus(function () {
                    $(this).autocomplete('search', $(this).val())
                });
            },
            filter_optometrist:function(event){
                var self = this;
                var id = $(event.currentTarget).attr('data-id');
                var value = false;
                if($(event.currentTarget).is(":checked")){
                    value = true
                }
                this._rpc({
                model: 'optometrist.user',
                    method: 'filter_optometrist',
                    args: [[parseInt(self.context.uid)], parseInt(id), {'active_roster_view':value}],
                })
                .then(function() {
                    self.optometrist = Array();
                    self.optometristList = Array();
                    self.renderElement();
                });
            },
            renderElement: function () {
                var self = this;
                this._super.apply(this, arguments);
                self.$el.find('#backend_resource_view').fullCalendar('destroy');
                self.loadOptometrist();
                self.loadEvents();
                $(window).trigger('resize');
            },
            loadOptometrist: function(){
                var self = this;
                rpc.query({
                    model: 'res.users',
                    method: 'get_optometrist_ids',
                    args:[self.context.uid],
                }, {async: false}).then(function (res) {
                    $.each(res,function(each){
                        self.optometrist.push({'id':res[each].id,'title':res[each].name,'image':res[each].image,'calendar_bg_color':res[each].calendar_bg_color,'calendar_text_color':res[each].calendar_text_color,'active_roster_view':res[each].active_roster_view})
                        if(res[each].active_roster_view){
                            self.optometristList.push({'id':res[each].id,'title':res[each].name,'image':res[each].image,'calendar_bg_color':res[each].calendar_bg_color,'calendar_text_color':res[each].calendar_text_color})
                        }
                    });
                });

                var $content = QWeb.render('TOMS.RosterViewOptometrist', {widget: self});
                self.$el.find('.o_calendar_filters').html('').html($content);
            },
            loadEvents:function(){
                var self = this;
                this._rpc({
                    model: 'calendar.event',
                    method: 'getEventList',
                    args: [[],{'date':moment(self.moment_date).format('YYYY-MM-DD'),'timezone':Intl.DateTimeFormat().resolvedOptions().timeZone}]
                }, {async: true}).then(function (res) {
                    self.eventList = res
                    self.init_roster_view();
                    self._initCalendarMini();
                    $(window).trigger('resize');
                });
            },
            init_roster_view: function(){
                var self = this
                var locale = moment.locale();
                console.log
                var timezone = Intl.DateTimeFormat().resolvedOptions().timeZone
                console.log("\n\n\n timezone--->", timezone)
                self.$el.find('#backend_resource_view').fullCalendar('destroy');
                $.fullCalendar.locale(locale);
                setTimeout(function(){
                    self.$el.find('#backend_resource_view').fullCalendar({
                        defaultView: 'agendaDay',
                        defaultDate: moment(self.moment_date),
                        editable: false,
                        allDaySlot: false,
                        eventOverlap: true,
                        selectable: true,
                        height: 'parent',
                        unselectAuto: false,
                        minTime: "00:00:00",
                        maxTime: "23:59:59",
                        slotDuration: "00:30:00",
                        slotLabelInterval:"00:05",
                        scrollTime: '06:00',
                        nowIndicator:true,
                        header: {
                            left: 'date',
                            center: false,
                            right:'today',
                        },
                        resources:self.optometristList,
                        viewRender:function(view,element){
                            self.$el.find('.fc-toolbar.fc-header-toolbar .fc-left').html('').html(view.title)
                        },
                        events:self.eventList,
                        locale: locale,
//                        timezone:timezone,
                        eventAfterAllRender: function () {
                            $(window).trigger('resize');
                            self.$el.find('.fc-event-container .fc-time-grid-event').css('margin-left','7px')
                        },
                        eventClick: function (event) {
                            self.trigger_up('openEvent', event);
                            self.$el.find('#backend_resource_view').fullCalendar('unselect');
                        },
                        eventRender: function (events, element) {
                            if (events['rendering'] === 'background') {
                            } else {
                                var present = events.present;
                                if (present){
                                    element.prepend("<div class='fa fa-circle' style='color:green;float:right;'></div>");
                                }
                                else{
                                    element.prepend("<div class='fa fa-circle' style='color:red;float:right;'></div>");
                                }

                            }
                        },
                        select: function (start, end, jsEvent, view, resource) {
                            var current_time = moment().format('YYYY-MM-DD HH:mm:ss')
                            var start_date = moment(start).format('YYYY-MM-DD HH:mm:ss')
                            var end_date = moment(end).format('YYYY-MM-DD HH:mm:ss')
                            var diff =Math.abs(end - start) / 36e5;
                            if (resource){
                                var resourceId = resource.id;
                            }
                            rpc.query({
                                model: 'calendar.event',
                                method: 'timezone',
                                args: [[],{'start_date':start_date,'end_date':end_date,'timezone':timezone}]
                            }, {async: false}).then(function (res) {
                                var open_dialog = function (readonly) {
                                var options = {
                                    res_model: 'calendar.event',
                                    res_id: null,
                                    readonly: readonly,
                                    context: {
                                        'default_start': res[0],
                                        'default_stop': res[1],
                                        'dafault_optometrist_id':parseInt(resourceId) || null,
                                    },
                                    title: _t("Open:"),
                                    on_saved: function (el) {
                                        var res_id = el.res_id
                                        rpc.query({
                                            model: 'calendar.event',
                                            method: 'get_saved_data',
                                            args: [[],{'id':parseInt(res_id),'timezone':timezone}]
                                        }, {async: false}).then(function (res) {
                                                self.eventList.push(res)
                                                self.$el.find('#backend_resource_view').fullCalendar('renderEvent',res);

                                        });

                                    },
                                };
                                self.dialog = new dialogs.FormViewDialog(self, options).open();
                            };
                            open_dialog(true);
                            self.$el.find('#backend_resource_view').fullCalendar('unselect');
                            });
                        },
                    });
                    self.$el.find('.fc-today-button').click(function(){
                        self.moment_date = moment();
                        self.loadEvents();
                    });
                },500)
            },
            _initCalendarMini: function () {
                var self = this;
                self.$small_calendar = this.$(".o_calendar_mini");
                setTimeout(function(){
                    var date = moment(self.moment_date).format('YYYY-MM-DD');
                    self.$small_calendar.datepicker("destroy");
                    self.$small_calendar.datepicker({
                        'defaultDate':new Date(date),
                        'onSelect': function (datum, obj) {
                            self.trigger_up('changeDate', {
                                date: moment(new Date(+obj.currentYear , +obj.currentMonth, +obj.currentDay))
                            });
                        },
                    });
                },1000)
            },
        });
        core.action_registry.add('tag_appointment_resource_view', AppointmentRosterView);
        return {
            AppointmentRosterView : AppointmentRosterView,
        };
});
