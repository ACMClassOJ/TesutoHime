$(function(){
	$.ajax({
        type: "POST",
        dataType: "text",
        url: "/api/get_username",
        success: function (response_text)
        {
			var _mtac = {};
			(function() {
				var mta = document.createElement("script");
				mta.src = "//pingjs.qq.com/h5/stats.js?v2.0.4";
				mta.setAttribute("name", "MTAH5");
				mta.setAttribute("sid", "500731541");
				mta.setAttribute("cid", "500731570");
				var s = document.getElementsByTagName("script")[0];
				s.parentNode.insertBefore(mta, s);
			})();

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