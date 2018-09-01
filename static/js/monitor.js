$(document).ready(function(){
	$.getJSON('/methods/getLastReading', function(data){
		$('#temp-reading').html(data['temp']);
		$('#hum-reading').html(data['hum']);
		$('#moist-reading').html(data['moist']);
		$('#last-reading-timestamp').html(data['dt']);
	});

	$.getJSON('/methods/getActuators', function(data){
		if(data['sensors_on']) { $('#sensors-toggle').attr('class', 'toggle-button toggle-button-on p-0'); }
		if(data['actuators_on']) { $('#actuators-toggle').attr('class', 'toggle-button toggle-button-on p-0'); }
		if(data['light_on']) { $('#light-on').html('on'); }
		if(data['irrigation_on']) {  $('#water-on').html('on');  }
		if(data['fan_on']) { $('#fan-on').html('on'); }
	});
	
	Highcharts.setOptions({
		time: {
			timezone: 'Europe/Rome'
		}
	});
	
	$.getJSON('/methods/getParameters', function (data) { 
		thresholds = data; 

		function tempHistory() {
			$.getJSON('/methods/getTempHistory', function (data) {
					Highcharts.stockChart('current-chart', {
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

						yAxis: {
							title: {text: 'Temperature (°C)'},
							plotLines: [
								{value: thresholds['min_temp'], color: 'red', width: 1, label: {text: 'low', style:{color: 'red'}}, zIndex: 4},
								{value: thresholds['max_temp'], color: 'red', width: 1, label: {text: 'high', style:{color: 'red'}}, zIndex: 4}
							]
						},

						title: {text: 'Temperature History'},

						series: [{name: 'Temperature', data: data, tooltip: {valueDecimals: 1, valueSuffix: '°C'}}]

					});
					$('#chart-btns>.my-btn-active').toggleClass('my-btn-active');
					$('#temp-chart').toggleClass('my-btn-active');	
				});
		}

		function humHistory() {
			$.getJSON('/methods/getHumHistory', function (data) {
					Highcharts.stockChart('current-chart', {
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

						yAxis: {
							title: {text: 'Humidity (%)'},
							plotLines: [
								{value: thresholds['max_hum'], color: 'red', width: 1, label: {text: 'high', style:{color: 'red'}}, zIndex: 4}
							]
						},

						title: {text: 'Humidity History'},

						series: [{name: 'Humidity', data: data, tooltip: {valueDecimals: 1, valueSuffix: '%'}}]

					});
					$('#chart-btns>.my-btn-active').toggleClass('my-btn-active');
					$('#hum-chart').toggleClass('my-btn-active');					
				});
		}

		function moistHistory() {
			$.getJSON('/methods/getMoistHistory', function (data) {
				Highcharts.stockChart('current-chart', {
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

					yAxis: {
						title: {text: 'Soil Moisture (%)'},
						plotLines: [
							{value: thresholds['min_soil_moist'], color: 'red', width: 1, label: {text: 'low', style:{color: 'red'}}, zIndex: 4}
						]
					},

					title: {text: 'Soil Moisture'},

					series: [{name: 'Soil Moisture', data: data, tooltip: {valueDecimals: 1, valueSuffix: '%'}}]

				});
				
				$('#chart-btns>.my-btn-active').toggleClass('my-btn-active');
				$('#moist-chart').toggleClass('my-btn-active');
			});
		}

		tempHistory();

		$('#temp-chart').click(tempHistory);
		$('#hum-chart').click(humHistory);
		$('#moist-chart').click(moistHistory);
	});
});
