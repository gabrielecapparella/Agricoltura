$(document).ready(function(){
	$('#logs-main').click(function(){getLog('/agricoltura/methods/getMainLog', $(this));});
	$('#logs-sensors').click(function(){getLog('/agricoltura/methods/getSensorsLog', $(this));});
	$('#logs-db').click(function(){getLog('/agricoltura/methods/getDbLog', $(this));});
	

	getLog('/agricoltura/methods/getMainLog', $('#logs-main'));
	getUsers();
	
	$('#users-add').click(function(){
		var pwd = $("#users-pwd").val();
		if (pwd===$("#users-pwd-confirm").val()) {
			$.ajax({ url: '/agricoltura/methods/addUser', 
				type: 'POST',
				contentType: 'application/json', 
				data: JSON.stringify({ 
					username: $("#users-username").val(), 
					password: pwd,
					is_admin: $("#users-admin").is(":checked"), 
				}),
				success: function(response) {
					if(response['result']) { 
						$('#users-result').attr('class', 'text-monospace text-success');
						$('#users-result').text('OK');
						getUsers(); 
					} else {
						$('#users-result').attr('class', 'text-monospace text-danger');
						$('#users-result').text('ERROR');
					}
				},
				error: function(response) {
					$('#users-result').attr('class', 'text-monospace text-danger');
					$('#users-result').text('ERROR');
				}
			});
		} else {
			$('#users-result').attr('class', 'text-monospace text-danger');
			$('#users-result').text("Passwords don't match");
		}
	});



	$('#users-delete').click(function(){
		if($('#users-table>tbody>tr.checked-table-row').length) {
			$.ajax({ url: '/agricoltura/methods/deleteUser', 
				type: 'POST',
				contentType: 'application/json', 
				data: JSON.stringify({ 
					username: $('#users-table>tbody>tr.checked-table-row>.usr').html()
				}),
				success: function(response) {
					if(response['result']) { 
						$('#users-result').attr('class', 'text-monospace text-success');
						$('#users-result').text('OK');
						getUsers(); 
					} else {
						$('#users-result').attr('class', 'text-monospace text-danger');
						$('#users-result').text('ERROR');
					}
				},
				error: function(response) {
					$('#users-result').attr('class', 'text-monospace text-danger');
					$('#users-result').text('ERROR');
				}
			});
		}
	});

	$('#users-new-api').click(function(){
		if($('#users-table>tbody>tr.checked-table-row').length) {
			$.ajax({ url: '/agricoltura/methods/regenerateApiKey', 
				type: 'POST',
				contentType: 'application/json', 
				data: JSON.stringify({ 
					username: $('#users-table>tbody>tr.checked-table-row>.usr').html()
				}),
				success: function(response) {
					if(response['result']) { 
						$('#users-result').attr('class', 'text-monospace text-success');
						$('#users-result').text('OK');
						getUsers(); 
					} else {
						$('#users-result').attr('class', 'text-monospace text-danger');
						$('#users-result').text('ERROR');
					}
				},
				error: function(response) {
					$('#users-result').attr('class', 'text-monospace text-danger');
					$('#users-result').text('ERROR');
				}
			});
		}
	});

	function getLog(where, what) {
		$.get(where, function(data){
			$('#logs-textarea').text(data);
			$('#logs-bottom>.blue-button-active').toggleClass('blue-button-active');
			what.toggleClass('blue-button-active');			
		});
	}
	
	function getUsers() {
		$.getJSON('/agricoltura/methods/getUsers', function(data){
			var i, content='';
			data.forEach(function(i) {
				if (i[2]) {type = 'administrator';}
				else { type = 'regular';}
				
				content += '<tr>';
				content += '<td class="usr">'+i[0]+'</td>'; 
				content += '<td>'+type+'</td>';
				content += '<td>'+i[1]+'</td>';
				content += '</tr>';
			});
			
			$('#users-table tbody').html(content);
			
			$('#users-table tbody tr').click(function(){
				$('#users-table>tbody>tr').removeClass('checked-table-row');
				$(this).toggleClass('checked-table-row');
				
			});			
		});
	}
	
	// $('#poweroff').click(function(){$.get('/agricoltura/methods/poweroff');});
	// $('#reboot').click(function(){$.get('/agricoltura/methods/reboot');});
		
});
