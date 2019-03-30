$(document).ready(function(){
	var raw_config;
	var sel_dev_name;
	var sel_dev_index;


	$.getJSON('/agricoltura/methods/getDevicesCfg', function(data){
		raw_config = data;
		fill_dev_table();
	});

	$('.card-act-switch').click(function(){
		$.ajax({ url: '/agricoltura/methods/setActiveControl', 
			type: 'POST',
			contentType: 'application/json',
			dataType: 'json',
			data: JSON.stringify({ 
				state_index: parseInt($(this).attr('data-state-index')),
				state: $(this).attr('data-value')=='True'
			}),
			success: function(response) {
				var act_switch = $('.card-act-switch[data-state-index="'+response['state_index']+'"]')
				if(response["result"]) {
					act_switch.attr("class", "green card-act-switch");
					act_switch.attr("data-value", 'False');
					act_switch.html("AUTO");
				} else {
					act_switch.attr("class", "red card-act-switch");
					act_switch.attr("data-value", 'True');
					act_switch.html("MAN");

				}
			}
		});		
	});

	$('.zero, .one, .two').click(function(){
		var toggle = $(this).parent();
		switch($(this).attr('data-target')) {
			case "on":
				target = [true];
				break;
			case "off":
				target = [false];
				break;
			case "fan-50":
				target = [true, 50];
				break;
			case "fan-100":
				target = [true, 100];
				break;						
		}
		$.ajax({ url: '/agricoltura/methods/setActuator', 
			type: 'POST',
			contentType: 'application/json',
			dataType: 'json',
			data: JSON.stringify({ 
				name: $(this).parent().parent().attr('id'),
				target_state: target
			}),
			success: function(response) {
				if(!response[0]) {
					toggle.attr("class", "toggle-button");
				} else if(response.length==2 && response[1]>50) {
					toggle.attr("class", "toggle-button-two");
				} else {
					toggle.attr("class", "toggle-button-on");
				}
			}
		});	
	});

	$('#edit-dev-cfg').click(function(){
		try {
			usr_cfg = JSON.parse($('#dev-raw-config>textarea').val());
		} catch(e) {
			$('#edit-cfg-result').attr("class", "red");
			$("#edit-cfg-result").text("SYNTAX ERROR");	
			return false;
		}

		$.ajax({ url: '/agricoltura/methods/editDevCfg', 
			type: 'POST',
			contentType: 'application/json',
			dataType: 'json',
			data: JSON.stringify({ 
				name: sel_dev_name,
				index: sel_dev_index,
				cfg: usr_cfg
			}),
			success: function(response) {
				if(response["result"]) {
					$('#edit-cfg-result').attr("class", "green");
					$("#edit-cfg-result").text("OK");
					raw_config = response["new_cfg"];
					fill_dev_table();
				} else {
					$('#edit-cfg-result').attr("class", "red");
					$("#edit-cfg-result").text("VALUE ERROR");									
				}
			},
			error: function(response) {
				$('#users-result').attr("class", "red");
				$("#edit-cfg-result").text("ERROR");
			}
		});
		$("#edit-cfg-result").show();
	});

	function click_dev_table(row) {
		$('#dev-table>tbody>tr').removeClass('checked-table-row');
		$(row).toggleClass('checked-table-row');

		sel_dev_index = $('tr').index(row)-1;
		sel_dev_name = $(row).children('.dev-name').html();
		dev_cfg = JSON.stringify(raw_config[sel_dev_index], null, '  ');
		$('#dev-raw-config>textarea').val(dev_cfg);		
	}

	function fill_dev_table() {
		var content = '';
		$.each(raw_config, function( index, dev_raw_cfg){
			content += '<tr>';
			content += '<td class="dev-name">'+dev_raw_cfg["name"]+'</td>'; 
			content += '<td>'+dev_raw_cfg["model"]+'</td>';
			content += '<td>'+dev_raw_cfg["enabled"]+'</td>';
			content += '</tr>';			
		});		
		$('#dev-table tbody').html(content);
		$('#dev-table>tbody>tr').click(function(){
			click_dev_table($(this));
		});	
		click_dev_table($('#dev-table>tbody>tr:first'));		
	}

});