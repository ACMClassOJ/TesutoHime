$(function(){
    $("input").on('keypress', function(e){
        var key = window.event ? e.keyCode : e.which;
        if(key.toString() == "13")
            return false;
    });
    $('#problem-id').off('keypress')
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

function formatDate(date) {
    var date = new Date(date);
    var YY = date.getFullYear() + '-';
    var MM = (date.getMonth() + 1 < 10 ? '0' + (date.getMonth() + 1) : date.getMonth() + 1) + '-';
    var DD = (date.getDate() < 10 ? '0' + (date.getDate()) : date.getDate());
    var hh = (date.getHours() < 10 ? '0' + date.getHours() : date.getHours()) + ':';
    var mm = (date.getMinutes() < 10 ? '0' + date.getMinutes() : date.getMinutes());
    return YY + MM + DD +"T"+ hh + mm;
}

function getUrlArg(arg) {
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
    contest_id = getUrlArg('contest_id');

    if (contest_id != false) {
        document.getElementById('contest_tab_btn').click();
        $("#iptContestID").val(contest_id);
        document.getElementById('btnGetContestDetails').click();
    }
}

let op;
$(function () {
    $('#form-jump-problem').submit(e => {
        e.preventDefault()
        const id = $('#problem-id').val()
        if (id === '' || isNaN(id)) return
        location = `/OnlineJudge/problem/${id}/admin`
    })

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

    $("#divContestHidden").hide();
    $("#divContestProblemListHidden").hide();
    $("#divContestUserListHidden").hide();

    $("#btnGoToContestPage").click(function(){
        if($("#iptContestID").val() != "")
            window.location.replace('/OnlineJudge/problem-group/' + $("#iptContestID").val());
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


    var ajaxForms = [ '#formRejudge', '#formRejudge2', '#formDisableJudge', '#formDisableJudge2', '#formRealname', '#form-abort', '#form-abort-2' ]
    var ajaxButtons = [ '#btnRejudge', '#btnRejudge2', '#btnDisableJudge', '#btnDisableJudge2', '#btnAddRealname', '#btnAbortJudge', '#btnAbortJudge2' ]
    // disable when submit
    for (btn of ajaxButtons) {
        $(btn).attr('onclick', 'this.disabled = true;');
    }
    for (form of ajaxForms) {
        $(form).ajaxForm(function (ret_json) {
            if(ret_json['e'] < 0)
                swal("Error " + ret_json['e'], ret_json['msg'], "error");
            else
                swal("Success", ret_json['msg'], "success");
            // enable when receive
            for (btn of ajaxButtons) {
                $(btn).removeAttr('disabled');
            }
        });
    }
});
