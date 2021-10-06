odoo.define('sh_inventory_adjustment_barcode_scanner.sound_sh_barcode_scanner', function (require) {
"use strict";



var ajax = require('web.ajax');
var core = require('web.core');
var Dialog = require('web.Dialog');
var CrashManager = require('web.CrashManager');
var AbstractWebClient = require('web.AbstractWebClient');

var QWeb = core.qweb;
var _t = core._t;
var _lt = core._lt;
var qweb = core.qweb;

var CrashManager = CrashManager.include({
	
    show_warning: function(error) {
    	if (!this.active) {
            return;
        }
    	

        
		/****************************************************************
		 * softhealer custom code start here
		 * SH_BARCODE_SCANNER_ is a code to identi
		 * fy that message is coming from barcode scanner.
		 * here we remove code for display valid message and play sound.       
		 * ***************************************************************
        */
		if (error.data.message.length){
			
    		//for auto close popup start here
    		var auto_close_ms = error.data.message.match("AUTO_CLOSE_AFTER_(.*)_MS&");
    		if(auto_close_ms && auto_close_ms.length == 2){
    			auto_close_ms = auto_close_ms[1];    			
    			var original_msg = "AUTO_CLOSE_AFTER_"+ auto_close_ms +"_MS&";
    			error.data.message = error.data.message.replace(original_msg, "");    			
    			
    			setTimeout(function(){     				
    				$('.o_technical_modal').find('button[type="button"] > span:contains("Ok")').closest('button').trigger( "click" );
    			}, auto_close_ms);	    			
    			
    		} 	  
    		//for auto close popup ends here
    		
    		
    		//for play sound start here
    		//if message has SH_BARCODE_SCANNER_
    		var str_msg = error.data.message.match("SH_BARCODE_SCANNER_");    		
    		if (str_msg){
    			//remove SH_BARCODE_SCANNER_ from message and make valid message
    			error.data.message = error.data.message.replace("SH_BARCODE_SCANNER_", "");
    			    			
    			//play sound
    			var src = "/sh_inventory_adjustment_barcode_scanner/static/src/sounds/error.wav";
    	        $('body').append('<audio src="'+src+'" autoplay="true"></audio>');	   
    		}
    		//for play sound ends here

		}
		
	
					
		//softhealer custom code ends here
        
        
        return new Dialog(this, {
            size: 'medium',
            title: _.str.capitalize(error.type || error.message) || _t("Odoo Warning"),
            subtitle: error.data.title,
            $content: $(QWeb.render('CrashManager.warning', {error: error}))
        }).open({shouldFocusButtons:true});
    },
    
    

	/*
    show_warning: function(error) {

		alert("error ==>" + error);
		
        return this._super.apply(this, arguments);	    
	    
	},
	
	*/
	
	

});

var AbstractWebClient = AbstractWebClient.include({

    /**
     * Displays a warning in a dialog or with the notification service
     *
     * @private
     * @param {OdooEvent} e
     * @param {string} e.data.message the warning's message
     * @param {string} e.data.title the warning's title
     * @param {string} [e.data.type] 'dialog' to display in a dialog
     * @param {boolean} [e.data.sticky] whether or not the warning should be
     *   sticky (if displayed with the Notification)
     */
    _onDisplayWarning: function (e) {
        
		/****************************************************************
		 * softhealer custom code start here
		 * SH_BARCODE_SCANNER_ is a code to identi
		 * fy that message is coming from barcode scanner.
		 * here we remove code for display valid message and play sound.       
		 * ***************************************************************
        */
    	 	

    	if (e.data.message.length){
			
    		
    		//for auto close popup start here
    		var auto_close_ms = e.data.message.match("AUTO_CLOSE_AFTER_(.*)_MS&");
    		if(auto_close_ms && auto_close_ms.length == 2){
    			auto_close_ms = auto_close_ms[1];    			
    			var original_msg = "AUTO_CLOSE_AFTER_"+ auto_close_ms +"_MS&";
    			e.data.message = e.data.message.replace(original_msg, "");    			
    			
    			setTimeout(function(){     				
    				$('.o_technical_modal').find('button[type="button"] > span:contains("Ok")').closest('button').trigger( "click" );
    			}, auto_close_ms);	    			
    			
    		} 	  
    		//for auto close popup ends here    		
    		
    		//for play sound start here
    		//if message has SH_BARCODE_SCANNER_
    		var str_msg = e.data.message.match("SH_BARCODE_SCANNER_");    		
    		if (str_msg){
    			//remove SH_BARCODE_SCANNER_ from message and make valid message
    			e.data.message = e.data.message.replace("SH_BARCODE_SCANNER_", "");
    			//play sound
    			var src = "/sh_inventory_adjustment_barcode_scanner/static/src/sounds/error.wav";
    	        $('body').append('<audio src="'+src+'" autoplay="true"></audio>');	  
    	           	  
    		}
    		//for play sound ends here    		

		}
		
		

 
					
		//softhealer custom code ends here    	
 	
    	
    	
    	var data = e.data;
        if (data.type === 'dialog') {
            new Dialog(this, {
                size: 'medium',
                title: data.title,
                $content: qweb.render("CrashManager.warning", data),
            }).open({shouldFocusButtons: true});
        } else {
            this.call('notification', 'notify', e.data);
        }
    },	
	

});

});


