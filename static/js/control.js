$(document).ready(function(){

	$.getJSON('/agricoltura/methods/getLastReading', function(data){
		$('#temp-reading').html(data['temp']);
		$('#hum-reading').html(data['hum']);
		$('#moist-reading').html(data['moist']);
	});

	$.getJSON('/agricoltura/methods/getActuators', function(data){
		if(data['sensors_on']) { $('#sensors-toggle').attr('class', 'toggle-button toggle-button-on p-0'); }
		if(data['actuators_on']) { $('#actuators-toggle').attr('class', 'toggle-button toggle-button-on p-0'); }
		if(data['light_on']) { $('#light-toggle').attr('class', 'toggle-button toggle-button-on'); }
		if(data['water_on']) { $('#irrigation-toggle').attr('class', 'toggle-button toggle-button-on'); }
		if(data['fan_on']) {
			if(data['fan_speed']<=50) {$('#fan-toggle').attr('class', 'toggle-button toggle-button-on');}
			else {$('#fan-toggle').attr('class', 'toggle-button toggle-button-two');}
		}
	});

	getParameters();
	getRates();
	getCosts();

	$('#reset').click(getParameters);
	$('#calculate-costs').click(getCosts);

	$('#update-param').click(function(){
		$.ajax({ url: '/agricoltura/methods/setParameters',
			type: 'POST',
			contentType: 'application/json',
			data: JSON.stringify({
				interval_min: $("#interval-min").val(),
				min_temp: $("#min-temp").val(),
				max_hum: $("#max-hum").val(),
				max_temp: $("#max-temp").val(),
				min_soil_moist: $("#min-moist").val(),
				min_light_hours: $("#min-light").val(),
				max_soil_moist: $("#max-moist").val(),
				cam_h: $("#cam-h").val()
			}),
			success: function(response) {
				$('#set-param-result').attr('class', 'text-monospace text-success');
				$('#set-param-result').text('OK');
				getParameters();
			},
			error: function(response) {
				$('#set-param-result').attr('class', 'text-monospace text-danger');
				$('#set-param-result').text('ERROR');
				getParameters();
			}
		});
	});

	$('#update-rates').click(function(){
		$.ajax({ url: '/agricoltura/methods/setRates',
			type: 'POST',
			contentType: 'application/json',
			data: JSON.stringify({
				elec_price: $("#elec-price").val(),
				water_price: $("#water-price").val(),
				fan_w: $("#fan-w").val(),
				pump_w: $("#pump-w").val(),
				pump_f: $("#pump-f").val(),
				light_w: $("#light-w").val(),
				server_w: $("#server-w").val()
			}),
			success: function(response) {
				$('#set-rates-result').attr('class', 'text-monospace text-success');
				$('#set-rates-result').text('OK');
				getRates();
			},
			error: function(response) {
				$('#set-rates-result').attr('class', 'text-monospace text-danger');
				$('#set-rates-result').text('ERROR');
				getRates();
			}
		});
	});

	$('#sensors-toggle').click(function(){
		if( $('#sensors-toggle').hasClass('toggle-button-on') ) { target = false; }
		else { target = true; }

		$.ajax({ url: '/agricoltura/methods/setSensors',
			type: 'POST',
			contentType: 'application/json',
			data: JSON.stringify({ targetState: target }),
			success: function(response) {
				$('#sensors-toggle').toggleClass('toggle-button-on');
			}
		});
	});

	$('#actuators-toggle').click(function(){
		if( $('#actuators-toggle').hasClass('toggle-button-on') ) { target = false; }
		else { target = true; }

		$.ajax({ url: '/agricoltura/methods/setActuators',
			type: 'POST',
			contentType: 'application/json',
			data: JSON.stringify({ targetState: target }),
			success: function(response) {
				$('#actuators-toggle').toggleClass('toggle-button-on');
			}
		});
	});

	$('#light-toggle').click(function(){
		if( $('#light-toggle').hasClass('toggle-button-on') ) { target = false; }
		else { target = true; }

		$.ajax({ url: '/agricoltura/methods/setLight',
			type: 'POST',
			contentType: 'application/json',
			data: JSON.stringify({ targetState: target }),
			success: function(response) {
				$('#light-toggle').toggleClass('toggle-button-on');
			}
		});
	});

	$('#irrigation-toggle').click(function(){
		if( $('#irrigation-toggle').hasClass('toggle-button-on') ) { target = false; }
		else { target = true; }

		$.ajax({ url: '/agricoltura/methods/setWater',
			type: 'POST',
			contentType: 'application/json',
			data: JSON.stringify({ targetState: target }),
			success: function(response) {
				$('#irrigation-toggle').toggleClass('toggle-button-on');
			}
		});
	});

	$('#fan-zero').click(function(){
		$.ajax({ url: '/agricoltura/methods/setFan',
			type: 'POST',
			contentType: 'application/json',
			data: JSON.stringify({ targetState: false, targetSpeed: 0 }),
			success: function(response) {
				$('#fan-toggle').attr('class', 'toggle-button toggle-button-zero');
			}
		});
	});

	$('#fan-one').click(function(){
		$.ajax({ url: '/agricoltura/methods/setFan',
			type: 'POST',
			contentType: 'application/json',
			data: JSON.stringify({ targetState: true, targetSpeed: 50 }),
			success: function(response) {
				$('#fan-toggle').attr('class', 'toggle-button toggle-button-on');
			}
		});
	});

	$('#fan-two').click(function(){
		$.ajax({ url: '/agricoltura/methods/setFan',
			type: 'POST',
			contentType: 'application/json',
			data: JSON.stringify({ targetState: true, targetSpeed: 100 }),
			success: function(response) {
				$('#fan-toggle').attr('class', 'toggle-button toggle-button-two');
			}
		});
	});

	$('#sensors-export').click(function(){
		$.ajax({ url: '/agricoltura/methods/getReadings',
			type: 'POST',
			contentType: 'application/json',
			data: JSON.stringify({
				from: new Date($("#sensors-from").val()).getTime(),
				to: new Date($("#sensors-to").val()).getTime()
			}),
			dataType: 'json',
			success: function(response) {
				download('sensors_data.txt', response);
			}
		});
	});

	$('#actuators-export').click(function(){
		$.ajax({ url: '/agricoltura/methods/getActuators',
			type: 'POST',
			contentType: 'application/json',
			data: JSON.stringify({
				from: new Date($("actuators-from").val()).getTime(),
				to: new Date($("#actuators-to").val()).getTime()
			}),
			dataType: 'json',
			success: function(response) {
				download('actuators_data.txt', response);
			}
		});
	});

	function getCosts() {
		$.ajax({ url: '/agricoltura/methods/getCosts',
			type: 'POST',
			contentType: 'application/json',
			data: JSON.stringify({
				from: new Date($("#costs-from").val()).getTime(),
				to: new Date($("#costs-to").val()).getTime()
			}),
			dataType: 'json',
			success: function(response) {
				var table = $("#table-costs tbody")[0], i, j;
				for(i=0; i<6; i++) {
					for(j=0; j<3; j++) {
						$(table.rows[i].cells[j+1]).html(response[i][j]);
					}
				}
			}
		});
	}

	function download(filename, text) {
		var element = document.createElement('a');
		element.setAttribute('href', 'data:json;charset=utf-8,' + encodeURIComponent(text));
		element.setAttribute('download', filename);
		element.style.display = 'none';
		document.body.appendChild(element);
		element.click();
		document.body.removeChild(element);
	}

	function getParameters() {
		$.getJSON('/agricoltura/methods/getParameters', function(data){
			$('#interval-min').val(data['interval_min']);
			$('#min-temp').val(data['min_temp']);
			$('#max-temp').val(data['max_temp']);
			$('#max-hum').val(data['max_hum']);
			$('#min-moist').val(data['min_soil_moist']);
			$('#min-light').val(data['min_light_hours']);
			$('#max-moist').val(data['max_soil_moist']);
			$('#cam-h').val(data['cam_h']);
		});
	}

	function getRates() {
		$.getJSON('/agricoltura/methods/getRates', function(data){
			$('#elec-price').val(data['elec_price']);
			$('#water-price').val(data['water_price']);
			$('#fan-w').val(data['fan_w']);
			$('#pump-w').val(data['pump_w']);
			$('#pump-f').val(data['pump_f']);
			$('#light-w').val(data['light_w']);
			$('#server-w').val(data['server_w']);
		});
	}

});
