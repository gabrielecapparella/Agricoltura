$(document).ready(function(){
	var light_schedule;
	var sel_rule_index; // if -1 then it's a new rule
	var thresholds;
	var chart;
	var history = [null, null, null]; //temperature, humidity, soil moisture

	chart = Highcharts.stockChart('current-chart', {
		rangeSelector: {
			buttons: [
				{type: 'day', count: 1, text: '1d'},
				{type: 'week', count: 1, text: '1w'},
				{type: 'month', count: 1, text: '1m'},
				{type: 'year', count: 1, text: '1y'},
				{type: 'all',text: 'All'}
			],
			selected: 0
		},
		series: [{name: 'Temperature', tooltip: {valueDecimals: 1, valueSuffix: '°C'}}]
	});

	$('#temp-chart').click(drawTemperature);
	$('#hum-chart').click(drawHumidity);
	$('#moist-chart').click(drawSoilMoisture);	

	$.getJSON('/agricoltura/methods/getLightSchedule', function(data){
		light_schedule = data;
		fill_light_table();
	});

	getParameters();

	fill_costs_table();

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
				$('#set-param-result').addClass('green');
				$('#set-param-result').text('OK');
			},
			error: function(response) {
				$('#set-param-result').addClass('red');
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

	$('#costs-ok').click(fill_costs_table);

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

			thresholds = data;
			drawTemperature();
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

	function fill_costs_table() {
		$.ajax({ url: '/agricoltura/methods/getCosts',
			type: 'POST',
			contentType: 'application/json',
			data: JSON.stringify({
				from: new Date($("#costs-from").val()).getTime(),
				to: new Date($("#costs-to").val()).getTime()
			}),
			dataType: 'json',
			success: function(response) {		
				var content = '';
				$.each(response, function(index, model_type){
					content += '<tr>';
					content += '<td>'+model_type[0]+'</td>'; 
					content += '<td>'+model_type[1]+'</td>';
					content += '<td>'+model_type[2]+'</td>';
					content += '<td>'+model_type[3]+'</td>';
					content += '</tr>';			
				});
				$('#costs-table tbody').html(content);
			}
		});
	}	

	function drawTemperature() {
		if (!history[0]) {
			$.getJSON('/agricoltura/methods/getTempHistory', function(data){
				history[0] = data;
				drawTemperature();
			});			
		} else {
			chart.yAxis[0].update({
				title: {text: 'Temperature (°C)'},
				plotLines: [
					{value: thresholds['min_temp'], color: 'red', width: 1, label: {text: 'low', style:{color: 'red'}}, zIndex: 4},
					{value: thresholds['max_temp'], color: 'red', width: 1, label: {text: 'high', style:{color: 'red'}}, zIndex: 4}
				]
			});
			chart.setTitle({text: 'Temperature History'});
			chart.series[0].update({name: 'Temperature', data: history[0], tooltip: {valueDecimals: 1, valueSuffix: '°C'}});
			$('#history-chart>.blue-button-active').toggleClass('blue-button-active');
			$('#temp-chart').toggleClass('blue-button-active');
		}	
	}

	function drawHumidity() {
		if (!history[1]) {
			$.getJSON('/agricoltura/methods/getHumHistory', function(data){
				history[1] = data;
				drawHumidity();
			});			
		} else {
			chart.yAxis[0].update({
				title: {text: 'Humidity (%)'},
				plotLines: [
					{value: thresholds['max_hum'], color: 'red', width: 1, label: {text: 'high', style:{color: 'red'}}, zIndex: 4}
				]
			});
			chart.setTitle({text: 'Humidity History'});
			chart.series[0].update({name: 'Humidity', data: history[1], tooltip: {valueDecimals: 1, valueSuffix: '%'}})
			$('#history-chart>.blue-button-active').toggleClass('blue-button-active');
			$('#hum-chart').toggleClass('blue-button-active');
		}	
	}

	function drawSoilMoisture() {
		if (!history[2]) {
			$.getJSON('/agricoltura/methods/getMoistHistory', function(data){
				history[2] = data;
				drawSoilMoisture();
			});			
		} else {
			chart.yAxis[0].update({
				title: {text: 'Soil Moisture (%)'},
				plotLines: [
					{value: thresholds['min_soil_moist'], color: 'red', width: 1, label: {text: 'low', style:{color: 'red'}}, zIndex: 4}
				]
			});
			chart.setTitle({text: 'Soil Moisture History'});
			chart.series[0].update({name: 'Soil Moisture', data: history[2], tooltip: {valueDecimals: 1, valueSuffix: '%'}})
			$('#history-chart>.blue-button-active').toggleClass('blue-button-active');
			$('#moist-chart').toggleClass('blue-button-active');
		}	
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
