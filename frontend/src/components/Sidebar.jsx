import React from 'react';
import { LayoutGrid, Heart, Search, RotateCcw, Music2 } from 'lucide-react';
import useMusicStore from '../musicStore';

const Sidebar = () => {
  const { 
    view, setView, 
    likedSongs,
    searchQuery, setSearchQuery,
    selectedGenre, setGenre,
    selectedMood, setMood,
    selectedDuration, setDuration,
    resetFilters, fetchSongs
  } = useMusicStore();

  const handleReset = () => {
    resetFilters();
    fetchSongs();
  };

  return (
    // 🟢 FIXED: Added 'pb-32' to ensure bottom content clears the Music Player
    <aside className="w-72 h-screen bg-black/40 backdrop-blur-xl border-r border-white/5 flex flex-col fixed left-0 top-0 z-50 pb-32">
      
      {/* --- HEADER --- */}
      <div className="p-6 pb-2">
        <div className="flex items-center gap-3 px-2 mb-6">
          <div className="w-10 h-10 bg-accent rounded-xl flex items-center justify-center shadow-[0_0_20px_rgba(71,208,208,0.3)]">
            <Music2 className="text-black" size={22} />
          </div>
          <h1 className="text-xl font-heading font-bold text-white tracking-tight">MusicPro</h1>
        </div>

        {/* --- NAVIGATION --- */}
        <nav className="flex flex-col gap-2">
          <button 
            onClick={() => setView('home')}
            className={`flex items-center gap-4 px-4 py-3 rounded-xl transition-all group ${
              view === 'home' ? 'bg-accent/10 text-accent' : 'text-gray-400 hover:bg-white/5 hover:text-white'
            }`}
          >
            <LayoutGrid size={20} className={view === 'home' ? 'scale-110' : 'group-hover:scale-110 transition-transform'} />
            <span className="font-medium">Music Library</span>
          </button>

          <button 
            onClick={() => setView('liked')}
            className={`flex items-center justify-between px-4 py-3 rounded-xl transition-all group ${
              view === 'liked' ? 'bg-accent/10 text-accent' : 'text-gray-400 hover:bg-white/5 hover:text-white'
            }`}
          >
            <div className="flex items-center gap-4">
              <Heart 
                size={20} 
                fill={view === 'liked' ? "currentColor" : "none"} 
                className={view === 'liked' ? 'scale-110' : 'group-hover:scale-110 transition-transform'} 
              />
              <span className="font-medium">My Collection</span>
            </div>
            <span className={`text-[10px] px-2 py-0.5 rounded-full ${
              view === 'liked' ? 'bg-accent/20' : 'bg-white/10'
            }`}>
              {likedSongs?.length || 0}
            </span>
          </button>
        </nav>
      </div>

      {/* --- SCROLLABLE FILTERS --- */}
      <div className="flex-1 overflow-y-auto px-6 py-2 custom-scrollbar space-y-6">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-bold mb-4 px-2">Search</p>
          <div className="relative group">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-accent transition-colors" size={16} />
            <input 
              type="text"
              placeholder="Songs, Artists..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                if(view !== 'home') setView('home');
                fetchSongs();
              }}
              className="w-full bg-black border border-white/10 rounded-xl pl-11 pr-4 py-3 text-sm text-white placeholder:text-gray-600 focus:outline-none focus:ring-2 focus:ring-accent/50 transition-all"
            />
          </div>
        </div>

        <div className="flex flex-col gap-4">
          <p className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-bold px-2">Refine</p>

          {/* 🟢 FIXED: Dropdowns now have bg-black and text-white */}
          <select 
            value={selectedDuration}
            onChange={(e) => { setDuration(e.target.value); setView('home'); fetchSongs(); }}
            className="w-full bg-black text-gray-300 border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-accent/50 appearance-none cursor-pointer hover:bg-white/5"
          >
            <option value="all" className="bg-black text-white">All Durations</option>
            <option value="Short" className="bg-black text-white">Short (&lt; 3m)</option>
            <option value="Mid" className="bg-black text-white">Medium (3-5m)</option>
            <option value="Long" className="bg-black text-white">Long (&gt; 5m)</option>
          </select>

          <select 
            value={selectedGenre}
            onChange={(e) => { setGenre(e.target.value); setView('home'); fetchSongs(); }}
            className="w-full bg-black text-gray-300 border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-accent/50 appearance-none cursor-pointer hover:bg-white/5"
          >
            <option value="all" className="bg-black text-white">All Genres</option>
            <option value="Bollywood" className="bg-black text-white">Bollywood</option>
            <option value="Pop" className="bg-black text-white">Pop</option>
            <option value="Classical" className="bg-black text-white">Classical</option>
            <option value="Instrumental" className="bg-black text-white">Instrumental</option>
            <option value="Devotional" className="bg-black text-white">Devotional</option>
          </select>

          <select 
            value={selectedMood}
            onChange={(e) => { setMood(e.target.value); setView('home'); fetchSongs(); }}
            className="w-full bg-black text-gray-300 border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-accent/50 appearance-none cursor-pointer hover:bg-white/5"
          >
            <option value="all" className="bg-black text-white">All Moods</option>
            <option value="Happy" className="bg-black text-white">Happy</option>
            <option value="Sad" className="bg-black text-white">Sad</option>
            <option value="Romantic" className="bg-black text-white">Romantic</option>
            <option value="Calm" className="bg-black text-white">Calm</option>
            <option value="Slow" className="bg-black text-white">Slow</option>
          </select>
        </div>
      </div>

      {/* --- PINNED FOOTER (Reset Button) --- */}
      <div className="p-6 border-t border-white/5 mt-auto bg-black/40 backdrop-blur-md">
        <button 
          onClick={handleReset}
          className="flex items-center justify-center gap-2 w-full py-3 rounded-xl border border-dashed border-white/10 text-gray-500 hover:text-white hover:border-white/20 transition-all text-xs font-medium hover:bg-white/5"
        >
          <RotateCcw size={14} />
          Reset Defaults
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;