$(function(){
	$("#register").ajaxForm(function(response_text)
	{
		if(response_text == 0)
		{
			swal("Success","注册成功！您现在可以登陆了","success");
			setTimeout(function(){window.location.replace("../../login.html");},1000);
		}
		else if(response_text == -1)
			swal("Oops","注册失败，检查您的输入信息！","error");
	});
});