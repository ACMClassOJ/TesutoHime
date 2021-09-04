// var main_json = {
//     "problems": [
//         {
//             "id": "1",
//             "type": "SELECT",
//             "title": "在一个具有n个顶点的有向图中，若所有顶点的出度数之和为s，则所有顶点的度数之和为(　　)。",
//             "answer": "3",
//             "options": [
//                 {
//                     "value": "0",
//                     "text": "s"
//                 },
//                 {
//                     "value": "1",
//                     "text": "s-1"
//                 },
//                 {
//                     "value": "2",
//                     "text": "s+1"
//                 },
//                 {
//                     "value": "3",
//                     "text": "2s"
//                 },
//             ]
//         },
//         {
//             "id": "3.1",
//             "type": "SELECT",
//             "title": "在一个具有n个顶点的无向完全图中，所含的边数为(　　)。",
//             "answer": "2",
//             "options": [
//                 {
//                     "value": "0",
//                     "text": "n"
//                 },
//                 {
//                     "value": "1",
//                     "text": "n(n-1)"
//                 },
//                 {
//                     "value": "2",
//                     "text": "n(n-1)/2"
//                 },
//                 {
//                     "value": "3",
//                     "text": "n(n+1)/2"
//                 },
//             ]
//         },
//         {
//             "id": "2.3",
//             "type": "FILL",
//             "title": "一棵4阶B树中，每个节点最多有（）个子树，（）个关键字；最少有 （）个子树，（）个关键字 (四个数字用空格隔开)",
//             "answer": ["4 3 2 1"],
//         }
//     ]
// }

// function escapeHTML(html) {
//     return html.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
// }

// function create_quiz_main_form(main_json) {
//     alert(Object.keys(main_json["problems"]).length);
//     main_array = main_json["problems"];
//     var main_html = '';
//     var form_start = '<form action="/OnlineJudge/submit/" method="post">';
//     var hidden_problem_id = '<input type="hidden" name="problem_id" value="{{ Problem_ID }}">'
//     main_html += form_start + hidden_problem_id;
//     for (var i = 0; i < main_array.length; i++) {
//         var question_line = main_array[i]["id"] + ". " + main_array[i]["title"] + "<br>";
//         var question_form_content = "";
//         if (main_array[i]["type"] == "SELECT")
//             for (var j = 0; j < main_array[i]["options"].length; j++)
//                 question_form_content += '<input type="radio" name = "' + main_array[i]["id"] + '" value=' + main_array[i]["options"][j]["value"] + '>' + main_array[i]["options"][j]["text"];
//         else if (main_array[i]["type"] == "FILL")
//             question_form_content += '<input type="text" name = "' + main_array[i]["id"] + '"';
//         main_html += question_line + question_form_content + "<br>";
//     }
//     main_html += "</form>";
//     document.write(main_html);
// }

// // $(function () {
//     create_quiz_main_form(main_json);
// // });