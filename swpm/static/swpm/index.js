document.addEventListener('DOMContentLoaded', function() {

    $('.ccypair legend').click( () => {
        $('.ccypair table').toggle();
        $('.ccypair button').toggle();
    });

    document.querySelectorAll('legend')[0].addEventListener('click', () =>{
        const effective_date = new Date();
		effective_date.setDate(effective_date.getDate()+2);
        var oneyear = new Date();
        oneyear.setFullYear(oneyear.getFullYear()+1);
		oneyear.setDate(oneyear.getDate()+2);
        document.getElementById('id_book').value = "FXO1"
        document.getElementById('id_counterparty').value = "HSBC";
        document.querySelectorAll('[id*="effective_date"]').forEach( d => {d.value = effective_date.toISOString().split('T')[0];} );
        document.querySelectorAll('[id*="maturity_date"]').forEach( d => {d.value = oneyear.toISOString().split('T')[0];} );
        document.querySelectorAll('[id*="notional"]').forEach( d => {d.value = '1000000';} );
        document.querySelectorAll('#id_form-0-fixed_rate').forEach( d => {d.value = '0.03';} );
        document.querySelectorAll('[id*="freq"]').forEach( d => {d.value = '3M';} );
        document.getElementById('id_form-0-reset_freq').value = '';
        document.querySelectorAll('[id*="day_counter"]').forEach( d => {d.value = 'Actual360';} );
        document.querySelectorAll('[id*="index"]')[0].value = '';
        document.querySelectorAll('[id*="index"]')[1].value = 'USD LIBOR 3M';
        document.querySelectorAll('[id*="pay_rec"]')[0].value = '1';
        document.querySelectorAll('[id*="pay_rec"]')[1].value = '-1';
        document.querySelectorAll('[id*="ccy"]')[0].value = 'USD';
        document.querySelectorAll('[id*="ccy"]')[1].value = 'USD';
    })

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
