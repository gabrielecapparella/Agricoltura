$(document).ready(function(){
	$('#error-log').click(function(){getLog('/agricoltura/methods/getErrorLog', $(this));});
	$('#access-log').click(function(){getLog('/agricoltura/methods/getAccessLog', $(this));});
	$('#sensors-log').click(function(){getLog('/agricoltura/methods/getSensorsLog', $(this));});
	$('#db-log').click(function(){getLog('/agricoltura/methods/getDbLog', $(this));});
	

	getLog('/agricoltura/methods/getErrorLog', $('#error-log'));
	getUsers();
	
	$('#new-user-confirm').click(function(){
		$.ajax({ url: '/agricoltura/methods/addUser', 
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
			$.ajax({ url: '/agricoltura/methods/deleteUser', 
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
			$.ajax({ url: '/agricoltura/methods/regenerateApiKey', 
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

	function getLog(where, what) {
		$.get(where, function(data){
			$('#current-log').text(data);
			$('#log-btns>.my-btn-active').toggleClass('my-btn-active');
			what.toggleClass('my-btn-active');			
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
			
			$('#table-users tbody').html(content);
			
			$('#table-users tbody tr').click(function(){
				$('#table-users>tbody>tr').removeClass('checked-table-row');
				$(this).toggleClass('checked-table-row');
				
			});			
		});
	}
	
	// $('#poweroff').click(function(){$.get('/agricoltura/methods/poweroff');});
	// $('#reboot').click(function(){$.get('/agricoltura/methods/reboot');});
		
});
