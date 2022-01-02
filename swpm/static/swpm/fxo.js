function numberWithCommas(x) {
  if (Math.abs(x) < 1.0) {
    return x;
  }
  return x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

document.querySelector(".as_of").value = new Date().toISOString().split("T")[0];

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
      for (var key in response.data.parameters) {
        document.querySelector("#val-" + key).textContent =
          Math.round(response.data.parameters[key] * 1e8) / 1e8;
      }
      document.querySelector("#val-alert").textContent =
        response.data.valuation_message;
    })
    .catch((error) => {
      //console.log(error.response.data.errors);
      console.log(error);
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
    });
});

document.getElementById("btn-mkt").addEventListener("click", (event) => {
  event.preventDefault();
  let myForm = document.querySelector(".trade-form");
  let fd = new FormData(myForm);
  axios({
    method: "post",
    url: "/swpm/fx_volatility_table", // starting from slash to access the root of the site
    data: fd,
    headers: { "Content-Type": "multipart/form-data" },
  }).then((response) => {
    console.log(response);
    document.getElementById("mktdata").innerHTML = response.data.result;
  });
});
