// <div id="root" style="border: solid black 2px;"></div>
// <br/>
// <div id="bottom" style="border: solid red 2px;"></div>


function FXOForm() {
  var formhtml = `<input type="text" id="name" label="Name" placeholder="Input your name"></input>`
  clickHandler = (e) => { 
    e.preventDefault();
    ReactDOM.render(<div>HI</div>, document.getElementById('bottom'))
  }
  
  return (
    <form>
      <div dangerouslySetInnerHTML={{ __html: formhtml }}></div>
      <button onClick={clickHandler}>Click</button>
    </form>
  )
}

ReactDOM.render(
  <FXOForm />,
  document.getElementById('root')
);
