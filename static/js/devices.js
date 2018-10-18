$(document).ready(function(){
	var raw_config;
	var sel_dev_type;
	var sel_dev_index;

	$.getJSON('/agricoltura/methods/getDevicesCfg', function(data){
		raw_config = data;
		click_dev_table($('#dev-table>tbody>tr:first'));
	});



	function click_dev_table(row) {
		$('#dev-table>tbody>tr').removeClass('checked-table-row');
		$(row).toggleClass('checked-table-row');
		sel_dev_type = $(row).children('.dev-type').html();
		sel_dev_index = $(row).attr('data-dev-index');
		dev_cfg = raw_config[sel_dev_type][sel_dev_index];
		$('#dev-raw-config>textarea').text(ident(dev_cfg));		
	}

	$('#dev-table tbody tr').click(function(){
		click_dev_table($(this));
	});

	$('#edit-dev-cfg').click(function(){
		usr_cfg = JSON.parse($('#dev-raw-config>textarea').val());
		$.ajax({ url: '/agricoltura/methods/editDevCfg', 
			type: 'POST',
			contentType: 'application/json', 
			data: JSON.stringify({ 
				type: sel_dev_type,
				index: sel_dev_index,
				cfg: usr_cfg
			}),
			success: function(response) {
				switch(response['result']) {
					case 0:
						$('#users-result').attr("class", "green");
						$("#edit-cfg-result").text("OK");
						break;
					case 1:
						$('#users-result').attr("class", "red");
						$("#edit-cfg-result").text("SYNTAX ERROR");
					case 2:
						$('#users-result').attr("class", "red");
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

	function indent(text) {
		return text.replace("{", "{\n\t").replace(/, /g, ",\n\t").replace("}", "\n}");
	}

});