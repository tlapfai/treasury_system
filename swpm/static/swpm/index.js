document.addEventListener('DOMContentLoaded', function() {

    $('.ccypair legend').click( () => {
        $('.ccypair table').toggle();
        $('.ccypair button').toggle();
    });

    document.querySelectorAll('legend')[0].addEventListener('click', () =>{
        document.getElementById('id_book').value = "FXO1"
        document.getElementById('id_counterparty').value = "HSBC";
        document.querySelectorAll('[id*="effective_date"]').forEach( d => {d.value = '2021-11-02';} );
        document.querySelectorAll('[id*="maturity_date"]').forEach( d => {d.value = '2022-11-02';} );
        document.querySelectorAll('[id*="notional"]').forEach( d => {d.value = '1000000';} );
        document.querySelectorAll('[id*="rate"]').forEach( d => {d.value = '0.03';} );
        document.querySelectorAll('[id*="freq"]').forEach( d => {d.value = '3M';} );
        document.querySelectorAll('[id*="counter"]').forEach( d => {d.value = 'A360';} );
        document.querySelectorAll('[id*="index"]').forEach( d => {d.value = 'USD LIBOR';} );
        document.querySelectorAll('[id*="pay_rec"]')[0].value = '1';
        document.querySelectorAll('[id*="pay_rec"]')[1].value = '-1';
        document.querySelectorAll('[id*="ccy"]')[0].value = 'USD';
        document.querySelectorAll('[id*="ccy"]')[1].value = 'USD';
    })

    function updateTextView(_obj){
        var num = getNumber(_obj.val());
        if(num==0){
          _obj.val('');
        }else{
          _obj.val(num.toLocaleString());
        }
      }
      function getNumber(_str){
        var arr = _str.split('');
        var out = new Array();
        for(var cnt=0;cnt<arr.length;cnt++){
          if(isNaN(arr[cnt])==false){
            out.push(arr[cnt]);
          }
        }
        return Number(out.join(''));
      }
      $(document).ready(function(){
        $('input[type=text]').on('keyup',function(){
          updateTextView($(this));
        });
      });
});