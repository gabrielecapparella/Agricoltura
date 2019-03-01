$(document).ready(function(){
	var light_schedule;
	var sel_rule_index; // if -1 then it's a new rule

	$.getJSON('/agricoltura/methods/getLightSchedule', function(data){
		light_schedule = data;
		fill_light_table();
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

	$('#light-save').click(function(){
		rule = [
			$("#light-who").val(),
			$("#light-when").val().replace("T", " "),
			$("#light-duration").val(),
			$("#light-interval").val(),
			$("#light-enabled").val()
		];

		if (sel_rule_index < 0) { // Adding a new rule
			light_schedule.push(rule);
		} else { // Updating an old one
			light_schedule[sel_rule_index] = rule
		}
		
		saveLightSchedule();
	});

	$('#light-delete').click(function(){
		if (sel_rule_index > -1) {
			light_schedule.splice(sel_rule_index, 1);
			saveLightSchedule();
		}
	});

	$('#light-add').click(function(){
		sel_rule_index = -1;
		$("#light-who").val("");
		$("#light-when").val("");
		$("#light-duration").val("");
		$("#light-interval").val("");
		$("#light-enabled").val("");	
	});

	function saveLightSchedule() {
		$.ajax({ url: '/agricoltura/methods/setLightSchedule', 
			type: 'POST',
			contentType: 'application/json',
			dataType: 'json',
			data: JSON.stringify(light_schedule),
			success: function(response) {
				if(response["result"]) {
					$('#light-result').attr("class", "green");
					$("#light-result").text("OK");
					light_schedule = response["new_rules"];
					fill_light_table();
				} else {
					$('#light-result').attr("class", "red");
					$("#light-result").text(response["reason"]);									
				}
			},
			error: function(response) {
				$('light-result').attr("class", "red");
				$("light-result").text("ERROR");
			}
		});
		$("#light-result").show();		
	}

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

		rule = light_schedule[sel_rule_index];

		$("#light-who").val(rule[0]);
		$("#light-when").val(rule[1].replace(" ", "T"));
		$("#light-duration").val(rule[2]);
		$("#light-interval").val(rule[3]);
		$("#light-enabled").val(rule[4].toString());

	}

	function fill_light_table() {
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
