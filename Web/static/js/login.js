let result = {};
$(function(){
    let url = window.location.href; 
    url = url.substr(url.indexOf("?")+1);
    let queryString = url || location.search.substring(1),
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
				if(result['next'])
					window.location.replace(result['next']);
				else
					window.location.replace('/');
			},500);
		}
		else
			swal("Oops","用户名或密码错误","error");
	});
});