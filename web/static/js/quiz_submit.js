var id = $("#problem_id").text();
var problem_type = {};
var main_json = {};
$(function(){
    $.ajax({
        type: "POST",
        dataType: "text",
        data: {problem_id: $("#problem_id").text()},
        url: "/OnlineJudge/api/quiz",
        success: function (response_text)
        {
            main_json = JSON.parse(response_text);
            if(main_json["e"] < 0)
                swal("Error " + main_json["e"], main_json["msg"], "error");
            else
            {
                var problems = main_json["problems"];
                var quiz_rendering_node = document.getElementById("quiz_rendering");
                for(var i = 0; i < problems.length; i++)
                {
                    var problem = problems[i];
                    var title = document.createElement("p");
                    title.innerHTML = marked(problem["id"] + ". " + problem["title"]);
                    quiz_rendering_node.appendChild(title);
                    problem_type[i] = problem["type"];
                    if(problem["type"] == "SELECT")
                    {
                        var options = problem["options"];
                        for(var j = 0; j < options.length; j++)
                        {
                            var option = options[j];
                            var option_div = document.createElement("div");
                            option_div_word = '<div class="custom-control custom-radio mb-3">';
                            option_div_word += '<input id="' + problem["id"] + "__" + option["value"] 
                                + '" name="' + problem["id"] + '" class="custom-control-input" value="' 
                                + option["value"] + '" type="radio">';
                            option_div_word += '<label class="custom-control-label" for="' 
                                + problem["id"] + '__' + option["value"] + '">' + marked(option["text"]) + '</label>';
                            option_div.innerHTML = option_div_word;
                            quiz_rendering_node.appendChild(option_div);
                        }
                    }
                    else if(problem["type"] == "FILL")
                    {
                        var fill_div = document.createElement("div");
                        fill_div_word = '<textarea class="form-control" rows="1" name = "' + problem['id'] + '"></textarea>';
                        fill_div.innerHTML = fill_div_word;
                        quiz_rendering_node.appendChild(fill_div);
                    }
                }
                renderMathInElement(document.body,
                    {
                        delimiters: [
                            {left: "$$", right: "$$", display: true},
                            {left: "$", right: "$", display: false}
                        ]
                    }
                );
                hljs.initHighlighting();
            }
        },
    });
});

$(function() {
    $("input").keyup(function(){
        alert("checkValue");
    });
});

$(function() {
    var submit_options = {
        beforeSubmit: function() {
            $("input").attr("disabled", "disabled");
        },
        success: function(response_text) {
            if (response_text == "0") 
            {
                swal("Success", "提交成功", "success");
                setTimeout(function() {
                    window.location.replace('/OnlineJudge/status');
                }, 500);
            }
            else
                swal("Oops", "提交失败，网络故障！", "error");
        }
    };
    $("#quiz_submit_form").ajaxForm(submit_options);
});