import React, { useState, useEffect } from "react";
import axios from "axios";

function TradeRequest() {
  const [results, setResults] = useState([]);

  useEffect(() => {
    res = axios.get("swpm/api/fxo").then((response) => {
      setResults(response.data);
    });
  }, []);

  return (
    <table className="trade-table">
      {results.map((result) => (
        <tr key={result.objectID}>
          <td>{result.id}</td>
          <td>{result.notional_1}</td>
          <td>{result.product_type}</td>
        </tr>
      ))}
    </table>
  );
}

export default TradeRequest;
