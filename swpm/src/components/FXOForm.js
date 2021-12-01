import React, { useState, useEffect } from "react";
import AsOfForm from "./AsOfForm";

function FXOForm(props) {
  const [form, setForm] = useState("");
  useEffect(() => {
    fetch("fxodetail")
      .then((response) => response.json())
      .then((data) => setForm(data.form));
  });

  return (
    <form action="{% url 'pricing' %}" method="post">
      <button className="btn btn-primary">Price</button>
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
