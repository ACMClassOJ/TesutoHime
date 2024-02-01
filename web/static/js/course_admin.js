document.querySelector('#form-jump-problem').addEventListener('submit', e => {
  e.preventDefault()
  const id = document.getElementById('problem-id').value
  if (id === '' || isNaN(id)) return
  location = `/OnlineJudge/problem/${id}/admin`
})
