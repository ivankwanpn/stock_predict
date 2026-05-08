import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api/client';
import { useLang } from '../i18n/LanguageContext';
import toast from 'react-hot-toast';
import type { WatchlistItem, StockSearchResult } from '../types';

interface WatchlistTableProps {
  onSelect: (ticker: string) => void;
}

export default function WatchlistTable({ onSelect }: WatchlistTableProps) {
  const { t } = useLang();
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<StockSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchWatchlist = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getWatchlist();
      setItems(data as WatchlistItem[]);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchWatchlist();
  }, [fetchWatchlist]);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Debounced search
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const q = e.target.value;
    setSearchQuery(q);

    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (q.trim().length < 1) {
      setSearchResults([]);
      setShowDropdown(false);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      setSearching(true);
      try {
        const results = await api.searchStocks(q);
        setSearchResults(results as StockSearchResult[]);
        setShowDropdown(true);
      } catch {
        toast.error(t('stockNotFound'));
        setSearchResults([]);
      } finally {
        setSearching(false);
      }
    }, 300);
  };

  const handleAddStock = async (ticker: string) => {
    try {
      await api.addWatchlist(ticker);
      toast.success(t('stockAdded'));
      setSearchQuery('');
      setSearchResults([]);
      setShowDropdown(false);
      await fetchWatchlist();
    } catch (e: any) {
      if (e.message?.includes('already')) {
        toast.error(t('stockAlreadyExists'));
      } else {
        toast.error(t('addStockFailed'));
      }
    }
  };

  const handleRemoveStock = async (e: React.MouseEvent, ticker: string) => {
    e.stopPropagation();
    try {
      await api.removeWatchlist(ticker);
      toast.success(t('stockRemoved'));
      await fetchWatchlist();
    } catch {
      toast.error(t('removeStockFailed'));
    }
  };

  if (loading && items.length === 0) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <div className="flex items-center justify-center h-32">
          <div className="animate-spin w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full" />
          <span className="ml-3 text-gray-400 text-sm">{t('loadingWatchlist')}</span>
        </div>
      </div>
    );
  }

  if (error && items.length === 0) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <div className="flex flex-col items-center justify-center gap-4 h-32">
          <p className="text-gray-500 text-sm">{t('watchlistUnavailable')}</p>
          <button
            onClick={fetchWatchlist}
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed px-4 py-1.5 rounded-lg text-xs font-medium transition-colors"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <div className="animate-spin w-3 h-3 border-2 border-white border-t-transparent rounded-full" />
                {t('analyzing')}
              </span>
            ) : (
              t('retry')
            )}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      {/* Header with search */}
      <div className="px-5 py-3 border-b border-gray-800">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">{t('watchlistTitle')}</h2>
        </div>

        {/* Search bar */}
        <div ref={searchRef} className="relative">
          <div className="relative">
            <input
              type="text"
              value={searchQuery}
              onChange={handleSearchChange}
              onFocus={() => searchQuery.trim().length >= 1 && setShowDropdown(true)}
              placeholder={t('searchWatchlist')}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors"
            />
            {searching && (
              <div className="absolute right-3 top-1/2 -translate-y-1/2">
                <div className="animate-spin w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full" />
              </div>
            )}
          </div>

          {/* Search results dropdown */}
          {showDropdown && searchResults.length > 0 && (
            <div className="absolute z-10 mt-1 w-full bg-gray-800 border border-gray-700 rounded-lg shadow-xl max-h-60 overflow-y-auto">
              {searchResults.map((result) => (
                <div
                  key={result.ticker}
                  className="flex items-center justify-between px-3 py-2 hover:bg-gray-700 cursor-pointer transition-colors"
                >
                  <div
                    className="flex-1"
                    onClick={() => handleAddStock(result.ticker)}
                  >
                    <span className="font-mono text-gray-200 text-sm">{result.ticker}</span>
                    <span className="ml-2 text-gray-400 text-sm">{result.name}</span>
                    <span className="ml-2 text-gray-500 text-xs">({result.market})</span>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleAddStock(result.ticker);
                    }}
                    className="ml-2 px-2 py-1 bg-blue-600 hover:bg-blue-700 rounded text-xs text-white font-medium transition-colors"
                  >
                    {t('addStock')}
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* No results */}
          {showDropdown && searchQuery.trim().length >= 1 && searchResults.length === 0 && !searching && (
            <div className="absolute z-10 mt-1 w-full bg-gray-800 border border-gray-700 rounded-lg shadow-xl px-3 py-4">
              <p className="text-gray-500 text-sm text-center">{t('noResults')}</p>
            </div>
          )}
        </div>
      </div>

      {/* Table or empty state */}
      {items.length === 0 ? (
        <div className="px-5 py-8 flex flex-col items-center justify-center">
          <div className="text-center">
            <p className="text-gray-400 text-sm mb-2">{t('emptyWatchlist')}</p>
            <p className="text-gray-500 text-xs">{t('emptyWatchlistHint')}</p>
          </div>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-gray-500 text-xs uppercase tracking-wider">
                <th className="text-left px-5 py-3 font-medium">{t('tickerCol')}</th>
                <th className="text-left px-5 py-3 font-medium">{t('nameCol')}</th>
                <th className="text-right px-5 py-3 font-medium">{t('priceCol')}</th>
                <th className="text-right px-5 py-3 font-medium">{t('changeCol')}</th>
                <th className="w-10"></th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const chg = item.change_pct ?? 0;
                const isPositive = chg >= 0;
                return (
                  <tr
                    key={item.ticker}
                    onClick={() => onSelect(item.ticker)}
                    className="border-b border-gray-800/50 hover:bg-gray-800/50 cursor-pointer transition-colors last:border-b-0"
                  >
                    <td className="px-5 py-3 font-mono text-gray-200 font-medium">{item.ticker}</td>
                    <td className="px-5 py-3 text-gray-400">{item.name || item.ticker}</td>
                    <td className="px-5 py-3 text-right font-mono text-gray-200">
                      {item.latest_price.toFixed(2)}
                    </td>
                    <td className={`px-5 py-3 text-right font-mono ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                      <span className="flex items-center justify-end gap-1">
                        {isPositive ? (
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7 7 7" />
                          </svg>
                        ) : (
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7-7-7" />
                          </svg>
                        )}
                        {chg >= 0 ? '+' : ''}{chg.toFixed(2)}%
                      </span>
                    </td>
                    <td className="px-3 py-3">
                      <button
                        onClick={(e) => handleRemoveStock(e, item.ticker)}
                        className="w-6 h-6 flex items-center justify-center rounded hover:bg-gray-700 text-gray-500 hover:text-red-400 transition-colors"
                        title={t('removeStock')}
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}