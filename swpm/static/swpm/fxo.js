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

$("#btn-mkt").click(function (event) {
  event.preventDefault();
  const date = $("#id_as_of").val();
  const ccy_pair = $("#id_ccy_pair").val().replace("/", "");
  window.open("/mkt/fxv/" + ccy_pair + "/" + date);
});

function fillInputHandle() {
  $(this).val($(this).data("value"));
}

// prettier-ignore
$("#id_tenor").focusout(function () {
  let regex1 = /^(\d+[DMYdmy])+$/;
  let regex2 = /^(\d+[Ww])+$/;
  tenor_ = $("#id_tenor").val().trim();
  if (regex1.test(tenor_) || regex2.test(tenor_)) {
    let axios_cfg = { headers: { "X-CSRFToken": $.cookie("csrftoken") } };
    axios
      .post("/api/tenor2date", {
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
        updateMktTable();
      });
  } else {
    $("#id_tenor").val("");
  }
});

$("#id_maturity_date").change(function () {
  $("#id_maturity_date").css("color", "");
  $("#id_tenor").val("");
});

$(document).ready(function () {
  $('[data-bs-toggle="tooltip"]').tooltip();

  const n1 = $("#id_notional_1");
  const n2 = $("#id_notional_2");
  const kk = $("#id_strike_price");

  n1.change(() => {
    $.isNumeric(n2.val()) && kk.val((n2.val() / n1.val()).toFixed(10));
  });

  n2.change(() => {
    $.isNumeric(n1.val()) && kk.val((n2.val() / n1.val()).toFixed(10));
  });

  kk.change(() => {
    if ($.isNumeric(n1.val())) {
      n2.val((n1.val() * kk.val()).toFixed(2));
    } else if ($.isNumeric(n2.val())) {
      n1.val((n2.val() / kk.val()).toFixed(2));
    }
  });

  $("input#id_barrier").change(function () {
    if ($("input#id_barrier").prop("checked")) {
      $("div.trade-ticket-bar-up, div.trade-ticket-bar-dn").show();
    } else {
      $("div.trade-ticket-bar-up, div.trade-ticket-bar-dn").hide();
    }
  });

  const valuationTable = new Handsontable($("#valuation-table")[0], {
    startRows: 7,
    startCols: 5,
    minSpareRows: 0,
    contextMenu: true,
    readOnly: true,
    colHeaders: ["Measure", "CCY1", "CCY2", "CCY1%", "CCY2%"],
    data: [
      { measure: "npv" },
      { measure: "delta" },
      { measure: "gamma" },
      { measure: "vega" },
      { measure: "theta" },
      { measure: "rho" },
      { measure: "dividendRho" },
    ],
    // prettier-ignore
    columns: [
      { data: "measure", type: "text" },
      { data: "ccy1", type: "numeric", numericFormat: { pattern: "0,0.00" },},
      { data: "ccy2", type: "numeric", numericFormat: { pattern: "0,0.00" },},
      { data: "ccy1Pct", type: "numeric", numericFormat: { pattern: "0,0.00" }, },
      { data: "ccy2Pct", type: "numeric", numericFormat: { pattern: "0,0.00" }, },
    ],
    colWidths: [100, 100, 100, 100, 100],
    licenseKey: "non-commercial-and-evaluation",
  });

  const mktTable = new Handsontable($("#mkt-table")[0], {
    startRows: 7,
    startCols: 2,
    minSpareRows: 0,
    contextMenu: true,
    readOnly: false,
    colHeaders: ["Data", "Value"],
    data: [
      { data: "spot", value: "" },
      { data: "spot0", value: "" },
      { data: "fwd", value: "" },
      { data: "vol", value: "" },
      { data: "q", value: "" },
      { data: "r", value: "" },
      { data: "swap_point", value: "" },
    ],
    columns: [
      { data: "data", type: "text" },
      {
        data: "value",
        type: "numeric",
        numericFormat: { pattern: "0,0.0000" },
      },
    ],
    colWidths: [100, 100, 100, 100, 100],
    licenseKey: "non-commercial-and-evaluation",
  });

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

  function load_fxo_mkt() {
    $("#form-alert").html("");
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
          "/load_fxo_mkt",
          {
            as_of: as_of,
            ccy_pair: ccy_pair,
            maturity_date: maturity_date,
            strike_price: strike_price,
          },
          axios_cfg
        )
        .then((response) => {
          //console.log(JSON.stringify(response.data.result));
          let hd = response.data.result.headers;
          mktTable.updateData(response.data.result.values);
          // prettier-ignore
          $("#mkt-table").handsontable({
            data: response.data.result.values,
            minSpareRows: 0,
            colHeaders: true,
            contextMenu: true,
            readOnly: false,
            colHeaders: Object.keys(response.data.result.values[0]),
            columns: [
              { data: hd[0], type: "text" },
              { data: hd[1], type: "numeric", numericFormat: { pattern: "0,0.0000" }, },
            ],
            colWidths: [100, 100],
            licenseKey: "non-commercial-and-evaluation",
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

  async function load_fxo_mkt2() {
    // return a promise
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
      let data = {
        as_of: as_of,
        ccy_pair: ccy_pair,
        maturity_date: maturity_date,
        strike_price: strike_price,
      };
      return await axios.post("/load_fxo_mkt", data, axios_cfg);
    }
  }

  function updateMktTable() {
    load_fxo_mkt2().then((response) => {
      mktTable.updateData(response.data.result.values);
    });
  }

  async function price_fxo2(path, scn = false) {
    if (
      $("#id_up-bar-effect").prop("checked") == false &&
      $("#id_low-bar-effect").prop("checked") == false
    ) {
      $("#id_barrier").prop("checked", false);
    }
    let trade_form_data = new FormData($(".trade-form")[0]); // use [0] to convert jquery obj to DOM
    var form_alert = $("#form-alert");
    form_alert.html("");
    $("input, select").removeClass("is-invalid");
    if (scn) {
      trade_form_data.append(
        "measure",
        $("input[name=scn-measure]:checked", "#scn-form").val()
      );
      trade_form_data.append(
        "unit",
        $("input[name=scn-unit]:checked", "#scn-form").val()
      );
      trade_form_data.append("scnLo", $("#scn-lo").val());
      trade_form_data.append("scnUp", $("#scn-up").val());
    }
    return await axios({
      method: "post",
      url: path, // starting with slash will use the root of the site
      data: trade_form_data,
      headers: { "Content-Type": "multipart/form-data" },
    });
  }

  function updateValuationTable(event) {
    event.preventDefault();
    updateMktTable();
    let path = "/api/trade/fxo/price";
    price_fxo2(path)
      .then((response) => {
        valuationTable.updateData(response.data.result.values);
        valuationTable.updateSettings({
          colHeaders: response.data.result.headers,
        });
      })
      .catch((error) => {
        var e = error.response.data.errors;
        for (var y in e) {
          form_alert.append(
            // append is add a element at the end inside the tag
            `<div class="alert alert-danger" role="alert">${e[y]}</div>`
          );
          $(`[name="${y}"]`).addClass("is-invalid");
        }
      });
  }

  function calculateScn(event) {
    event.preventDefault();
    updateMktTable();
    var scnChart = echarts.init(document.getElementById("plot-body-scn"));
    scnChart.showLoading({
      text: "Loading...",
    });
    let path = "/api/trade/fxo/scn";
    price_fxo2(path, true).then((response) => {
      console.log(response.data.result);
      var para = response.data.parameters;
      $("#scn-lo").val(para.range_lo);
      $("#scn-up").val(para.range_up);
      $("label[for='unit-ccy1']").html(para.ccy1);
      $("label[for='unit-ccy2']").html(para.ccy2);
      $("label[for='unit-ccy1pct']").html(para.ccy1 + "%");
      $("label[for='unit-ccy2pct']").html(para.ccy2 + "%");
      var dp = para.unit.slice(-1) == "%" ? 6 : 2;
      var option = {
        title: { text: para.measure },
        tooltip: {
          trigger: "axis",
          valueFormatter: (value) => value.toFixed(dp),
        },
        legend: { data: ["Sold"] },
        xAxis: { type: "value", name: "Spot", min: "dataMin", max: "dataMax" },
        yAxis: { type: "value" },
        series: [
          {
            showSymbol: true,
            type: "line",
            data: response.data.result,
          },
        ],
      };
      scnChart.hideLoading();
      scnChart.setOption(option);
    });
  }

  function plugIframe() {
    const date = $("#id_as_of").val();
    const ccy_pair = $("#id_ccy_pair").val().replace("/", "");
    var fxv = "/mkt/fxv/" + ccy_pair + "/" + date;
    $("#modal-fxv .modal-body").html(
      `<iframe src="` +
        fxv +
        `" style="width: 920px; height:480px; margin:auto;"></iframe>`
    );
  }

  $("#id_maturity_date, input#id_as_of").focusout(updateMktTable);
  $("#id_strike_price, #id_ccy_pair").change(updateMktTable);
  $("#btn-price").click(updateValuationTable);
  $("#btn-scn-pop").click(calculateScn);
  $("#btn-scn-calc").click(calculateScn);
  $("#btn-mkt-pop").click(plugIframe);

  // https://studygyaan.com/django/render-html-as-you-type-with-django-and-ajax
});
