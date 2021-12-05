import React, { useState, useEffect } from "react";
import ReactDOM from "react-dom";
import axios from "axios";
import AsOfForm from "./AsOfForm";

function FXOForm(props) {
  const [form, setForm] = useState("");
  const [valForm, setValForm] = useState("");
  useEffect(() => {
    axios
      .get("fxodetail")
      .then((response) => {
        setForm(response.data.form);
      })
      .catch(() => {
        console.log(Error("cannot fetch form"));
      });
  }, []);

  const handleClick = (e) => {
    e.preventDefault();
    axios
      .post("fxo_price", { formdata: 123 })
      .then((response) => response.json())
      .then((data) => setValForm(data.valuation_message))
      .catch(() => {
        console.log(Error("cannot return result"));
      });
    ReactDOM.render(
      <div>{valForm}</div>,
      document.querySelector(".valuation-form")
    );
  };

  return (
    <form className="fxo-form" method="post">
      <button className="btn btn-primary" onClick={handleClick}>
        Price
      </button>
      <br />
      <AsOfForm />
      <table
        className="trade-form"
        dangerouslySetInnerHTML={{ __html: form }}
      />
    </form>
  );
}

export default FXOForm;
