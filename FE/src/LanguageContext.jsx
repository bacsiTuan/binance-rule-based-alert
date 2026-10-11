import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { DEFAULT_LANGUAGE, errorMessage, LANGUAGE_KEY, LOCALES, normalizeLanguage, readLanguage, translate } from "./i18n.js";

const LanguageContext = createContext(null);

export function LanguageProvider({ children }) {
  const [language, updateLanguage] = useState(() => {
    try { return readLanguage(localStorage); } catch { return DEFAULT_LANGUAGE; }
  });
  const setLanguage = (value) => updateLanguage(normalizeLanguage(value));
  const t = useCallback((text, values) => translate(text, language, values), [language]);
  const localizedError = useCallback((error) => errorMessage(error, language), [language]);

  useEffect(() => {
    document.documentElement.lang = language;
    document.title = t("Indicator Alert – Cảnh báo chỉ báo Binance");
    document.querySelector('meta[name="description"]')?.setAttribute("content",
      t("Tạo và quản lý luật cảnh báo chỉ báo kỹ thuật (SMA, EMA, RSI) cho dữ liệu thị trường Binance."));
    try { localStorage.setItem(LANGUAGE_KEY, language); } catch { /* Language switching still works without storage. */ }
  }, [language, t]);

  return <LanguageContext.Provider value={{ language, setLanguage, locale: LOCALES[language], t, localizedError }}>
    {children}
  </LanguageContext.Provider>;
}

export const useLanguage = () => useContext(LanguageContext);
