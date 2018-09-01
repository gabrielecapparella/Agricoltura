$(document).ready(function() { 
	$(document).on("click", "#update", function(){
		$.getJSON('/methods/getLastReading', function(data){
			$('#temp').html(data['temp']);
			$('#hum').html(data['hum']);
			$('#moist').html(data['moist']);
		});
	});
});
