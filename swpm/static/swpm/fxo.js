function commaNum(x) {
  if (Math.abs(x) < 1.0) {
    return x;
  }
  return x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

$("#id_as_of").val(new Date().toISOString().split("T")[0]);

// $("#btn-scn").click(function (event) {
//   event.preventDefault();
//   let fd = $(".trade-form")[0];
//   let form_data = new FormData(fd);
//   let axios_cfg = { headers: { "X-CSRFToken": $.cookie("csrftoken") } };
//   axios.post("/swpm/trade/fxo/scn", form_data, axios_cfg).then((response) => {
//     let w = window.open("about:blank", "scn-window");
//     w.document.write(response);
//   });
// });

$("#btn-price").click((event) => {
  event.preventDefault();
  load_fxo_mkt();
  let myForm = $(".trade-form")[0];
  let form_data = new FormData(myForm);
  var form_alert = $("#form-alert");
  form_alert.html("");
  $("input, select").removeClass("is-invalid");
  $('[id^="val-"]').text("");

  axios({
    method: "post",
    url: "/swpm/trade/fxo/price", // starting with slash will use the root of the site
    data: form_data,
    headers: { "Content-Type": "multipart/form-data" },
  })
    .then((response) => {
      $.each(response.data.result, function (key, value) {
        $(`#val-${key}`).text(commaNum(value.toFixed(2)));
      });
      $("#val-alert").text(response.data.valuation_message);
    })
    .catch((error) => {
      console.log(error);
      var e = error.response.data.errors;
      for (var y in e) {
        form_alert.append(
          `<div class="alert alert-danger" role="alert">${e[y]}</div>`
        );
        $(`[name="${y}"]`).addClass("is-invalid");
      }
      $('[id^="val-"]').text("");
    });
});

$("#btn-mkt").click(function (event) {
  event.preventDefault();
  let myForm = document.querySelector(".trade-form");
  let fd = new FormData(myForm);
  axios({
    method: "post",
    url: "/swpm/fx_volatility_table", // starting from slash to access the root of the site
    data: fd,
    headers: { "Content-Type": "multipart/form-data" },
  }).then((response) => {
    $("#mktdata").html(response.data.result);
  });
});

$("input#id_as_of").focusout(load_fxo_mkt);
$("#id_ccy_pair").change(load_fxo_mkt);
$("#id_maturity_date").focusout(load_fxo_mkt);
$("#id_strike_price").change(load_fxo_mkt);

function fillInputHandle() {
  $(this).val($(this).data("value"));
}

$("#id_tenor").focusout(function () {
  let regex1 = /^(\d+[DMYdmy])+$/;
  let regex2 = /^(\d+[Ww])+$/;
  tenor_ = $("#id_tenor").val().trim();
  if (regex1.test(tenor_) || regex2.test(tenor_)) {
    let axios_cfg = { headers: { "X-CSRFToken": $.cookie("csrftoken") } };
    axios
      .post(
        "/swpm/tenor2date",
        {
          ccy_pair: $("#id_ccy_pair").val(),
          trade_date: $("#id_trade_date").val(),
          tenor: tenor_,
        },
        axios_cfg
      )
      .then((response) => {
        $("#id_maturity_date").val(response.data.date);
        $("#id_maturity_date").css("color", "blue");
        $("#id_tenor").val(response.data.tenor);
        load_fxo_mkt();
      });
  } else {
    $("#id_tenor").val("");
  }
});

function load_fxo_mkt() {
  $('[id^="para-"] input').text("");
  var form_alert = document.querySelector("#form-alert");
  form_alert.innerHTML = "";
  const as_of = $("input#id_as_of").val();
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
    let axios_cfg = { headers: { "X-CSRFToken": $.cookie("csrftoken") } };
    axios
      .post(
        "/swpm/load_fxo_mkt",
        {
          as_of: as_of,
          ccy_pair: ccy_pair,
          maturity_date: maturity_date,
          strike_price: strike_price,
        },
        axios_cfg
      )
      .then((response) => {
        let valueInPercentage = ["vol", "r", "q"];
        $.each(response.data, function (key, value) {
          let scale = 1.0;
          if (valueInPercentage.includes(key)) scale = 100;
          $(`table.parameters input#${key}`).data("value", value * scale);
          $(`table.parameters input#${key}`).data("byUser", false);
          $(`table.parameters input#${key}`).val((value * scale).toFixed(6));
          $(`table.parameters input#${key}`).focus(fillInputHandle);
        });
        $(`table.parameters input`).change(function () {
          $(this).css("background-color", "lightBlue");
          $(this).data("byUser", true);
        });
      })
      .catch((error) => {
        var e = error.response.data.errors;
        for (var y in e) {
          var li = document.createElement("div");
          li.innerHTML = `<div class="alert alert-danger" role="alert">${e[y]}</div>`;
          form_alert.appendChild(li);
          document.querySelector(`[name="${y}"]`).classList.add("is-invalid");
        }
      });
  }
}

$("#id_maturity_date").change(function () {
  $("#id_maturity_date").css("color", "");
  $("#id_tenor").val("");
});

document.addEventListener("DOMContentLoaded", function () {
  $('[data-bs-toggle="tooltip"]').tooltip();
  // prettier-ignore
  $("#id_notional_1").change(() => {
    if ($.isNumeric($("#id_notional_2").val())) {
      $("#id_strike_price").val(($("#id_notional_2").val() / $("#id_notional_1").val()).toFixed(10));
    }
  });
  // prettier-ignore
  $("#id_notional_2").change(() => {
    if ($.isNumeric($("#id_notional_1").val())) {
      $("#id_strike_price").val(($("#id_notional_2").val() / $("#id_notional_1").val()).toFixed(10));
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

  $("#btn-std-fill").click(function (event) {
    event.preventDefault();
    $("input#id_as_of").val("2021-11-18");
    $("input#id_trade_date").val("2021-11-18");
    const effective_date = new Date();
    effective_date.setDate(effective_date.getDate() + 2);
    var oneyear = new Date();
    oneyear.setFullYear(oneyear.getFullYear() + 1);
    oneyear.setDate(oneyear.getDate() + 2);
    $("#id_book").val("FXO1");
    $("#id_counterparty").val("HSBC");
    $('[id*="effective_date"]').val(effective_date.toISOString().split("T")[0]);
    $('[id*="maturity_date"]').val(oneyear.toISOString().split("T")[0]);
    $('[id*="notional_1"]').val("1000000.00");
    $('[id*="notional_2"]').val("1090000.00");
    $("#id_form-0-fixed_rate").val(0.03);
    $('[id*="freq"]').val("3M");
    $("#id_form-0-reset_freq").val("");
    $('[id*="day_counter"]').val("Actual360");
    $('[id*="calendar"]').val("UnitedStates");
    $("#id_exercise_type").val("EUR");
    $("#id_payoff_type").val("PLA");
    $("#id_ccy_pair").val("EUR/USD");
    $("#id_cp").val("C");
    $("#id_strike_price").val(1.09);
    $("#id_cashflow-ccy").val("USD");
    $("#id_cashflow-amount").val(10000);
    $("#id_cashflow-value_date").val("2021-11-22");
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
