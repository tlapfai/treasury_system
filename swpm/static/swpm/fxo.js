document.getElementById("btn-price").addEventListener("click", (event) => {
  event.preventDefault();
  let myForm = document.querySelector(".trade-form");
  let fd = new FormData(myForm);

  axios({
    method: "post",
    url: "price",
    data: fd,
    headers: { "Content-Type": "multipart/form-data" },
  })
    .then((response) => {
      console.log(response.data);
      for (var key in response.data.result) {
        document.querySelector("#val-" + key).innerHTML =
          response.data.result[key];
      }
    })
    .catch((e) => {
      console.error(e);
    });
});
