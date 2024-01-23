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
            data[e.name] = e.value;
    });
    return data;
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
            window.location.replace('/OnlineJudge/problemset/' + $("#iptContestID").val());
    });

    $("#btnGetContestAutoIncreseID").click(function(){
        $.ajax({
            type: "GET",
            dataType: "text",
            url: "/OnlineJudge/api/contest-id-autoinc",
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
        $("#iptStartTime").val(new Date().toISOString().replace(/:\d+\..+$|Z/, ''));
        $("#iptEndTime").val(new Date(2030, 0, 1, 0, 0, 0, 0).toISOString().replace(/\..+$|Z/, ''));
        $("#iptContestType").selectpicker("val", "0");
        const contestId = $("#iptContestID").val()
        $.ajax({
            dataType: "text",
            url: `/OnlineJudge/api/contest/${contestId}`,
            success: function (response_text)
            {
                if(response_text == "{}")
                {
                    $("#btnCreateContest").removeAttr("disabled");
                    $("#iptContestStatusBadge").removeClass();
                    $("#iptContestStatusBadge").addClass("badge badge-secondary");
                    $("#iptContestStatusBadge").text("空");
                    $('#iptRanked').prop('checked', true)
                    $('#iptRankPenalty').prop('checked', false)
                    $('#iptRankPartialScore').prop('checked', true)
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
                    $("#iptStartTime").val(main_json['Start_Time']);
                    $("#iptEndTime").val(main_json['End_Time']);
                    $("#iptContestType").selectpicker("val", main_json['Type']);
                    $('#iptRanked').prop('checked', main_json.Ranked)
                    $('#iptRankPenalty').prop('checked', main_json.Rank_Penalty)
                    $('#iptRankPartialScore').prop('checked', main_json.Rank_Partial_Score)
                }
            }
        });
        $("#divContestHidden").slideDown(500);
    });

    $('#iptContestType').change(() => {
        const switches = [
            [true, false, true],
            [false, false, false],
            [true, false, true],
        ][$('#iptContestType').val()]
        ; ['#iptRanked', '#iptRankPenalty', '#iptRankPartialScore'].forEach((x, i) => {
            $(x).prop('checked', switches[i])
        })
    })

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
        for (const key of [ 'ranked', 'rank_penalty', 'rank_partial_score' ]) {
            data[key] = data[key] === 'on'
        }
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
        $(btn).attr('onclick', 'setTimeout(() => this.disabled = true)');
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
