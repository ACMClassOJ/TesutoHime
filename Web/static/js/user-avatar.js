$(function(){
	$.ajax({
        type: "POST",
        dataType: "text",
        url: "/get_username",
        success: function (response_text)
        {
			if(response_text == "Nobody")
			{
				document.getElementById('navbar_right').innerHTML = '\
					<ul class="navbar-nav navbar-nav-hover align-items-lg-right">\
			        	<li class="nav-item d-none d-lg-block ml-lg-4">\
				        	<a class="btn btn-neutral btn-icon" href="/login">\
	              				<span class="nav-link-inner--text">登录</span>\
	            			</a>\
	            		</li>\
			          	<li class="nav-item d-none d-lg-block ml-lg-4">\
				        	<a class="btn btn-neutral btn-icon" href="/register">\
	              				<span class="nav-link-inner--text">注册</span>\
	            			</a>\
	            		</li>\
	    			</ul>'
			}
			else
			{
				document.getElementById('navbar_right').innerHTML = '<div>当前用户：<b>' + response_text + '</b><b><a href="/logout"> &nbsp&nbsp注销</a></b></div>';
			}
			
        },
    });
});