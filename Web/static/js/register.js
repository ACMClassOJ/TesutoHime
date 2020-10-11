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
	$("#register").ajaxForm(function(response_text)
	{
		if(response_text == 0)
		{
			swal("Success","注册成功！您现在可以登陆了","success");
			setTimeout(function(){
				window.location.replace("/");
			},500);
		}
		else if(response_text == -1)
			swal("Oops","注册失败，检查您的输入信息！","error");
	});
});