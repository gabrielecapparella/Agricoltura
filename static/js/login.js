$(document).ready(function(){
	$("#commit").click(function(){
	
		$.ajax({ url: '/agricoltura/methods/usrlogin', 
			type: 'POST',
			contentType: 'application/json', 
			data: JSON.stringify({ user: $("#user").val(), password:$("#password").val()}),
			success: function(response) {
				switch(response['result']) {
					case 1:
						$("#label").text("Wrong username, it must contain only letters and numbers");
						break;
					case 2:
						$("#label").text("Wrong credentials, try again");
						break;
					case 0:
						window.location.href = "/agricoltura";
				}
			}
		});	
	});
});
