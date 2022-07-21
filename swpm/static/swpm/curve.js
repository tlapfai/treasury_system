$(document).ready(function () {
  const regex1 = /^(\d+[DWMYdwmy])+$/;
  const axios_cfg = { headers: { "X-CSRFToken": $.cookie("csrftoken") } };

  const day_counters = [
    "",
    "Actual360",
    "Actual365Fixed",
    "ActualActual",
    "Thirty360",
  ];

  const curveTable = new Handsontable($(".curve-table")[0], {
    startRows: 1,
    startCols: 5,
    minSpareRows: 1,
    contextMenu: true,
    readOnly: false,
    colHeaders: ["Tenor", "Instrument", "Rate", "Day Counter", "Ccy Pair"],
    // prettier-ignore
    columns: [
      { data: "tenor", type: "text", validator: regex1, allowInvalid: false, allowEmpty: false },
      { data: "instrument", type: "text", allowEmpty: false },
      { data: "rate", type: "numeric", numericFormat: { pattern: "0,0.00000000" }, },
      { data: "day_counter", type: "dropdown", source: day_counters },
      { data: "ccy_pair_id", type: "text" },
    ],
    colWidths: [50, 100, 100, 120, 80],
    licenseKey: "non-commercial-and-evaluation",
  });

  async function load_curve() {
    const date = $("input#date").val();
    const ccy = $("input#ccy").val().trim();
    const name = $("input#name").val().trim();
    const data = { date: date, ccy: ccy, name: name };
    return await axios.get("/api/mkt/curve", { params: data }, axios_cfg);
  }

  if ($("input#date").val() && $("input#ccy").val() && $("input#name").val()) {
    load_curve().then(function (response) {
      curveTable.updateData(response.data.result);
      curveTable.updateSettings({ minSpareRows: 1 });
    });
  }

  async function save_curve() {
    const data = {
      date: $("input#date").val(),
      ccy: $("input#ccy").val().trim(),
      name: $("input#name").val().trim(),
      rates: curveTable.getData(),
    };
    return await axios.post("/api/mkt/curve", data, axios_cfg);
  }

  $("#save").click(function () {
    $(".message-area").html("");
    $(".message-area").hide();
    save_curve()
      .then(function (response) {
        $(".message-area").html(`<div>${response.data.message}</div>`);
        $(".message-area").show();
      })
      .catch(function (error) {
        var e = error.response.data.errors;
        $.each(e, function () {
          $(".message-area").append(`<div>${this}</div>`);
        });
        $(".message-area").show();
      });
  });

  $("#ccy").change(function () {
    $("#ccy").val($("#ccy").val().toUpperCase());
  });

  $("#name").change(function () {
    $("#name").val($("#name").val().toUpperCase());
  });

  async function calc_curve() {
    const date = $("input#date").val();
    const ccy = $("input#ccy").val().trim();
    const name = $("input#name").val().trim();
    const data = { date: date, ccy: ccy, name: name };
    return await axios.get("/api/mkt/curve/calc", { params: data }, axios_cfg);
  }

  $("button#btn-plot").click(function () {
    calc_curve().then(function (response) {
      var myChart = echarts.init(document.getElementById("plot"));
      var option = {
        title: { text: "Zero Rate Term Structure" },
        tooltip: {
          trigger: "axis",
        },
        legend: { data: ["Sold"] },
        xAxis: { type: "time" },
        yAxis: { type: "value" },
        series: [
          {
            showSymbol: true,
            type: "line",
            data: response.data.result,
          },
        ],
      };
      myChart.setOption(option);
    });
  });

  $("#btn-zero-calc").click(function () {
    $(".message-area").hide();
    $(".zero-rate-table").html("");
    calc_curve()
      .then(function (response) {
        $(".zero-rate-card").removeClass("visually-hidden");
        const zeroTable = new Handsontable($(".zero-rate-table")[0], {
          data: response.data.result,
          startRows: 1,
          startCols: 2,
          minSpareRows: 0,
          contextMenu: true,
          readOnly: true,
          columns: [
            { type: "date", dateFormat: "YYYY-MM-DD" },
            {
              type: "numeric",
              numericFormat: { pattern: "0,0.00000000" },
            },
          ],
          colHeaders: ["Date", "Zero Rate"],
          colWidths: [140, 140],
          licenseKey: "non-commercial-and-evaluation",
        });
      })
      .catch(function (error) {
        var e = error.response.data.errors;
        $.each(e, function () {
          $(".message-area").append(`<div>${this}</div>`);
        });
        $(".message-area").show();
      });
  });
});
