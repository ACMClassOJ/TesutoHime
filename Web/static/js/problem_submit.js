const max_len = 16384;
$(function(){
	$("#code").keyup(function(){
		if(this.value.length > max_len)
		{
			swal("超过长度上限！", "最多提交"+max_len+"个字符", "error");
			this.value = this.value.substring(0, max_len);
		}
	});
});
function getCookie(cname)
{
	var name = cname + "=";
	var ca = document.cookie.split(';');
	for(var i = 0; i<ca.length; i++) 
	{
		var c = ca[i].trim();
		if (c.indexOf(name)==0)
			return c.substring(name.length,c.length);
	}
	return "";
}
function shared_checkbox_hide(x)
{
	if(x == 1)
	{
		$("#shared").attr("disabled", "disabled");
		$("#shared").attr("checked", "0");
	}
	else
	{
		if(getCookie("share_status") == "")
		{
			var exdate = new Date();
    		exdate.setTime(exdate.getTime() + 100*24*60*60*1000);
			document.cookie="share_status = 1; expires=" + exdate.toGMTString();
			$("#shared").attr("checked", "checked");
		}
		else if(getCookie("share_status") == 1)
			$("#shared").attr("checked", "checked");
	}
}
$(function(){
	$("#shared").change(function(){
		if($("#shared").attr("checked") == "checked")
		{
			var exdate = new Date();
    		exdate.setTime(exdate.getTime() + 100*24*60*60*1000);
			document.cookie="share_status = 0; expires=" + exdate.toGMTString();
		}
		else
		{
			var exdate = new Date();
    		exdate.setTime(exdate.getTime() + 100*24*60*60*1000);
			document.cookie="share_status = 1; expires=" + exdate.toGMTString();
		}
	});	
});

$(function(){
	$("#problem_submit_form").ajaxForm(function(response_text)
	{
		if(response_text == 0)
		{
			swal("Success","提交成功","success");
			setTimeout(function(){
				window.location.replace('/status');
			},500);
		}
		else
			swal("Oops","提交失败，网络故障！","error");
	});
});