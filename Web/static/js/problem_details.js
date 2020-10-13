$(function(){
	$.ajax({
        type: "POST",
        dataType: "text",
        data: {problem_id: $("#problem_id").text()},
        url: "/api/get_detail",
        success: function (response_text)
        {
        	var main_json = JSON.parse(response_text);
			$("#problem_details_description").html(marked(main_json['Description']));
			$("#problem_details_input").html(marked(main_json['Input']));
			$("#problem_details_output").html(marked(main_json['Output']));
			$("#problem_details_example_input").html(marked(main_json['Example_Input']));
			$("#problem_details_example_output").html(marked(main_json['Example_Output']));
			$("#problem_details_data_range").html(marked(main_json['Data_Range']));
			renderMathInElement(document.body,
				{
					delimiters: [
						{left: "$$", right: "$$", display: true},
						{left: "$", right: "$", display: false}
					]
				}
			);
		},
	});
});