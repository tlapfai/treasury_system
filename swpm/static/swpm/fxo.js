document.getElementById("btn-price").addEventListener("click", (event) => {
  event.preventDefault();
  console.log(event);
  alert("hi");
  let myForm = document.getElementsByClassName("trade-form");
  alert("hi");
  let fd = new FormData(myForm);

  axios({
    method: "post",
    url: "pricing",
    data: fd,
    headers: { "Content-Type": "multipart/form-data" },
  })
    .then((response) => {
      setForm(response.data.form);
    })
    .catch(() => {
      console.log(Error("cannot fetch form"));
    });
});
