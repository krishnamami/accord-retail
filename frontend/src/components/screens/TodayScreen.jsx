import React from "react";

export default function TodayScreen({ business }) {
  return (
    <div>
      <h2>What Needs Your Attention Today</h2>
      <p>Business: {business.name}</p>
      <p>Revenue: ${business.revenue.toLocaleString()}</p>
    </div>
  );
}
