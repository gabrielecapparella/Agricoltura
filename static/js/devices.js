$(document).ready(function(){
	var raw_config;
	var sel_dev_name;
	var sel_dev_index;


	$.getJSON('/agricoltura/methods/getDevicesCfg', function(data){
		raw_config = data;
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
			data: JSON.stringify({ 
				name: $(this).parent().parent().attr('id'),
				target_state: target
			}),
			success: function(response) {
				response = JSON.parse(response)
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
		usr_cfg = JSON.parse($('#dev-raw-config>textarea').val());
		$.ajax({ url: '/agricoltura/methods/editDevCfg', 
			type: 'POST',
			contentType: 'application/json', 
			data: JSON.stringify({ 
				name: sel_dev_name,
				index: sel_dev_index,
				cfg: usr_cfg
			}),
			success: function(response) {
				switch(response['result']) {
					case 0:
						$('#edit-cfg-result').attr("class", "green");
						$("#edit-cfg-result").text("OK");
						break;
					case 1:
						$('#edit-cfg-result').attr("class", "red");
						$("#edit-cfg-result").text("SYNTAX ERROR");
					case 2:
						$('#edit-cfg-result').attr("class", "red");
						$("#edit-cfg-result").text("VALUE ERROR");									
				}
				$("#edit-cfg-result").show();
			},
			error: function(response) {
				$('#users-result').attr("class", "red");
				$("#edit-cfg-result").text("ERROR");
				$("#edit-cfg-result").show();
			}
		});

	});

	function click_dev_table(row) {
		$('#dev-table>tbody>tr').removeClass('checked-table-row');
		$(row).toggleClass('checked-table-row');

		sel_dev_index = $('tr').index(row)-1;
		sel_dev_name = $(row).children('.dev-name').html();
		dev_cfg = JSON.stringify(raw_config[sel_dev_index], null, '  ');
		$('#dev-raw-config>textarea').text(dev_cfg);		
	}	

});