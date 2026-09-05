import { Hexagon, Key } from "lucide-react";
import { useEffect, useState } from "react";
import { SUPPORTED_LANGUAGES } from "../constants";

export default function Header({ language }) {
  const currentLang = SUPPORTED_LANGUAGES.find((l) => l.id === language);
  const displayLabel = currentLang ? currentLang.label : "Python 3";

  const [apiKey, setApiKey] = useState("");

  useEffect(() => {
    const savedKey = localStorage.getItem("ai_api_key");
    if (savedKey) setApiKey(savedKey);
  }, []);

  const handleKeyChange = (e) => {
    const val = e.target.value;
    setApiKey(val);
    localStorage.setItem("ai_api_key", val);
  };

  return (
    <header className="app-header">
      <div className="brand">
        <Hexagon size={22} strokeWidth={2.25} className="brand-mark" />
        <span className="brand-name">CodeSage</span>
        <span className="brand-tag">code review agent</span>
      </div>
      <div className="header-right">
        <div className="api-key-input-wrapper" style={{ display: "flex", alignItems: "center", background: "var(--bg-surface)", borderRadius: "var(--radius-sm)", padding: "4px 10px", border: "1px solid var(--line)", marginRight: "12px" }}>
          <Key size={14} style={{ color: "var(--ink-faint)", marginRight: "6px" }} />
          <input 
            type="password" 
            placeholder="OpenAI / Gemini API Key" 
            value={apiKey} 
            onChange={handleKeyChange}
            style={{ background: "transparent", border: "none", color: "var(--ink)", outline: "none", fontSize: "12px", width: "160px" }}
          />
        </div>
        <span className="lang-pill">
          <span className="lang-dot" /> {displayLabel}
        </span>
      </div>
    </header>
  );
}
