function getCookie(cname)
{
  var name = cname + "=";
  var ca = document.cookie.split(';');
  for(var i=0; i<ca.length; i++) 
  {
    var c = ca[i].trim();
    if (c.indexOf(name)==0)
    	return c.substring(name.length,c.length);
  }
  return "";
}
if(getCookie("username") == "")
{
	swal("Oops!", "您还没有登陆！", "info")
	.then(() => {
  		window.location.href="login.html";	
  	});
}