document.addEventListener("DOMContentLoaded", function () {
  $(".ccypair legend").click(() => {
    $(".ccypair table").toggle();
    $(".ccypair button").toggle();
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

  document.querySelectorAll("legend")[0].addEventListener("click", () => {
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

  $(".btn-primary").click(() => {
    $(".full-screen").show();
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
