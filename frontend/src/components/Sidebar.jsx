import React from 'react';
import { motion } from 'framer-motion';
import { LayoutGrid, Heart, Search, RotateCcw, Music2, ChevronDown } from 'lucide-react';
import useMusicStore from '../musicStore';

const Sidebar = () => {
  const { 
    view, setView, 
    likedSongs,
    searchQuery, setSearchQuery,
    selectedGenre, setGenre,
    selectedMood, setMood,
    selectedDuration, setDuration,
    selectedLanguage, setLanguage,
    resetFilters, fetchSongs
  } = useMusicStore();

  const handleReset = () => {
    resetFilters();
    fetchSongs();
  };

  const handleFilterChange = (setter, value) => {
    setter(value);
    if (view !== 'home') setView('home');
  };

  return (
    <aside className="w-72 h-screen bg-black/40 backdrop-blur-xl border-r border-white/5 flex flex-col fixed left-0 top-0 z-50 pb-32">
      {/* HEADER */}
      <div className="p-6 pb-2">
        <motion.div 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="flex items-center gap-3 px-2 mb-6"
        >
          <div className="w-10 h-10 bg-emerald-500 rounded-xl flex items-center justify-center shadow-[0_0_20px_rgba(16,185,129,0.3)]">
            <Music2 className="text-black" size={22} />
          </div>
          <h1 className="text-xl font-bold text-white tracking-tight">VibeStream</h1>
        </motion.div>

        <nav className="flex flex-col gap-2">
          <NavItem 
            active={view === 'home'} 
            onClick={() => setView('home')} 
            icon={<LayoutGrid size={20} />} 
            label="Music Library" 
          />
          <NavItem 
            active={view === 'liked'} 
            onClick={() => setView('liked')} 
            icon={<Heart size={20} fill={view === 'liked' ? "currentColor" : "none"} />} 
            label="My Collection" 
            badge={likedSongs?.length || 0}
          />
        </nav>
      </div>

      {/* FILTERS SECTION */}
      <div className="flex-1 overflow-y-auto px-6 py-2 custom-scrollbar space-y-6">
        <motion.div 
          initial={{ opacity: 0 }} 
          animate={{ opacity: 1 }} 
          transition={{ delay: 0.2 }}
        >
          <p className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-bold mb-4 px-2">Search</p>
          <div className="relative group">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500 group-focus-within:text-emerald-500 transition-colors" size={16} />
            <input 
              type="text"
              placeholder="Songs, Artists..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-zinc-900 border border-white/10 rounded-xl pl-11 pr-4 py-3 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all"
            />
          </div>
        </motion.div>

        <motion.div 
          initial={{ opacity: 0 }} 
          animate={{ opacity: 1 }} 
          transition={{ delay: 0.3 }}
          className="flex flex-col gap-4"
        >
          <p className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-bold px-2">Refine</p>

          <FilterSelect 
            label="Genre"
            value={selectedGenre}
            onChange={(e) => handleFilterChange(setGenre, e.target.value)}
            options={[
              {v: "all", t: "All Genres"},
              {v: "Bollywood", t: "Bollywood"},
              {v: "Pop", t: "Pop"},
              {v: "Lo-Fi", t: "Lo-Fi"},
              {v: "Rock", t: "Rock"},
              {v: "Electronic", t: "Electronic"}
            ]}
          />

          {/* 🟢 LOGICAL FIX: MATCHED TO DATABASE BUCKETS */}
          <FilterSelect 
            label="Language"
            value={selectedLanguage}
            onChange={(e) => handleFilterChange(setLanguage, e.target.value)}
            options={[
              {v: "all", t: "All Languages"},
              {v: "English", t: "English"},
              {v: "Hindi", t: "Hindi"},
              {v: "Bengali", t: "Bengali"},
              {v: "Punjabi", t: "Punjabi"},
              {v: "Others", t: "Others (K-Pop, Tamil, etc.)"} 
            ]}
          />

          <FilterSelect 
            label="Duration"
            value={selectedDuration}
            onChange={(e) => handleFilterChange(setDuration, e.target.value)}
            options={[
              {v: "all", t: "All Durations"},
              {v: "Short", t: "Short (< 3m)"},
              {v: "Mid", t: "Medium (3-5m)"},
              {v: "Long", t: "Long (> 5m)"}
            ]}
          />

          <FilterSelect 
            label="Mood"
            value={selectedMood}
            onChange={(e) => handleFilterChange(setMood, e.target.value)}
            options={[
              {v: "all", t: "All Moods"},
              {v: "Happy", t: "Happy"},
              {v: "Sad", t: "Sad"},
              {v: "Chill", t: "Chill"},
              {v: "Energetic", t: "Energetic"},
              {v: "Romantic", t: "Romantic"},
              {v: "Party", t: "Party"}
            ]}
          />
        </motion.div>
      </div>

      {/* FOOTER */}
      <div className="p-6 border-t border-white/5 mt-auto bg-black/40 backdrop-blur-md">
        <motion.button 
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={handleReset}
          className="flex items-center justify-center gap-2 w-full py-3 rounded-xl border border-dashed border-white/10 text-zinc-500 hover:text-white hover:border-white/20 transition-all text-xs font-medium hover:bg-white/5"
        >
          <RotateCcw size={14} />
          Reset Defaults
        </motion.button>
      </div>
    </aside>
  );
};

// 🟢 Reusable Nav Item
const NavItem = ({ active, onClick, icon, label, badge }) => (
  <motion.button 
    whileHover={{ x: 5 }}
    onClick={onClick}
    className={`flex items-center justify-between w-full px-4 py-3 rounded-xl transition-all group ${
      active ? 'bg-emerald-500/10 text-emerald-500' : 'text-zinc-400 hover:bg-white/5 hover:text-white'
    }`}
  >
    <div className="flex items-center gap-4">
      <span className={active ? 'scale-110' : 'group-hover:scale-110 transition-transform'}>
        {icon}
      </span>
      <span className="font-medium">{label}</span>
    </div>
    {badge !== undefined && (
      <span className={`text-[10px] px-2 py-0.5 rounded-full ${active ? 'bg-emerald-500/20' : 'bg-white/10'}`}>
        {badge}
      </span>
    )}
  </motion.button>
);

// 🟢 Reusable Filter Select with Black Background Logic
const FilterSelect = ({ value, onChange, options }) => (
  <div className="relative">
    <select 
      value={value} 
      onChange={onChange} 
      className="w-full bg-zinc-900 text-white border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50 appearance-none cursor-pointer hover:bg-zinc-800 transition-all"
    >
      {options.map(opt => (
        <option key={opt.v} value={opt.v} className="bg-zinc-900 text-white">
          {opt.t}
        </option>
      ))}
    </select>
    <ChevronDown size={14} className="absolute right-4 top-1/2 -translate-y-1/2 text-zinc-500 pointer-events-none" />
  </div>
);

export default Sidebar;