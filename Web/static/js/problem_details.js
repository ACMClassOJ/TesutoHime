$(function(){
    $.ajax({
        type: "POST",
        dataType: "text",
        data: {problem_id: $("#problem_id").text()},
        url: "/OnlineJudge/api/get_detail",
        success: function (response_text)
        {
            var main_json = JSON.parse(response_text);
            if (main_json['Description'] == "None") $("#problem_details_description_header").html("");
            else $("#problem_details_description").html(marked(main_json['Description']));
            if (main_json['Input'] == "None") $("#problem_details_input_header").html("");
            else $("#problem_details_input").html(marked(main_json['Input']));
            if (main_json['Output'] == "None") $("#problem_details_output_header").html("");
            else $("#problem_details_output").html(marked(main_json['Output']));
            if (main_json['Example_Input'] == "None") $("#problem_details_example_input_header").html("");
            else $("#problem_details_example_input").html(marked(main_json['Example_Input']));
            if (main_json['Example_Output'] == "None") $("#problem_details_example_output_header").html("");
            else $("#problem_details_example_output").html(marked(main_json['Example_Output']));
            if (main_json['Data_Range'] == "None") $("#problem_details_data_range_header").html("");
            else $("#problem_details_data_range").html(marked(main_json['Data_Range']));
            if (main_json['Limits'] == "None") $("#problem_details_time_mem_disk_limit_header").html("");
            else
            {
                var str = "";
                var limit_lst = JSON.parse(main_json['Limits']);
                var limit_lst_length = limit_lst["length"];
                var limit_list_min_time = Math.min(...limit_lst["time"]);
                var limit_list_max_time = Math.max(...limit_lst["time"]);
                if(limit_list_max_time == limit_list_min_time)
                    str += "<p> 时间限制： " + limit_list_min_time + " ms</p>";
                else
                    str += "<p> 时间限制： " + limit_list_min_time + " ms min, " + limit_list_max_time + " ms max </p>";

                var limit_list_min_mem = parseInt(Math.min(...limit_lst["mem"]) / 1024 / 1024);
                var limit_list_max_mem = parseInt(Math.max(...limit_lst["mem"]) / 1024 / 1024);
                if(limit_list_max_mem == limit_list_min_mem)
                    str += "<p> 空间限制： " + limit_list_min_mem + " MiB</p>";
                else
                    str += "<p> 空间限制： " + limit_list_min_mem + " MiB min, " + limit_list_max_mem + " MiB max </p>";
                
                // if("disk" in limit_lst)
                // {
                //     str += "<p> 空间限制： " + limit_list_min_mem + " MB min, " + limit_list_max_mem + " MB max </p>";
                // }
                str += "<details><summary>单个测试点时空限制详情</summary><table>";
                str += "<thead><tr> <th>测试点编号</th> <th>时间限制 (ms)</th> <th>空间限制 (MiB)</th> </tr></thead>";
                for(var i = 0; i < limit_lst_length; i++)
                    str += "<tr> <td>" + (i+1) + "</td> <td>" + limit_lst["time"][i] + "</td>  <td>" + parseInt(limit_lst["mem"][i] / 1024 / 1024) + "</td> </tr>";
                str += "</table></details>";
                $("#problem_details_time_mem_disk_limit").html(str);
            }
            renderMathInElement(document.body,
                {
                    delimiters: [
                        {left: "$$", right: "$$", display: true},
                        {left: "$", right: "$", display: false},
                        {left: "\\(", right: "\\)", display: false}
                    ]
                }
            );
            hljs.initHighlighting();
            $("pre").wrap('<div style="position: relative;"></div>');
            $("pre").each(function(index, element){
                $(this).find("code").eq(0).attr('id', 'code_highlighted_' + index);
                var copy_button = $('<button class="btn btn-primary btn-sm" style="position: absolute; top: 0; right: 0;">复制</button>');
                copy_button.attr('id', 'copy_button_' + index);
                copy_button.attr('data-clipboard-target', '#code_highlighted_' + index);
                copy_button.appendTo($(this));
                new ClipboardJS(document.getElementById('copy_button_' + index));
            });
        },
    });
});
