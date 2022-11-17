$(function(){
    $("input").on('keypress', function(e){
        var key = window.event ? e.keyCode : e.which;
        if(key.toString() == "13")
            return false;
    });
});

$.fn.serializeObject = function () {
    let data = {};
    this.serializeArray().forEach(function (e) {
        if (e.value !== "")
            if (e.name.search("[T t]ime") !== -1)
                data[e.name] = Math.floor(new Date(e.value).getTime() / 1000);
            else if ($("#" + e.name))
                data[e.name] = e.value;
    });
    return data;
}

function formatDate(date)
{
    var date = new Date(date);
    var YY = date.getFullYear() + '-';
    var MM = (date.getMonth() + 1 < 10 ? '0' + (date.getMonth() + 1) : date.getMonth() + 1) + '-';
    var DD = (date.getDate() < 10 ? '0' + (date.getDate()) : date.getDate());
    var hh = (date.getHours() < 10 ? '0' + date.getHours() : date.getHours()) + ':';
    var mm = (date.getMinutes() < 10 ? '0' + date.getMinutes() : date.getMinutes());
    return YY + MM + DD +"T"+ hh + mm;
}

function getUrlArg(arg)
{
    var query = window.location.search.substring(1);
    var vars = query.split("&");
    for (var i=0;i<vars.length;i++) {
        var pair = vars[i].split("=");
        if(pair[0] == arg){
            return pair[1];
        }
    }
    return false;
}

window.onload = function() {
    problem_id = getUrlArg('problem_id');
    contest_id = getUrlArg('contest_id');

    if (problem_id != false) {
        $("#iptProblemID").val(problem_id);
        document.getElementById('btnGetProblemDetails').click();
    }
    else if (contest_id != false) {
        document.getElementById('contest_tab_btn').click();
        $("#iptContestID").val(contest_id);
        document.getElementById('btnGetContestDetails').click();
    }
}

