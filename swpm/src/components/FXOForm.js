import React, { useState, useEffect } from "react";

function FXOForm() {
  const [form, setForm] = useState("");
  useEffect(() => {
    fetch("fxodetail")
      .then((response) => response.json())
      .then((data) => setForm(data.form));
  });

  return (
    <table className="trade-form" dangerouslySetInnerHTML={{ __html: form }} />
  );
}

export default FXOForm;
