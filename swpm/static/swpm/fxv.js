$(document).ready(function () {
  const regex1 = /^(\d+[DWMYdwmy])+$/;
  const axios_cfg = { headers: { "X-CSRFToken": $.cookie("csrftoken") } };

  const fxvTable = new Handsontable($(".fxv-table")[0], {
    startRows: 1,
    startCols: 6,
    minSpareRows: 1,
    contextMenu: true,
    readOnly: false,
    colHeaders: ["Tenor", "ATM", "10C", "25C", "25P", "10P"],
    data: [{ measure: "npv" }],
    // prettier-ignore
    columns: [
            { data: "tenor", type: "text", validator: regex1, allowInvalid: false },
            { data: "atm", type: "numeric", numericFormat: { pattern: "0,0.00" }, },
            { data: "90", type: "numeric", numericFormat: { pattern: "0,0.00" }, },
            { data: "75", type: "numeric", numericFormat: { pattern: "0,0.00" }, },
            { data: "25", type: "numeric", numericFormat: { pattern: "0,0.00" }, },
            { data: "10", type: "numeric", numericFormat: { pattern: "0,0.00" }, },
        ],
    colWidths: [100, 100, 100, 100, 100, 100],
    licenseKey: "non-commercial-and-evaluation",
  });

  async function load_fxv() {
    const date = $("input#date").val();
    const ccy_pair = $("input#ccy_pair").val().trim();
    const data = { date: date, ccy_pair: ccy_pair };
    return await axios.get("/api/mkt/fxv", { params: data }, axios_cfg);
  }

  if ($("input#date").val() && $("input#ccy_pair").val()) {
    load_fxv().then(function (response) {
      fxvTable.updateData(response.data.result);
      $("#id_atm_type").val(response.data.atm_type);
      $("#id_delta_type").val(response.data.delta_type);
    });
  }

  async function save_fxv() {
    const axios_cfg = { headers: { "X-CSRFToken": $.cookie("csrftoken") } };
    const data = {
      date: $("input#date").val(),
      ccy_pair: $("input#ccy_pair").val().trim(),
      atm_type: $("#id_atm_type").val(),
      delta_type: $("#id_delta_type").val(),
      fxv: fxvTable.getData(),
    };
    return await axios.post("/api/mkt/fxv", data, axios_cfg);
  }

  $("#save").click(function () {
    $(".message-area").hide();
    $(".message-area").html("");
    save_fxv()
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

  $("#ccy_pair").change(function () {
    $("#ccy_pair").val($("#ccy_pair").val().toUpperCase());
  });
});
