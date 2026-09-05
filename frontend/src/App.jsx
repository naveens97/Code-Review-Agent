import { AnimatePresence } from "framer-motion";
import { FileCode2, History as HistoryIcon, TerminalSquare, MessageSquare } from "lucide-react";
import { Component, useEffect, useRef, useState } from "react";
import { deleteHistoryItem, fetchHistory, fetchHistoryDetail, reviewCode, runCode } from "./api";
import CodeEditor from "./components/CodeEditor";
import Header from "./components/Header";
import HistoryPanel from "./components/HistoryPanel";
import OutputPanel from "./components/OutputPanel";
import ReviewPanel from "./components/ReviewPanel";
import ReviewPrompt from "./components/ReviewPrompt";
import StdinPanel from "./components/StdinPanel";
import Toolbar from "./components/Toolbar";
import ChatPanel from "./components/ChatPanel";
import { DEFAULT_CODE, SUPPORTED_LANGUAGES } from "./constants";
import "./styles/App.css";

const TABS = [
  { id: "output", label: "Output", icon: TerminalSquare },
  { id: "review", label: "Review", icon: FileCode2 },
  { id: "history", label: "History", icon: HistoryIcon },
  { id: "chat", label: "Chat", icon: MessageSquare },
];

// ---------------------------------------------------------------------------
// Simple error boundary so a crash in one panel doesn't take down the app.
// ---------------------------------------------------------------------------
class PanelErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }
  static getDerivedStateFromError(error) {
    return { error };
  }
  render() {
    if (this.state.error) {
      return (
        <div className="panel-content empty-state">
          <p style={{ color: "var(--critical)" }}>Something went wrong in this panel.</p>
          <p style={{ fontSize: 12, color: "var(--ink-faint)" }}>{this.state.error.message}</p>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function App() {
  const [language, setLanguage] = useState("python");
  const [code, setCode] = useState(DEFAULT_CODE["python"]);
  const [stdin, setStdin] = useState("");
  const [activeTab, setActiveTab] = useState("output");

  const [isRunning, setIsRunning] = useState(false);
  const [runResult, setRunResult] = useState(null);
  const [showReviewPrompt, setShowReviewPrompt] = useState(false);

  const [isReviewing, setIsReviewing] = useState(false);
  const [review, setReview] = useState(null);

  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const editorRef = useRef(null);

  // -------------------------------------------------------------------------
  // Switch language: swap the editor content to the new default only when the
  // editor still contains the previous language's default (i.e. the user
  // hasn't written anything yet).  If they have custom code, leave it alone.
  // -------------------------------------------------------------------------
  const handleLanguageChange = (newLang) => {
    const prevDefault = DEFAULT_CODE[language] ?? "";
    if (code === prevDefault || code.trim() === "") {
      setCode(DEFAULT_CODE[newLang] ?? "");
    }
    setLanguage(newLang);
    setRunResult(null);
    setReview(null);
    setShowReviewPrompt(false);
  };

  const loadHistory = async () => {
    setHistoryLoading(true);
    try {
      const items = await fetchHistory(50);
      setHistory(items);
    } catch {
      // History is a convenience feature — a failed fetch shouldn't block anything.
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  // Ctrl+Enter → Run
  useEffect(() => {
    const handler = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        if (!isRunning) handleRun();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  });

  const handleRun = async () => {
    setIsRunning(true);
    setShowReviewPrompt(false);
    setActiveTab("output");
    try {
      const result = await runCode(code, language, stdin);
      setRunResult(result);
      if (result.success) setShowReviewPrompt(true);
    } catch (err) {
      setRunResult({
        success: false,
        stdout: "",
        stderr: err.message || "Could not reach the server.",
        exit_code: -1,
        execution_time_ms: 0,
        timed_out: false,
      });
    } finally {
      setIsRunning(false);
    }
  };

  const handleReview = async () => {
    setIsReviewing(true);
    setShowReviewPrompt(false);
    setActiveTab("review");
    try {
      const result = await reviewCode(code, language);
      setReview(result);
      loadHistory();
    } catch (err) {
      setReview({
        rating: { score: 0, label: "Error", breakdown: { critical: 0, warning: 0, info: 0 } },
        issues: [],
        summary: err.message || "Could not reach the server.",
        metrics: { code_lines: 0, functions: 0, classes: 0 },
      });
    } finally {
      setIsReviewing(false);
    }
  };

  const handleSelectHistory = async (id) => {
    try {
      const detail = await fetchHistoryDetail(id);
      setCode(detail.code);
      if (detail.language && SUPPORTED_LANGUAGES.find((l) => l.id === detail.language)) {
        setLanguage(detail.language);
      }
      setReview(detail);
      setRunResult(null);
      setActiveTab("review");
    } catch {
      // leave current state alone
    }
  };

  const handleDeleteHistory = async (id) => {
    setHistory((prev) => prev.filter((item) => item.id !== id));
    try {
      await deleteHistoryItem(id);
    } catch {
      loadHistory(); // resync if the delete didn't actually happen
    }
  };

  const handleJumpToLine = (line) => {
    editorRef.current?.revealLine(line);
  };

  return (
    <div className="app-shell">
      <Header language={language} />
      <Toolbar
        language={language}
        onLanguageChange={handleLanguageChange}
        onRun={handleRun}
        onReview={handleReview}
        isRunning={isRunning}
        isReviewing={isReviewing}
      />

      <div className="workspace">
        <div className="editor-pane">
          <CodeEditor
            ref={editorRef}
            value={code}
            onChange={setCode}
            language={language}
          />
          <StdinPanel value={stdin} onChange={setStdin} />
        </div>

        <div className="side-pane">
          <div className="tab-bar">
            {TABS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                className={`tab-btn ${activeTab === id ? "tab-btn-active" : ""}`}
                onClick={() => setActiveTab(id)}
              >
                <Icon size={14} />
                {label}
              </button>
            ))}
          </div>

          <div className="tab-content">
            {activeTab === "output" && (
              <PanelErrorBoundary>
                <OutputPanel isRunning={isRunning} result={runResult} language={language} />
              </PanelErrorBoundary>
            )}
            {activeTab === "review" && (
              <PanelErrorBoundary>
                <ReviewPanel isReviewing={isReviewing} review={review} onJumpToLine={handleJumpToLine} />
              </PanelErrorBoundary>
            )}
            {activeTab === "history" && (
              <PanelErrorBoundary>
                <HistoryPanel
                  items={history}
                  isLoading={historyLoading}
                  onSelect={handleSelectHistory}
                  onDelete={handleDeleteHistory}
                />
              </PanelErrorBoundary>
            )}
            {activeTab === "chat" && (
              <PanelErrorBoundary>
                <ChatPanel code={code} language={language} />
              </PanelErrorBoundary>
            )}
          </div>
        </div>
      </div>

      <AnimatePresence>
        {showReviewPrompt && runResult && (
          <ReviewPrompt
            executionTimeMs={runResult.execution_time_ms}
            onAccept={handleReview}
            onDismiss={() => setShowReviewPrompt(false)}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
