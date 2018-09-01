$(document).ready(function(){
	$('#error-log').click(function(){getLog('/methods/getErrorLog', $(this));});
	$('#access-log').click(function(){getLog('/methods/getAccessLog', $(this));});
	$('#sensors-log').click(function(){getLog('/methods/getSensorsLog', $(this));});
	$('#db-log').click(function(){getLog('/methods/getDbLog', $(this));});
	

	getLog('/methods/getErrorLog', $('#error-log'));
	getUsers();
	
	$('#new-user-confirm').click(function(){
		$.ajax({ url: '/methods/addUser', 
			type: 'POST',
			contentType: 'application/json', 
			data: JSON.stringify({ 
				username: $("#new-user-username").val(), 
				password: $("#new-user-password").val(),
				is_admin: $("#new-user-check").is(":checked"), 
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
				close_modal()
			},
			error: function(response) {
				$('#users-result').attr('class', 'text-monospace text-danger');
				$('#users-result').text('ERROR');
				close_modal()
			}
		});	
	});



	$('#del-user').click(function(){
		if($('#table-users>tbody>tr.checked-table-row').length) {
			$.ajax({ url: '/methods/deleteUser', 
				type: 'POST',
				contentType: 'application/json', 
				data: JSON.stringify({ 
					username: $('#table-users>tbody>tr.checked-table-row>.usr').html()
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
					close_modal()
				},
				error: function(response) {
					$('#users-result').attr('class', 'text-monospace text-danger');
					$('#users-result').text('ERROR');
					close_modal()
				}
			});
		}
	});

	$('#new-api-key').click(function(){
		if($('#table-users>tbody>tr.checked-table-row').length) {
			$.ajax({ url: '/methods/regenerateApiKey', 
				type: 'POST',
				contentType: 'application/json', 
				data: JSON.stringify({ 
					username: $('#table-users>tbody>tr.checked-table-row>.usr').html()
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
					close_modal()
				},
				error: function(response) {
					$('#users-result').attr('class', 'text-monospace text-danger');
					$('#users-result').text('ERROR');
					close_modal()
				}
			});
		}
	});

	function close_modal() {
		$('#modal-add-user').modal('hide');
		$("#new-user-username").val('');
		$("#new-user-password").val('');
		$("#new-user-check").prop('checked', false);				
	}

	function getLog(where, what) {
		$.get(where, function(data){
			$('#current-log').text(data);
			$('#log-btns>.my-btn-active').toggleClass('my-btn-active');
			what.toggleClass('my-btn-active');			
		});
	}
	
	function getUsers() {
		$.getJSON('/methods/getUsers', function(data){
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
			
			$('#table-users tbody').html(content);
			
			$('#table-users tbody tr').click(function(){
				$('#table-users>tbody>tr').removeClass('checked-table-row');
				$(this).toggleClass('checked-table-row');
				
			});			
		});
	}
	
	$.getJSON('/methods/getSystemStatus', function(data){
		$('#cpu-temp').html(data['cpu_temp']);
		$('#uptime').html(data['uptime']);
		$('#storage').attr('aria-valuenow', data['st_perc']);
		$('#storage').attr('style', 'width: '+data['st_perc']+'%');
		$('#ram').attr('aria-valuenow', data['mem_perc']);
		$('#ram').attr('style', 'width: '+data['mem_perc']+'%');		
	});
	
	$('#poweroff').click(function(){$.get('/methods/poweroff');});
	$('#reboot').click(function(){$.get('/methods/reboot');});
		
});
