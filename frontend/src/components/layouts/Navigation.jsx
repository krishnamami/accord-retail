import React from "react";

export default function Navigation({ currentScreen, onNavigate }) {
  return (
    <nav className="navigation">
      <h1>Accord Retail</h1>
      <button onClick={() => onNavigate("TODAY")}>Today</button>
      <button onClick={() => onNavigate("DECISIONS")}>Decisions</button>
    </nav>
  );
}
