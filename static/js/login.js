$(document).ready(function(){
	$("#commit").click(function(){
	
		$.ajax({ url: '/methods/usrlogin', 
			type: 'POST',
			contentType: 'application/json', 
			data: JSON.stringify({ user: $("#user").val(), password:$("#password").val()}),
			success: function(response) {
				//alert(response['result'])
				switch(response['result']) {
					case '1':
						$("#label").text("Wrong username, it must contain only letters and numbers");
						break;
					case '2':
						$("#label").text("Wrong credentials, try again");
						break;
					default:
						window.location.href = "/";
				}
			}
		});	
	});
});
