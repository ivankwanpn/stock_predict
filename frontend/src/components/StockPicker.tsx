import { useState, useRef, useEffect } from 'react';
import { api } from '../api/client';
import { useLang } from '../i18n/LanguageContext';
import type { StockSearchResult } from '../types';

interface StockPickerProps {
  value: string;
  onChange: (ticker: string) => void;
}

export default function StockPicker({ value, onChange }: StockPickerProps) {
  const { t } = useLang();
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [results, setResults] = useState<StockSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const q = e.target.value;
    setQuery(q);

    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (q.trim().length < 1) {
      setResults([]);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      setSearching(true);
      try {
        const data = await api.searchStocks(q);
        setResults(data as StockSearchResult[]);
      } catch {
        setResults([]);
      } finally {
        setSearching(false);
      }
    }, 300);
  };

  const handleSelect = (ticker: string) => {
    onChange(ticker);
    setOpen(false);
    setQuery('');
    setResults([]);
  };

  const displayValue = value || t('selectStock');

  return (
    <div ref={ref} className="relative w-72">
      <label className="block text-xs text-gray-400 mb-1 font-medium uppercase tracking-wider">
        {t('stock')}
      </label>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-left text-gray-100 flex items-center justify-between hover:border-gray-600 transition-colors"
      >
        <span>{displayValue}</span>
        <svg
          className={`w-4 h-4 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="absolute z-50 mt-1 w-full bg-gray-800 border border-gray-700 rounded-lg shadow-xl max-h-72 overflow-hidden">
          <div className="p-2 border-b border-gray-700">
            <input
              type="text"
              placeholder={t('searchStock')}
              value={query}
              onChange={handleSearchChange}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && query.trim()) {
                  handleSelect(query.trim().toUpperCase());
                }
              }}
              autoFocus
              className="w-full bg-gray-900 border border-gray-600 rounded px-2.5 py-1.5 text-sm text-gray-100 placeholder-gray-500 outline-none focus:border-blue-500"
            />
            {searching && (
              <div className="mt-1 flex items-center gap-2 text-xs text-gray-500">
                <div className="animate-spin w-3 h-3 border-2 border-blue-500 border-t-transparent rounded-full" />
                {t('analyzing')}
              </div>
            )}
          </div>
          <ul className="overflow-y-auto max-h-56">
            {results.length === 0 && query.trim().length >= 1 && !searching ? (
              <li
                onClick={() => handleSelect(query.trim().toUpperCase())}
                className="px-3 py-2.5 text-sm cursor-pointer text-gray-200 hover:bg-gray-700 transition-colors"
              >
                {t('pressEnterToUse')} <span className="font-mono">{query.toUpperCase()}</span>
              </li>
            ) : results.length === 0 && !searching ? (
              <li className="px-3 py-4 text-sm text-gray-500 text-center">{t('noResults')}</li>
            ) : (
              results.map((result) => (
                <li
                  key={result.ticker}
                  onClick={() => handleSelect(result.ticker)}
                  className={`px-3 py-2.5 text-sm cursor-pointer flex items-center justify-between hover:bg-gray-700 transition-colors ${
                    result.ticker === value ? 'bg-blue-900/40 text-blue-300' : 'text-gray-200'
                  }`}
                >
                  <span>
                    <span className="font-mono">{result.ticker}</span>
                    <span className="text-gray-500 ml-2">{result.name}</span>
                    <span className="text-gray-600 ml-1 text-xs">({result.market})</span>
                  </span>
                  {result.ticker === value && (
                    <svg className="w-4 h-4 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                  )}
                </li>
              ))
            )}
          </ul>
        </div>
      )}
    </div>
  );
}