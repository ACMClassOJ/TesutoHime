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
                alert(JSON.stringify(ret));
            }
        });
    });

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
        $("#iptDescription").val("");
        $("#iptInput").val("");
        $("#iptOutput").val("");
        $("#iptExampleInput").val("");
        $("#iptExampleOutput").val("");
        $("#iptDataRange").val("");
        $("#iptProblemType").selectpicker("val", "0");
        $.ajax({
            type: "POST",
            dataType: "text",
            data: {problem_id: $("#iptProblemID").val()},
            url: "/OnlineJudge/api/get_detail",
            success: function (response_text)
            {
                if(response_text == "{}")
                {
                    $("#btnAddProblem").removeAttr("disabled");
                    $("#iptProblemStatusBadge").removeClass();
                    $("#iptProblemStatusBadge").addClass("badge badge-secondary");
                    $("#iptProblemStatusBadge").text("空");
                }
                else
                {
                    $("#btnModifyProblem").removeAttr("disabled");
                    $("#btnRemoveProblem").removeAttr("disabled");
                    $("#iptProblemStatusBadge").removeClass();
                    $("#iptProblemStatusBadge").addClass("badge badge-success");
                    $("#iptProblemStatusBadge").text("已存在");
                    var main_json = JSON.parse(response_text);
                    $("#iptTitle").val(main_json['Title']);
                    $("#iptReleaseTime").val(formatDate(main_json['Release_Time'] * 1000));
                    $("#iptProblemType").val(main_json['Problem_Type']);
                    $("#iptDescription").val(main_json['Description']);
                    $("#iptInput").val(main_json['Input']);
                    $("#iptOutput").val(main_json['Output']);
                    $("#iptExampleInput").val(main_json['Example_Input']);
                    $("#iptExampleOutput").val(main_json['Example_Output']);
                    $("#iptDataRange").val(main_json['Data_Range']);
                    $("#iptProblemType").selectpicker("val", main_json['Problem_Type']);
                }
            }
        });
        $("#divProblemHidden").slideDown(500);
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
                alert(JSON.stringify(ret));
                document.getElementById('btnGetProblemDetails').click();
            }
        });
    });

    $("#divContestHidden").hide();
    $("#divContestProblemListHidden").hide();
    $("#divContestUserListHidden").hide();
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
                alert(ret.responseText);
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
                    alert(ret.responseText);
                }
            });
        });
    });

    $("#formDataZipUpload").submit(function (e) {
        e.preventDefault();
        e.stopPropagation();
        let data = new FormData(this);
        $.ajax({
            url: "/OnlineJudge/admin/data",
            type: "POST",
            processData: false,
            contentType: false,
            data: data,
            dataType: "json",
            complete: function (ret) {
                alert(ret.responseText);
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

    $("#formRejudge").ajaxForm(function (response_text) {
        alert(response_text);
    });
});