let op;
$(function () {

    $("#btnAddUser").click(function () {
        op = 0;
    });
    $("#btnModifyUser").click(function () {
        op = 1;
    });
    $("#btnRemoveUser").click(function () {
        op = 2;
    });
    $("#formUser").submit(function (e) {
        e.preventDefault();
        e.stopPropagation();
        let data = $(this).serializeObject();
        data.type = op;
        console.log(data);
        $.ajax({
            type: "POST",
            contentType: "application/json",
            url: "/OnlineJudge/admin/user",
            dataType: "json",
            data: JSON.stringify(data),
            complete: function (ret) {
                var ret_json = JSON.parse(ret.responseText);
                if(ret_json['e'] < 0)
                    swal("Error " + ret_json['e'], ret_json['msg'], "error");
                else
                    swal("Success", ret_json['msg'], "success");
            }
        });
    });

    var editors = {};
    function new_or_modify_content_in_editormd(editormd_name, content)
    {
        var new_editor = editormd(editormd_name, {
            width: "100%",
            height: 400,
            path: "/OnlineJudge/static/lib/editor.md/lib/",
            toolbarIcons: function() {
                return [
                    "undo", "redo", "|",
                    "bold", "del", "italic", "quote", "|",
                    "h1", "h2", "h3", "h4", "h5", "h6", "|",
                    "list-ul", "list-ol", "hr", "|",
                    "link", "reference-link", "image", "code", "preformatted-text", "code-block", "table", "html-entities", "pagebreak", "|",
                    "watch", "preview", "fullscreen", "clear", "search", "||",
                    "help", "info"
                ];
            },
            markdown: content,
            autoFocus: false,
            placeholder: "支持 Markdown 及 HTML 格式，支持留空。",
            codeFold: true,
            searchReplace: true,
            htmlDecode: "style,script,iframe|onclick,title,onmouseover,onmouseout,style",
            taskList: true,
            tocm: true,
            tex: false,
            flowChart: true,
            sequenceDiagram: true,
            atLink: false,
            emailLink: true,
            pageBreak: true
        });
        editors[editormd_name] = new_editor;
    }

    $("#divProblemHidden").hide();

    $("#btnGoToProblemPage").click(function(){
        if($("#iptProblemID").val() != "")
            window.location.replace('/OnlineJudge/problem?problem_id=' + $("#iptProblemID").val());
    });

    $("#btnGetProblemAutoIncreseID").click(function(){
        $.ajax({
            type: "POST",
            dataType: "text",
            url: "/OnlineJudge/api/get_problem_id_autoinc",
            success: function (response_text)
            {
                $("#iptProblemID").val(parseInt(response_text));
                document.getElementById('btnGetProblemDetails').click();
            }
        });
    });

    $("#btnGetProblemDetails").click(function(){
        $("#btnAddProblem").attr("disabled","disabled");
        $("#btnModifyProblem").attr("disabled","disabled");
        $("#btnRemoveProblem").attr("disabled","disabled");
        $("#iptTitle").val("");
        $("#iptReleaseTime").val(formatDate(new Date()));
        $("#iptProblemType").selectpicker("val", "0");
        if($("#iptProblemID").val() == "")
        {
            $("#divProblemHidden").slideUp(500);
            return;
        }
        $("#divProblemHidden").slideDown(500);
        $.ajax({
            type: "POST",
            dataType: "text",
            data: {problem_id: $("#iptProblemID").val()},
            url: "/OnlineJudge/api/get_detail",
            success: function (response_text)
            {
                var is_empty;
                var main_json;
                if(response_text == "{}")
                {
                    is_empty = 1;
                    $("#btnAddProblem").removeAttr("disabled");
                    $("#iptProblemStatusBadge").removeClass();
                    $("#iptProblemStatusBadge").addClass("badge badge-secondary");
                    $("#iptProblemStatusBadge").text("空");
                }
                else
                {
                    is_empty = 0;
                    $("#btnModifyProblem").removeAttr("disabled");
                    $("#btnRemoveProblem").removeAttr("disabled");
                    $("#iptProblemStatusBadge").removeClass();
                    $("#iptProblemStatusBadge").addClass("badge badge-success");
                    $("#iptProblemStatusBadge").text("已存在");
                    main_json = JSON.parse(response_text);
                    $("#iptTitle").val(main_json['Title']);
                    $("#iptReleaseTime").val(formatDate(main_json['Release_Time'] * 1000));
                    $("#iptProblemType").val(main_json['Problem_Type']);
                    $("#iptProblemType").selectpicker("val", main_json['Problem_Type']);
                }
                new_or_modify_content_in_editormd("iptDescription", is_empty ? "None" : main_json['Description']);
                new_or_modify_content_in_editormd("iptInput", is_empty ? "None" : main_json['Input']);
                new_or_modify_content_in_editormd("iptOutput", is_empty ? "None" : main_json['Output']);
                new_or_modify_content_in_editormd("iptExampleInput", is_empty ? "None" : main_json['Example_Input']);
                new_or_modify_content_in_editormd("iptExampleOutput", is_empty ? "None" : main_json['Example_Output']);
                new_or_modify_content_in_editormd("iptDataRange", is_empty ? "None" : main_json['Data_Range']);

                // $("#iptDescription").val(main_json['Description']);
                // $("#iptInput").val(main_json['Input']);
                // $("#iptOutput").val(main_json['Output']);
                // $("#iptExampleInput").val(main_json['Example_Input']);
                // $("#iptExampleOutput").val(main_json['Example_Output']);
                // $("#iptDataRange").val(main_json['Data_Range']);
            },
            error: function () {
                $("#divProblemHidden").slideUp(500);
            }
        });
    });

    $(function(){
        setInterval(function(){
            $(".markdown-body").each(function(){
                renderMathInElement($(this)[0],
                    {
                        delimiters: [
                            {left: "$$", right: "$$", display: true},
                            {left: "$", right: "$", display: false},
                            {left: "\\(", right: "\\)", display: false}
                        ]
                    });
            });
        }, 1000);
    });


    $("#btnAddProblem").click(function () {
        op = 0;
    });
    $("#btnModifyProblem").click(function () {
        op = 1;
    });
    $("#btnRemoveProblem").click(function () {
        op = 2;
    });
    $("#formProblem").submit(function (e) {
        e.preventDefault();
        e.stopPropagation();
        let data = $(this).serializeObject();
        data.type = op;
        console.log(data);
        $.ajax({
            type: "POST",
            contentType: "application/json",
            url: "/OnlineJudge/admin/problem",
            dataType: "json",
            data: JSON.stringify(data),
            complete: function (ret) {
                var ret_json = JSON.parse(ret.responseText);
                if(ret_json['e'] < 0)
                    swal("Error " + ret_json['e'], ret_json['msg'], "error");
                else
                    swal("Success", ret_json['msg'], "success");
                document.getElementById('btnGetProblemDetails').click();
            }
        });
    });

    $("#divContestHidden").hide();
    $("#divContestProblemListHidden").hide();
    $("#divContestUserListHidden").hide();

    $("#btnGoToContestPage").click(function(){
        if($("#iptContestID").val() != "")
            window.location.replace('/OnlineJudge/contest?contest_id=' + $("#iptContestID").val());
    });

    $("#btnGetContestAutoIncreseID").click(function(){
        $.ajax({
            type: "POST",
            dataType: "text",
            url: "/OnlineJudge/api/get_contest_id_autoinc",
            success: function (response_text)
            {
                $("#iptContestID").val(parseInt(response_text));
                document.getElementById('btnGetContestDetails').click();
            }
        });
    });

    $("#btnGetContestDetails").click(function(){
        $("#divContestProblemListHidden").slideUp();
        $("#divContestUserListHidden").slideUp();
        $("#btnCreateContest").attr("disabled","disabled");
        $("#btnModifyContest").attr("disabled","disabled");
        $("#btnRemoveContest").attr("disabled","disabled");
        $("#iptContestName").val("");
        $("#iptStartTime").val(formatDate(new Date()));
        $("#iptEndTime").val(formatDate(new Date(2030, 0, 1, 0, 0, 0, 0)));
        $("#iptContestType").selectpicker("val", "0");
        $.ajax({
            type: "POST",
            dataType: "text",
            data: {contest_id: $("#iptContestID").val()},
            url: "/OnlineJudge/api/get_contest_detail",
            success: function (response_text)
            {
                if(response_text == "{}")
                {
                    $("#btnCreateContest").removeAttr("disabled");
                    $("#iptContestStatusBadge").removeClass();
                    $("#iptContestStatusBadge").addClass("badge badge-secondary");
                    $("#iptContestStatusBadge").text("空");
                }
                else
                {
                    $("#btnModifyContest").removeAttr("disabled");
                    $("#btnRemoveContest").removeAttr("disabled");
                    $("#iptContestStatusBadge").removeClass();
                    $("#iptContestStatusBadge").addClass("badge badge-success");
                    $("#iptContestStatusBadge").text("已存在");
                    var main_json = JSON.parse(response_text);
                    $("#iptContestName").val(main_json['Name']);
                    $("#iptStartTime").val(formatDate(main_json['Start_Time'] * 1000));
                    $("#iptEndTime").val(formatDate(main_json['End_Time'] * 1000));
                    $("#iptContestType").selectpicker("val", main_json['Type']);
                }
            }
        });
        $("#divContestHidden").slideDown(500);
    });

    $("#btnShowUserList").click(function () {
        $("#divContestUserListHidden").slideDown(500);
    });
    $("#btnShowProblemList").click(function () {
        $("#divContestProblemListHidden").slideDown(500);
    });
    $("#btnCreateContest").click(function () {
        op = 0;
    });
    $("#btnModifyContest").click(function () {
        op = 1;
    });
    $("#btnRemoveContest").click(function () {
        op = 2;
    });
    $("#btnAddProblemToContest").click(function () {
        op = 3;
    });
    $("#btnRemoveProblemFromContest").click(function () {
        op = 4;
    });
    $("#btnAddUserToContest").click(function () {
        op = 5;
    });
    $("#btnRemoveUserFromContest").click(function () {
        op = 6;
    });
    $("#formContest").submit(function (e) {
        e.preventDefault();
        e.stopPropagation();
        let data = $(this).serializeObject();
        if (data.hasOwnProperty("id"))
            data.id = data.id.split(/\s+/);
        if (data.hasOwnProperty("username"))
            data.username = data.username.split(/\s+/);
        data.type = op;
        console.log(data);
        $.ajax({
            type: "POST",
            contentType: "application/json",
            url: "/OnlineJudge/admin/contest",
            dataType: "json",
            data: JSON.stringify(data),
            complete: function (ret) {
                var ret_json = JSON.parse(ret.responseText);
                if(ret_json['e'] < 0)
                    swal("Error " + ret_json['e'], ret_json['msg'], "error");
                else
                    swal("Success", ret_json['msg'], "success");
                document.getElementById('btnGetContestDetails').click();
            }
        });
    });

    $("#btnAddGroupsRow").click(function () {
        let t = $("#tableGroups"), r = t.find("tr:last").clone(), td = r.children();
        if (!isNaN(td.eq(1).html())) {
            td.eq(1).html(parseInt(td.eq(1).html()) + 1);
        }
        if (!isNaN(td.last().html())) {
            td.last().html(parseInt(td.last().html()) + 1);
        }
        td.first().html(parseInt(td.first().html()) + 1);
        t.append(r);
    });
    $("#btnRemoveGroupsRow").click(function () {
        $("#tableGroups").children().last().remove();
    });
    $("#btnAddDetailsRow").click(function () {
        let t = $("#tableDetails"), r = t.find("tr:last").clone(), td = r.children();
        td.eq(1).html(parseInt(td.eq(1).html()) === parseInt(td.first().html()) - 1 && td.eq(1).html() !== "0" ? td.first().html() : 0);
        td.first().html(parseInt(td.first().html()) + 1);
        t.append(r);
    });
    $("#btnRemoveDetailsRow").click(function () {
        $("#tableDetails").children().last().remove();
    });
    $("#btnClearConfig").click(function () {
        $("#iptConfig").val("");
    });

    function extract_limit() {
        let tableDetails = $("#tableDetails");
        let config = {};
        config["length"] = tableDetails.children().length;
        config["mem"] = [];
        config["time"] = [];
        config["disk"] = [];
        tableDetails.children().each(function (i, e) {
            let d = e.children;
            config["time"].push(parseInt(d[2].innerHTML.replace("<br>", "")));
            config["mem"].push(parseInt(d[3].innerHTML.replace("<br>", "")));
            config["disk"].push(parseInt(d[4].innerHTML.replace("<br>", "")));
        });
        return config;
    }

    function generateConfig() {
        let tableGroups = $("#tableGroups"), tableDetails = $("#tableDetails"), config = "";
        config += `{"Groups":[`;
        tableGroups.children().each(function (i, e) {
            let d = e.children;
            config += `${i ? "," : ""}{"GroupID":${d[0].innerHTML.replace("<br>", "")},"GroupName":"${d[1].innerHTML.replace("<br>", "")}",` +
                `"GroupScore":${d[2].innerHTML.replace("<br>", "")},"TestPoints":[${d[3].innerHTML.replace("<br>", "")}]}`;
        });
        config += `],"Details":[`;
        tableDetails.children().each(function (i, e) {
            let d = e.children;
            config += `${i ? "," : ""}{"ID":${d[0].innerHTML.replace("<br>", "")},"Dependency":${d[1].innerHTML.replace("<br>", "")},` +
                `"TimeLimit":${d[2].innerHTML.replace("<br>", "")},"MemoryLimit":${d[3].innerHTML.replace("<br>", "")},` +
                `"DiskLimit":${d[4].innerHTML.replace("<br>", "")},"ValgrindTestOn":${$(d[5]).find("input").is(":checked") ? "true" : "false"}}`;
        });
        let type = $("#iptSpjType");
        config += `],"CompileTimeLimit":${$("#iptCompileTime").val()},"SPJ":${type.val()},` +
            `"Scorer":${type.val() === 3 ? 1 : 0}}`;
        return config;
    }

    $("#formData").submit(function (e) {
        e.preventDefault();
        e.stopPropagation();
        $.ajax({
            url: "/OnlineJudge/admin/problem_limit",
            type: "POST",
            data: {id: $("#iptDataProblemID").val(), data: JSON.stringify(extract_limit())},
            dataType: "json",
            complete: function (ret) {
                var ret_json = JSON.parse(ret.responseText);
                if(ret_json['e'] < 0)
                {
                    swal("Error " + ret_json['e'], ret_json['msg'], "error");
                    return;
                }
            }
        });
        let zip = new JSZip();
        let folder = zip.folder($("#iptDataProblemID").val());
        let data_files = $("#iptData");
        let description_md = $("#iptDescriptionMd");
        let type = $("#iptSpjType");
        let spj = $("#iptSpj");
        let scorer = $("#iptScorer");
        // let config = $("#iptConfig");
        if (data_files.val() !== null && data_files.val() !== "") {
            data_files = data_files[0].files;
            $(data_files).each(function (index, file) {
                folder.file(file.name, file);
            });
        }
        if (description_md.val() !== null && description_md.val() !== "") {
            description_md = description_md[0].files[0];
            folder.file(description_md.name, description_md);
        }
        if (type.val() === 1 || type.val() === 2 && spj.val() !== null && spj.val() !== "") {
            spj = spj[0].files[0];
            folder.file(spj.name, spj);
        }
        if (type.val() === 3 && scorer.val() !== null && scorer.val() !== "") {
            scorer = scorer[0].files[0];
            folder.file(scorer.name, scorer);
        }
        // if (config.val() !== null && config.val() !== "") {
        //     config = config[0].files[0];
        //     folder.file("config.json", config);
        // } else {
            folder.file("config.json", generateConfig());
        // }
        zip.generateAsync({
            type: "blob"
        }).then(function (blob) {
            let data = new FormData(), id = $("#iptDataProblemID").val();
            data.append("file", blob, id + ".zip");
            console.log(data);
            $.ajax({
                url: "/OnlineJudge/admin/data",
                type: "POST",
                processData: false,
                contentType: false,
                data: data,
                dataType: "json",
                complete: function (ret) {
                    var ret_json = JSON.parse(ret.responseText);
                    if(ret_json['e'] < 0)
                        swal("Error " + ret_json['e'], ret_json['msg'], "error");
                    else
                        swal("Success", ret_json['msg'], "success");
                }
            });
        });
    });

    $("#formDataZipUpload").submit(function (e) {
        e.preventDefault();
        e.stopPropagation();
        var long_zip_name = $("#iptDataZipUpload").val();
        var zip_name = long_zip_name.substring(long_zip_name.lastIndexOf("\\")+1, long_zip_name.lastIndexOf("."));
        if(isNaN(zip_name) || parseInt(zip_name) < 1000)
        {
            swal("Error", "数据包名不正确！", "error");
            return;
        }
        JSZip.loadAsync($("#iptDataZipUpload").prop("files")[0]).then(function (zip) {
            zip.file(zip_name + "/config.json").async("string").then(function (config) {
                var config_json = JSON.parse(config);
                let limit_config = {};
                limit_config["length"] = config_json["Details"].length;
                limit_config["mem"] = [];
                limit_config["time"] = [];
                limit_config["disk"] = [];
                limit_config["file"] = [];
                config_json["Details"].forEach(function (item) {
                    limit_config["time"].push(item["TimeLimit"]);
                    limit_config["mem"].push(item["MemoryLimit"]);
                    if("DiskLimit" in item)
                        limit_config["disk"].push(item["DiskLimit"]);
                    if("FileNumberLimit" in item)
                        limit_config["file"].push(item["FileNumberLimit"]);
                });
                console.log(limit_config);
                $.ajax({
                    url: "/OnlineJudge/admin/problem_limit",
                    type: "POST",
                    data: {id: zip_name, data: JSON.stringify(limit_config)},
                    dataType: "json",
                    complete: function (ret) {
                        var ret_json = JSON.parse(ret.responseText);
                        if(ret_json['e'] < 0) {
                            swal("Error " + ret_json['e'], ret_json['msg'], "error");
                            return;
                        }
                    }
                });
            });
        }, function (err) {
            var jszip_error_text = document.createElement("p");
            jszip_error_text.innerHTML = err.message + '<br> 无法从压缩包中提取 config.json，因此无法更新网页上的时空磁盘限制（运行时）。'
                                                     + '<br> 参考下方链接来测试压缩包是否符合规范。'
                                                     + '<br> 此警告不会影响数据包上传与评测。';
            swal({
                icon: "warning",
                title: "压缩包不符合规范",
                content: jszip_error_text,
                buttons: {
                    test_zip: {
                      text: "测试链接",
                      value: "test_zip",
                    },
                    confirm: true
                },
                timer: 5000
            }).then((value) => {
                if(value == "test_zip")
                    window.open("https://stuk.github.io/jszip/documentation/examples/read-local-file-api.html");
            });
        });

        let data = new FormData(this);
        $.ajax({
            url: "/OnlineJudge/admin/data",
            type: "POST",
            processData: false,
            contentType: false,
            data: data,
            dataType: "json",
            complete: function (ret) {
                var ret_json = JSON.parse(ret.responseText);
                if(ret_json['e'] < 0)
                    swal("Error " + ret_json['e'], ret_json['msg'], "error");
                else
                    swal("Success", ret_json['msg'], "success");
            }
        });
    });

    $("#formPicUpload").submit(function (e) {
        e.preventDefault();
        e.stopPropagation();
        let data = new FormData(this);
        $("#btnPicUpload").attr("disabled", "disabled");
        $.ajax({
            url: "/OnlineJudge/admin/pic",
            type: "POST",
            processData: false,
            contentType: false,
            data: data,
            complete: function (ret) {
                var ret_json = JSON.parse(ret.responseText);
                if(ret_json['e'] < 0)
                    swal("Error " + ret_json['e'], ret_json['msg'], "error");
                else
                {
                    var swal_content = document.createElement("p");
                    swal_content.innerHTML = '<img src="' + ret_json['link'] + '" style="width: 33%"><br>';
                    swal_content.innerHTML += "<xmp id='swal_content_url'>" + ret_json['link'] + "</xmp>";
                    swal_content.innerHTML += '<xmp id="swal_content_html"><img src="' + ret_json['link'] + '" style="width: 100%"></xmp>';
                    swal_config = {
                        title: ret_json['msg'],
                        icon: "success",
                        content: swal_content,
                        buttons: {
                            copy_url: {
                                text: "复制链接",
                                value: "copy_url",
                                className: "copy_url",
                                closeModal: false
                            },
                            copy_html: {
                                text: "复制html",
                                value: "copy_html",
                                className: "copy_html",
                                closeModal: false
                            }
                        }
                    };
                    swal(swal_config);
                    $(".swal-modal").css("width", "70%");
                    document.getElementsByClassName('copy_url')[0].setAttribute("data-clipboard-target", "#swal_content_url");
                    var clipboard1 = new ClipboardJS(document.getElementsByClassName('copy_url')[0]);
                    document.getElementsByClassName('copy_html')[0].setAttribute("data-clipboard-target", "#swal_content_html");
                    var clipboard2 = new ClipboardJS(document.getElementsByClassName('copy_html')[0]);
                }
                var upload_input_bar = $("#iptPicUpload");
                upload_input_bar.after(upload_input_bar.clone().val(""));
                upload_input_bar.remove();
                $("#btnPicUpload").removeAttr("disabled");
            }
        });
    });

    $("#formRejudge").ajaxForm(function (ret_json) {
        if(ret_json['e'] < 0)
            swal("Error " + ret_json['e'], ret_json['msg'], "error");
        else
            swal("Success", ret_json['msg'], "success");
    });

    $("#formRejudge2").ajaxForm(function (ret_json) {
        if(ret_json['e'] < 0)
            swal("Error " + ret_json['e'], ret_json['msg'], "error");
        else
            swal("Success", ret_json['msg'], "success");
    });

    $("#formDisableJudge").ajaxForm(function (ret_json) {
        if(ret_json['e'] < 0)
            swal("Error " + ret_json['e'], ret_json['msg'], "error");
        else
            swal("Success", ret_json['msg'], "success");
    });

    $("#formRealname").ajaxForm(function (ret_json) {
        if(ret_json['e'] < 0)
            swal("Error " + ret_json['e'], ret_json['msg'], "error");
        else
            swal("Success", ret_json['msg'], "success");
    });
});
