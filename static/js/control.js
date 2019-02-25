$(document).ready(function(){
	var light_schedule;
	var sel_rule_index;

	$.getJSON('/agricoltura/methods/getLightSchedule', function(data){
		raw_config = data;
		fill_dev_table();
	});

	getParameters();

	$('#update-params').click(function(){
		$.ajax({ url: '/agricoltura/methods/setParameters',
			type: 'POST',
			contentType: 'application/json',
			data: JSON.stringify({
				interval_min: $("#interval-min").val(),
				min_temp: $("#min-temp").val(),
				max_hum: $("#max-hum").val(),
				max_temp: $("#max-temp").val(),
				min_soil_moist: $("#min-moist").val(),
				max_soil_moist: $("#max-moist").val()
			}),
			success: function(response) {
				$('#set-param-result').attr('class', 'text-monospace text-success');
				$('#set-param-result').text('OK');
			},
			error: function(response) {
				$('#set-param-result').attr('class', 'text-monospace text-danger');
				$('#set-param-result').text('ERROR');
			},
			complete: function(response) {
				getParameters();
			}
		});
	});

	$('#reset-params').click(getParameters);

	$('#edit-light-cfg').click(function(){
		$.ajax({ url: '/agricoltura/methods/editLightCfg', 
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

	function getParameters() {
		$.getJSON('/agricoltura/methods/getParameters', function(data){
			$('#interval-min').val(data['interval_min']);
			$('#min-temp').val(data['min_temp']);
			$('#max-temp').val(data['max_temp']);
			$('#max-hum').val(data['max_hum']);
			$('#min-moist').val(data['min_soil_moist']);
			$('#max-moist').val(data['max_soil_moist']);
		});
	}

	function click_light_table(row) {
		$('#light-table>tbody>tr').removeClass('checked-table-row');
		$(row).toggleClass('checked-table-row');
		sel_rule_index = $('tr').index(row)-1;	
	}

	function fill_dev_table() {
		var content = '';
		$.each(light_schedule, function( index, rule){
			content += '<tr>';
			content += '<td>'+rule[0]+'</td>'; 
			content += '<td>'+rule[1]+'</td>';
			content += '<td>'+rule[2]+'</td>';
			content += '<td>'+rule[3]+'</td>';
			content += '<td>'+rule[4]+'</td>';
			content += '</tr>';			
		});		
		$('#light-table tbody').html(content);
		$('#light-table>tbody>tr').click(function(){
			click_light_table($(this));
		});	
		click_light_table($('#light-table>tbody>tr:first'));		
	}

	// $('#sensors-export').click(function(){
	// 	$.ajax({ url: '/agricoltura/methods/getReadings',
	// 		type: 'POST',
	// 		contentType: 'application/json',
	// 		data: JSON.stringify({
	// 			from: new Date($("#sensors-from").val()).getTime(),
	// 			to: new Date($("#sensors-to").val()).getTime()
	// 		}),
	// 		dataType: 'json',
	// 		success: function(response) {
	// 			download('sensors_data.txt', response);
	// 		}
	// 	});
	// });

	// $('#actuators-export').click(function(){
	// 	$.ajax({ url: '/agricoltura/methods/getActuators',
	// 		type: 'POST',
	// 		contentType: 'application/json',
	// 		data: JSON.stringify({
	// 			from: new Date($("actuators-from").val()).getTime(),
	// 			to: new Date($("#actuators-to").val()).getTime()
	// 		}),
	// 		dataType: 'json',
	// 		success: function(response) {
	// 			download('actuators_data.txt', response);
	// 		}
	// 	});
	// });

	// function getCosts() {
	// 	$.ajax({ url: '/agricoltura/methods/getCosts',
	// 		type: 'POST',
	// 		contentType: 'application/json',
	// 		data: JSON.stringify({
	// 			from: new Date($("#costs-from").val()).getTime(),
	// 			to: new Date($("#costs-to").val()).getTime()
	// 		}),
	// 		dataType: 'json',
	// 		success: function(response) {
	// 			var table = $("#table-costs tbody")[0], i, j;
	// 			for(i=0; i<6; i++) {
	// 				for(j=0; j<3; j++) {
	// 					$(table.rows[i].cells[j+1]).html(response[i][j]);
	// 				}
	// 			}
	// 		}
	// 	});
	// }

	// function download(filename, text) {
	// 	var element = document.createElement('a');
	// 	element.setAttribute('href', 'data:json;charset=utf-8,' + encodeURIComponent(text));
	// 	element.setAttribute('download', filename);
	// 	element.style.display = 'none';
	// 	document.body.appendChild(element);
	// 	element.click();
	// 	document.body.removeChild(element);
	// }

	// function getRates() {
	// 	$.getJSON('/agricoltura/methods/getRates', function(data){
	// 		$('#elec-price').val(data['elec_price']);
	// 		$('#water-price').val(data['water_price']);
	// 		$('#fan-w').val(data['fan_w']);
	// 		$('#pump-w').val(data['pump_w']);
	// 		$('#pump-f').val(data['pump_f']);
	// 		$('#light-w').val(data['light_w']);
	// 		$('#server-w').val(data['server_w']);
	// 	});
	// }

});
