function numberWithCommas(x) {
  if (Math.abs(x) < 1.0) {
    return x;
  }
  return x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

document.getElementById("btn-price").addEventListener("click", (event) => {
  event.preventDefault();
  let myForm = document.querySelector(".trade-form");
  let fd = new FormData(myForm);

  var form_alert = document.querySelector("#form-alert");
  form_alert.innerHTML = ``;
  document
    .querySelectorAll(`input, select`)
    .forEach((e) => e.classList.remove("is-invalid"));

  axios({
    method: "post",
    url: "price",
    data: fd,
    headers: { "Content-Type": "multipart/form-data" },
  })
    .then((response) => {
      for (var key in response.data.result) {
        document.querySelector("#val-" + key).textContent = numberWithCommas(
          response.data.result[key]
        );
      }
      document.querySelector("#val-alert").textContent =
        response.data.valuation_message;
    })
    .catch((error) => {
      console.log(error.response.data.errors);
      var e = error.response.data.errors;
      for (var y in e) {
        var li = document.createElement("div");
        li.innerHTML = `<div class="alert alert-danger" role="alert">${y}: ${e[y]}</div>`;
        form_alert.appendChild(li);
        document.querySelector(`[name="${y}"]`).classList.add("is-invalid");
      }
      document
        .querySelectorAll('[id^="val-"]')
        .forEach((e) => (e.textContent = ""));
      console.error("Valuation error: ", error);
    })
    .then(alert(response));
});
