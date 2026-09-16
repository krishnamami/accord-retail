import React, { useState, useEffect } from "react";
import Navigation from "./components/layouts/Navigation";
import TodayScreen from "./components/screens/TodayScreen";
import "./styles/global.css";

function App() {
  const [currentScreen, setCurrentScreen] = useState("TODAY");
  const [business, setBusiness] = useState(null);

  useEffect(() => {
    setBusiness({ name: "TechCo Inc", revenue: 15000000 });
  }, []);

  return (
    <div className="accord-app">
      <Navigation currentScreen={currentScreen} onNavigate={setCurrentScreen} />
      <main className="accord-main">
        {business ? <TodayScreen business={business} /> : <div>Loading...</div>}
      </main>
    </div>
  );
}

export default App;
