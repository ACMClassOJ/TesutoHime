$(function(){
	$.ajax({
        type: "POST",
        dataType: "text",
        url: "/get_username",
        success: function (response_text)
        {
			if(response_text == "Nobody")
			{
				document.getElementById('navbar_left').innerHTML = '\
					<ul class="navbar-nav navbar-nav-hover align-items-lg-right">\
			        	<li class="nav-item d-none d-lg-block ml-lg-4">\
				        	<a class="btn btn-neutral btn-icon">\
	              				<span class="nav-link-inner--text">登录</span>\
	            			</a>\
	            		</li>\
			          	<li class="nav-item d-none d-lg-block ml-lg-4">\
				        	<a class="btn btn-neutral btn-icon">\
	              				<span class="nav-link-inner--text">注册</span>\
	            			</a>\
	            		</li>\
	    			</ul>'
			}
			else
			{
				document.getElementById('navbar_left').innerHTML = '<div>欢迎您，' + response_text + '</div>';
			}
			
        },
    });
});