const axios_cfg = { headers: { "X-CSRFToken": $.cookie("csrftoken") } };

function commaNum(x) {
  if (Math.abs(x) < 1.0) {
    return x;
  }
  return x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

$(document).ready(function () {
  $("#id_as_of").val(new Date().toISOString().split("T")[0]);

  async function price_swap() {
    let form_data = new FormData($(".trade-form")[0]); // use [0] to convert jquery obj to DOM
    $("#form-alert").html("");
    $("#form-alert").addClass("invisible");
    $("input, select").removeClass("is-invalid");
    return await axios({
      method: "post",
      url: "/api/trade/swap/price", // starting with slash will use the root of the site
      data: form_data,
      headers: { "Content-Type": "multipart/form-data" },
    });
  }

  function updateValuationTable(event) {
    event.preventDefault();
    //updateMktTable();
    price_swap()
      .then((response) => {
        valuationTable.updateData(response.data.result.values);
        valuationTable.updateSettings({
          colHeaders: response.data.result.headers,
        });
      })
      .catch((error) => {
        var e = error.response.data.errors;
        $("#form-alert").removeClass("invisible");
        for (var y in e) {
          form_alert.append(
            // append is add a element at the end inside the tag
            `<div class="alert alert-danger" role="alert">${e[y]}</div>`
          );
          $(`[name="${y}"]`).addClass("is-invalid");
        }
      });
  }

  $("#btn-price").click(updateValuationTable);

  $("#btn-std-fill").click(function (event) {
    event.preventDefault();
    $("input#id_as_of, input#id_trade_date").val("2021-11-18");
    const effective_date = new Date();
    effective_date.setDate(effective_date.getDate() + 2);
    var oneyear = new Date();
    oneyear.setFullYear(oneyear.getFullYear() + 1);
    oneyear.setDate(oneyear.getDate() + 2);
    $("#id_book").val("FXO1");
    $("#id_counterparty").val("HSBC");
    $('[id*="start_date"]').val(effective_date.toISOString().split("T")[0]);
    $('[id*="end_date"]').val(oneyear.toISOString().split("T")[0]);
    $('[id*="notional"]').val("1000000.00");
    $("#id_form-0-fixed_rate").val(0.03);
    $('[id*="freq"]').val("3M");
    $("#id_form-0-reset_freq").val("");
    $('[id*="day_counter"]').val("Actual360");
    $('[id*="calendar"]').val("UnitedStates");
    $("#id_exercise_type").val("EUR");
    $("[id*='0-pay_rec']").val(1);
    $("[id*='1-pay_rec']").val(-1);
    $("[id*='ccy']").val("USD");
    $("#id_strike_price").val(1.09);
    $("#id_cashflow-ccy").val("USD");
    $("#id_cashflow-amount").val(10000);
    $("#id_cashflow-value_date").val("2021-11-22");
  });
});
