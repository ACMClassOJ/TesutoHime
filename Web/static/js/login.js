var result = {};
$(function(){
    var url = window.location.href; 
    url = url.substr(url.indexOf("?")+1);
    var queryString = url || location.search.substring(1),
        re = /([^&=]+)=([^&]*)/g,
        m; 
   	while (m = re.exec(queryString))
        result[decodeURIComponent(m[1])] = decodeURIComponent(m[2]); 
});

$(function(){
	$("#login").ajaxForm(function(response_text)
	{
		if(response_text == 0)
		{
			swal("Success","登录成功","success");
			setTimeout(function(){
				window.location.replace(result['next']);
			},500);
		}
		else
			swal("Oops","用户名或密码错误","error");
	});
});