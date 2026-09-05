import Editor from "@monaco-editor/react";
import { useEffect, forwardRef, useImperativeHandle, useRef } from "react";
import { SUPPORTED_LANGUAGES } from "../constants";
import { autocompleteCode } from "../api";

// Map our language IDs to Monaco's built-in language IDs
const MONACO_LANGUAGE_MAP = Object.fromEntries(
  SUPPORTED_LANGUAGES.map(({ id, monacoId }) => [id, monacoId])
);

// Custom theme so the editor matches the app's instrument-panel palette
// instead of Monaco's stock vs-dark, which would clash with everything
// around it.
function defineTheme(monaco) {
  monaco.editor.defineTheme("codesage-dark", {
    base: "vs-dark",
    inherit: true,
    rules: [
      { token: "comment", foreground: "4a6a8a", fontStyle: "italic" },
      { token: "keyword", foreground: "00e5c8" },
      { token: "string", foreground: "00f5a0" },
      { token: "number", foreground: "ffaa00" },
      { token: "function", foreground: "00b4d8" },
      { token: "variable", foreground: "e8f4ff" },
      { token: "type", foreground: "9b5de5" },
      { token: "operator", foreground: "ff3d71" },
    ],
    colors: {
      "editor.background": "#070e1a",
      "editor.foreground": "#e8f4ff",
      "editor.lineHighlightBackground": "#0c1e3450",
      "editor.lineHighlightBorder": "#00000000",
      "editorLineNumber.foreground": "#2a4a68",
      "editorLineNumber.activeForeground": "#5a8ab4",
      "editorCursor.foreground": "#00e5c8",
      "editor.selectionBackground": "#00e5c830",
      "editorGutter.background": "#070e1a",
      "editorWidget.background": "#0a1628",
      "editorWidget.border": "#0c2038",
      "scrollbarSlider.background": "#0c203880",
      "scrollbarSlider.hoverBackground": "#1a3a58a0",
      "editorIndentGuide.background": "#0a1828",
      "editorIndentGuide.activeBackground": "#0c2038",
    },
  });
}

const CodeEditor = forwardRef(function CodeEditor({ value, onChange, language = "python" }, ref) {
  const editorRef = useRef(null);
  const monacoRef = useRef(null);
  const decorationsRef = useRef([]);

  useEffect(() => {
    const monaco = monacoRef.current;
    if (!monaco) return;

    // Use a flag to prevent resolving old debounced promises
    let activeToken = null;

    const provider = monaco.languages.registerInlineCompletionsProvider(MONACO_LANGUAGE_MAP[language] ?? language, {
      provideInlineCompletions: async (model, position, context, token) => {
        // Only trigger on explicit request or typing (not just moving cursor)
        if (context.triggerKind !== monaco.languages.InlineCompletionTriggerKind.Invoke && 
            context.triggerKind !== monaco.languages.InlineCompletionTriggerKind.Automatic) {
          return { items: [] };
        }

        const offset = model.getOffsetAt(position);
        const code = model.getValue();
        const prefix = code.substring(0, offset);
        const suffix = code.substring(offset);

        // Debounce logic manually (wait 250ms for faster UI response)
        const currentToken = {};
        activeToken = currentToken;
        
        await new Promise((resolve) => setTimeout(resolve, 250));
        
        if (activeToken !== currentToken || token.isCancellationRequested) {
          return { items: [] };
        }

        try {
          const res = await autocompleteCode(prefix, suffix, language);
          if (res.completion && activeToken === currentToken && !token.isCancellationRequested) {
            return {
              items: [
                {
                  insertText: res.completion,
                  range: new monaco.Range(position.lineNumber, position.column, position.lineNumber, position.column),
                }
              ]
            };
          }
        } catch (e) {
          console.error("Autocomplete error:", e);
        }

        return { items: [] };
      },
      freeInlineCompletions() {}
    });

    return () => provider.dispose();
  }, [language]);

  useImperativeHandle(ref, () => ({
    revealLine(line) {
      const editor = editorRef.current;
      const monaco = monacoRef.current;
      if (!editor || !monaco || !line) return;
      editor.revealLineInCenter(line);
      decorationsRef.current = editor.deltaDecorations(decorationsRef.current, [
        {
          range: new monaco.Range(line, 1, line, 1),
          options: {
            isWholeLine: true,
            className: "highlighted-line",
            glyphMarginClassName: "highlighted-line-glyph",
          },
        },
      ]);
      window.setTimeout(() => {
        if (editorRef.current) {
          decorationsRef.current = editorRef.current.deltaDecorations(decorationsRef.current, []);
        }
      }, 1800);
    },
  }));

  return (
    <Editor
      language={MONACO_LANGUAGE_MAP[language] ?? language}
      theme="codesage-dark"
      value={value}
      onChange={(v) => onChange(v ?? "")}
      beforeMount={defineTheme}
      onMount={(editor, monaco) => {
        editorRef.current = editor;
        monacoRef.current = monaco;
        // Trigger a fake language change to force the useEffect to run after mount
        onChange(value); 
      }}
      options={{
        fontFamily: "Consolas, Menlo, Monaco, 'Courier New', monospace",
        fontSize: 14,
        lineHeight: 22,
        minimap: { enabled: false },
        padding: { top: 16 },
        scrollBeyondLastLine: false,
        smoothScrolling: true,
        cursorBlinking: "smooth",
        renderLineHighlight: "line",
        automaticLayout: true,
        tabSize: 4,
        glyphMargin: true,
        fixedOverflowWidgets: true,
        inlineSuggest: { enabled: true },
        suggestOnTriggerCharacters: true,
      }}
    />
  );
});

export default CodeEditor;
