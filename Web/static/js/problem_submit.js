const max_len = 16384;
$(function(){
	$("#problem_submit_code").keyup(function(){
		if(this.value.length > max_len)
		{
			swal("超过长度上限！", "最多提交"+max_len+"个字符", "error");
			this.value = this.value.substring(0, max_len);
		}
	});
});