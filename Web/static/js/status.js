let result = {};
$(function () {
`    let url = window.location.href;
    url = url.substr(url.indexOf("?") + 1);
    let queryString = url || location.search.substring(1),
        re = /([^&=]+)=([^&]*)/g,
        m;
    while (m = re.exec(queryString))
        result[decodeURIComponent(m[1])] = decodeURIComponent(m[2]);
`    if (result['submitter'])
        $("#submitter").val(result['submitter']);
    if (result['problem_id'])
        $("#problem_id").val(result['problem_id']);
    if (result['status'])
        $("#status").val(result['status']);
    if (result['lang'])
        $("#lang").val(result['lang']);
});