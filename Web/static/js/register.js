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
	$("#register").ajaxForm(function(ret_json)
	{
		if(ret_json['e'] < 0)
			swal("Error " + ret_json['e'], ret_json['msg'], "error");
		else
		{
			swal("Success", ret_json['msg'], "success");
			setTimeout(function(){
				window.location.replace("/OnlineJudge/compiler/");
			},500);
		}
	});
});