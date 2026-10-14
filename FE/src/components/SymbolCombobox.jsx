import { useEffect, useMemo, useRef, useState } from "react";
import Icon from "./Icon.jsx";

export default function SymbolCombobox({ id, value, symbols, onChange, placeholder, loadingText, emptyText, error, describedBy }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [typing, setTyping] = useState(false);
  const [active, setActive] = useState(0);
  const rootRef = useRef(null);
  const listRef = useRef(null);

  const options = useMemo(() => {
    const q = typing ? query.trim().toUpperCase() : "";
    if (!q) return symbols;
    return symbols
      .filter((s) => s.includes(q))
      .sort((a, b) => Number(b.startsWith(q)) - Number(a.startsWith(q)));
  }, [symbols, query, typing]);

  const close = () => { setOpen(false); setTyping(false); setQuery(""); };

  const select = (symbol) => {
    onChange(symbol);
    close();
  };

  // Đưa mục đang chọn / đang highlight vào vùng nhìn thấy của danh sách cuộn
  useEffect(() => {
    if (!open) return;
    listRef.current?.querySelector(`[data-index="${active}"]`)?.scrollIntoView({ block: "nearest" });
  }, [active, open, options]);

  useEffect(() => {
    if (!open) return undefined;
    const onDown = (e) => { if (!rootRef.current?.contains(e.target)) close(); };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  const openList = () => {
    if (open) return;
    setActive(Math.max(0, symbols.indexOf(value)));
    setOpen(true);
  };

  const onKeyDown = (e) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (!open) openList(); else setActive((i) => Math.min(i + 1, options.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (!open) openList(); else setActive((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (open && options[active]) select(options[active]);
    } else if (e.key === "Escape") {
      if (open) { e.preventDefault(); close(); }
    } else if (e.key === "Tab") {
      close();
    }
  };

  const listId = `${id}-listbox`;

  return (
    <div className="combobox" ref={rootRef}>
      <div className="search-field">
        <Icon name="search" size={17} />
        <input
          id={id}
          type="search"
          role="combobox"
          aria-expanded={open}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-invalid={!!error}
          aria-describedby={describedBy}
          autoComplete="off"
          placeholder={placeholder}
          value={typing ? query : (value || (symbols.length ? "" : loadingText))}
          onFocus={(e) => { openList(); e.target.select(); }}
          onClick={openList}
          onChange={(e) => { setQuery(e.target.value); setTyping(true); setActive(0); setOpen(true); }}
          onKeyDown={onKeyDown}
        />
      </div>
      {open && (
        <ul id={listId} className="combobox-list" role="listbox" ref={listRef}>
          {options.length === 0 && <li className="combobox-empty" role="presentation">{emptyText}</li>}
          {options.map((s, i) => (
            <li
              key={s}
              data-index={i}
              role="option"
              aria-selected={s === value}
              className={`combobox-option${i === active ? " active" : ""}${s === value ? " selected" : ""}`}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => select(s)}
              onMouseEnter={() => setActive(i)}
            >
              {s}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
