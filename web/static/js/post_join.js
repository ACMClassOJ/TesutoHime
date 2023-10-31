for (const el of document.querySelectorAll('[data-contest-id]')) {
    el.addEventListener('click', e => {
        e.preventDefault()
        $.ajax({
            type: "POST",
            dataType: "text",
            data: {contest_id: Number(el.getAttribute('data-contest-id'))},
            url: "/OnlineJudge/api/join",
            beforeSend: function () {
                el.disabled = true
            },
            success: function () {
                location.reload()
            },
        })
    })
}