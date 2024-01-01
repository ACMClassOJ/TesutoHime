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
                var raw_config_str = main_json['Limits'];
                var limit_lst = JSON.parse(main_json['Limits']);
                var limit_lst_length = limit_lst["length"];

                var limit_time_str = "";
                var limit_list_min_time = Math.min(...limit_lst["time"]);
                var limit_list_max_time = Math.max(...limit_lst["time"]);
                if(limit_list_max_time == limit_list_min_time)
                    limit_time_str = "<p> 时间限制： " + limit_list_min_time + " ms</p>";
                else
                    limit_time_str = "<p> 时间限制： " + limit_list_min_time + " ms min, " + limit_list_max_time + " ms max</p>";

                var limit_mem_str = "";
                var limit_list_min_mem = parseInt(Math.min(...limit_lst["mem"]) / 1024 / 1024);
                var limit_list_max_mem = parseInt(Math.max(...limit_lst["mem"]) / 1024 / 1024);
                if(limit_list_max_mem == limit_list_min_mem)
                    limit_mem_str = "<p> 内存空间限制： " + limit_list_min_mem + " MiB</p>";
                else
                    limit_mem_str = "<p> 内存空间限制： " + limit_list_min_mem + " MiB min, " + limit_list_max_mem + " MiB max</p>";
                
                var limit_disk_str = "";
                var limit_disk_flag = 0;
                if("disk" in limit_lst)
                {
                    if(limit_lst["disk"].length == 0)
                        limit_disk_str = "";
                    else
                    {
                        var limit_lst_disk_abs = Array.from(limit_lst["disk"], (n) => Math.abs(n));
                        var limit_list_min_disk = parseInt(Math.min(...limit_lst_disk_abs) / 1024 / 1024);
                        var limit_list_max_disk = parseInt(Math.max(...limit_lst_disk_abs) / 1024 / 1024);
                        if(limit_list_max_disk == 0 && limit_list_min_disk == 0)
                            limit_disk_str = "<p> 磁盘空间限制： 无限制</p>";
                        else if(limit_list_max_disk == limit_list_min_disk)
                        {
                            limit_disk_str = "<p> 磁盘空间限制： " + limit_list_min_disk + " MiB</p>";
                            limit_disk_flag = 1;
                        }
                        else
                        {
                            limit_disk_str = "<p> 磁盘空间限制： " + limit_list_min_disk + " MiB min, " + limit_list_max_disk + " MiB max </p>";
                            limit_disk_flag = 1;
                        }
                    }
                }
                else
                    limit_disk_str = "";

                var limit_file_str = "";
                var limit_file_flag = 0;
                if("file" in limit_lst)
                {
                    if(limit_lst["file"].length == 0)
                        limit_file_str = "";
                    else
                    {
                        var limit_list_min_file = parseInt(Math.min(...limit_lst["file"]));
                        var limit_list_max_file = parseInt(Math.max(...limit_lst["file"]));
                        if(limit_list_max_file == limit_list_min_file == 0)
                            limit_file_str = "<p> 文件数量限制： 无限制</p>";
                        else if(limit_list_max_file == limit_list_min_file)
                        {
                            limit_file_str = "<p> 文件数量限制： " + limit_list_min_file + " 个</p>";
                            limit_file_flag = 1;
                        }
                        else
                        {
                            limit_file_str = "<p> 文件数量限制： " + limit_list_min_file + " 个 min, " + limit_list_max_file + " 个 max </p>";
                            limit_file_flag = 1;
                        }
                    }
                }
                else
                    limit_file_num_str = "";
                var str = limit_time_str + limit_mem_str + limit_disk_str + limit_file_str;
                str += "<details><summary>单个测试点时空限制详情</summary><table>";
                str += "<thead><tr>";
                str += "<th>测试点编号</th> <th>时间限制 (ms)</th> <th>内存空间限制 (MiB)</th>";
                if(limit_disk_flag)
                    str += "<th>磁盘空间限制 (MiB)</th>";
                if(limit_file_flag)
                    str += "<th>文件数量限制</th>";
                str += "</tr></thead>";
                for(var i = 0; i < limit_lst_length; i++)
                {
                    str += "<tr>";
                    str += "<td>" + (i+1) + "</td> <td>" + limit_lst["time"][i] + "</td>  <td>" + parseInt(limit_lst["mem"][i] / 1024 / 1024) + "</td>";
                    if(limit_disk_flag)
                    {
                        str += "<td>";
                        var dd = parseInt(limit_lst["disk"][i] / 1024 / 1024);
                        if(dd == 0)
                            str += "无限制";
                        else if(dd < 0)
                            str += Math.abs(dd) + " （新开空间）";
                        else
                            str += dd;
                        str += "</td>";
                    }
                    if(limit_file_flag)
                        str += "<td>" + parseInt(limit_lst["file"][i]) + "</td>";
                    str += "</tr>";
                }
                str += "</table>";
                str += "<p>raw config data:<p>";
                str += "<code>" + raw_config_str + "</code>";
                str += "</details>";
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
            if (window.Han) {
                Han(document.getElementById('#content')).render()
            }
        },
    });
});
