document.getElementById('navbar_global').innerHTML = '\
<ul class="navbar-nav navbar-nav-hover align-items-lg-center">\
	<li class="nav-item">\
		<a href="/problems" class="nav-link" role="button">题库</a>\
	</li>\
	<li class="nav-item">\
		<a href="/contest" class="nav-link" role="button">比赛</a>\
	</li>\
	<li class="nav-item">\
		<a href="/homework" class="nav-link" role="button">作业</a>\
	</li>\
	<li class="nav-item">\
		<a href="/status" class="nav-link" role="button">评测状态</a>\
	</li>\
	<li class="nav-item">\
		<a href="/about" class="nav-link" role="button">关于</a>\
	</li>\
</ul>';

$(function(){
	$("#footer").html("<br><a href='https://github.com/cmd2001/Open-TesutoHime/' target='_blank'>TesutoHime</a>·ACM Class OnlineJudge 2020<br><br>");
});