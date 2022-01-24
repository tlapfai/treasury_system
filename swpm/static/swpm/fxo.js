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
  let form_data = new FormData(myForm);

  var form_alert = document.querySelector("#form-alert");
  form_alert.innerHTML = ``;
  document
    .querySelectorAll(`input, select`)
    .forEach((e) => e.classList.remove("is-invalid"));

  axios({
    method: "post",
    url: "/swpm/trade/fxo/price", // starting with slash will use the root of the site
    data: form_data,
    headers: { "Content-Type": "multipart/form-data" },
  })
    .then((response) => {
      //$("input#spot").val(response.data.spot);
      for (var key in response.data.result) {
        document.querySelector("#val-" + key).textContent = numberWithCommas(
          response.data.result[key]
        );
      }
      for (var key in response.data.parameters) {
        $("input#" + key).val(response.data.parameters[key]); //Math.round(response.data.parameters[key] * 1e8) / 1e8
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

$("#id_ccy_pair").change(load_fxo_mkt);
$("#id_maturity_date").change(load_fxo_mkt);
$("#id_strike_price").change(load_fxo_mkt);

function load_fxo_mkt() {
  const as_of = $("#id_as_of").val();
  const ccy_pair = $("#id_ccy_pair").val();
  const maturity_date = $("#id_maturity_date").val();
  const strike_price = $("#id_strike_price").val();
  if (
    as_of &&
    ccy_pair &&
    maturity_date &&
    strike_price &&
    maturity_date > as_of
  ) {
    axios
      .post("/swpm/load_fxo_mkt", {
        as_of: as_of,
        ccy_pair: ccy_pair,
        maturity_date: maturity_date,
        strike_price: strike_price,
      })
      .then((response) => {
        $("input#spot").val(response.data.spot);
        $("input#fwd").val(response.data.fwd);
        $("input#vol").val(response.data.vol);
      });
  }
}

document.addEventListener("DOMContentLoaded", function () {
  $(".ccypair legend").click(() => {
    $(".ccypair table").toggle();
    $(".ccypair button").toggle();
    axios();
  });

  $("#id_notional_1").change(() => {
    if ($.isNumeric($("#id_notional_2").val())) {
      $("#id_strike_price").val(
        ($("#id_notional_2").val() / $("#id_notional_1").val()).toFixed(10)
      );
    }
  });
  $("#id_notional_2").change(() => {
    if ($.isNumeric($("#id_notional_1").val())) {
      $("#id_strike_price").val(
        ($("#id_notional_2").val() / $("#id_notional_1").val()).toFixed(10)
      );
    }
  });
  $("#id_strike_price").change(() => {
    if ($.isNumeric($("#id_notional_1").val())) {
      $("#id_notional_2").val(
        ($("#id_notional_1").val() * $("#id_strike_price").val()).toFixed(2)
      );
    } else if ($.isNumeric($("#id_notional_2").val())) {
      $("#id_notional_1").val(
        ($("#id_notional_2").val() / $("#id_strike_price").val()).toFixed(2)
      );
    }
  });

  $("#btn-std-fill").click(() => {
    const effective_date = new Date();
    effective_date.setDate(effective_date.getDate() + 2);
    var oneyear = new Date();
    oneyear.setFullYear(oneyear.getFullYear() + 1);
    oneyear.setDate(oneyear.getDate() + 2);
    document.getElementById("id_book").value = "FXO1";
    document.getElementById("id_counterparty").value = "HSBC";
    document.querySelectorAll('[id*="effective_date"]').forEach((d) => {
      d.value = effective_date.toISOString().split("T")[0];
    });
    document.querySelectorAll('[id*="maturity_date"]').forEach((d) => {
      d.value = oneyear.toISOString().split("T")[0];
    });
    document.querySelectorAll('[id*="notional"]').forEach((d) => {
      d.value = "1000000";
    });
    document.querySelectorAll("#id_form-0-fixed_rate").forEach((d) => {
      d.value = "0.03";
    });
    document.querySelectorAll('[id*="freq"]').forEach((d) => {
      d.value = "3M";
    });
    document.querySelectorAll("#id_form-0-reset_freq").forEach((d) => {
      d.value = "";
    });
    document.querySelectorAll('[id*="day_counter"]').forEach((d) => {
      d.value = "Actual360";
    });
    document.querySelectorAll('[id*="calendar"]').forEach((d) => {
      d.value = "UnitedStates";
    });
    document.querySelector("#id_ccy_pair").value = "EUR/USD";
    document.querySelectorAll('[id*="index"]')[0].value = "";
    document.querySelectorAll('[id*="index"]')[1].value = "USD LIBOR 3M";
    document.querySelectorAll('[id*="pay_rec"]')[0].value = "1";
    document.querySelectorAll('[id*="pay_rec"]')[1].value = "-1";
    document.querySelectorAll('[id*="ccy"]')[0].value = "USD";
    document.querySelectorAll('[id*="ccy"]')[1].value = "USD";
    document.querySelectorAll('[id*="cp"]')[0].value = "C";
    document.querySelectorAll('[id*="buy_sell"]')[0].value = "B";
    document.querySelectorAll('[id*="type"]')[0].value = "EUR";
    document.querySelectorAll("id_ccy_pair").forEach((d) => {
      d.value = "EUR/USD";
    });
  });

  var triggerTabList = [].slice.call(document.querySelectorAll("#ticketTab a"));
  triggerTabList.forEach(function (triggerEl) {
    var tabTrigger = new bootstrap.Tab(triggerEl);

    triggerEl.addEventListener("click", function (event) {
      event.preventDefault();
      tabTrigger.show();
    });
  });

  // https://studygyaan.com/django/render-html-as-you-type-with-django-and-ajax
  // function updateTextView(_obj){
  // var num = getNumber(_obj.val());
  // if(num==0){
  // _obj.val('');
  // }else{
  // _obj.val(num.toLocaleString());
  // }
  // }
  // function getNumber(_str){
  // var arr = _str.split('');
  // var out = new Array();
  // for(var cnt=0;cnt<arr.length;cnt++){
  // if(isNaN(arr[cnt])==false){
  // out.push(arr[cnt]);
  // }
  // }
  // return Number(out.join(''));
  // }
  // $(document).ready(function(){
  // $('input[type=number]').on('keyup',function(){
  // updateTextView($(this));
  // });
  // });
});
