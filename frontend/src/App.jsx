import React, { useEffect, useRef, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import MusicPlayer from './components/MusicPlayer';
import SongCard from './components/SongCard';
// 🟢 FIXED: Added the missing import here
import FullScreenPlayer from './components/FullScreenPlayer'; 
import useMusicStore from './musicStore';
import { ArrowLeft } from 'lucide-react';

const App = () => {
  const { 
    songs, 
    fetchSongs, 
    isLoading, 
    view, 
    setView, 
    likedSongs,
    searchQuery, 
    selectedGenre, 
    selectedMood, 
    selectedDuration 
  } = useMusicStore();

  const observer = useRef();

  // 1. Sync Logic
  useEffect(() => {
    if (view !== 'home') return;
    const timeoutId = setTimeout(() => {
      fetchSongs();
    }, 300);
    return () => clearTimeout(timeoutId);
  }, [searchQuery, selectedGenre, selectedMood, selectedDuration, view, fetchSongs]);

  // 2. Pagination Logic
  const lastSongElementRef = useCallback(node => {
    if (isLoading || view !== 'home') return;
    if (observer.current) observer.current.disconnect();
    observer.current = new IntersectionObserver(entries => {
      if (entries[0].isIntersecting && songs?.length >= 50) {
        // Pagination logic hook
      }
    });
    if (node) observer.current.observe(node);
  }, [isLoading, songs, view]);

  const displaySongs = view === 'home' ? (songs || []) : (likedSongs || []);

  return (
    <div className="flex h-screen bg-[#070707] text-white overflow-hidden font-sans">
      <div className="w-72 h-full flex-shrink-0">
        <Sidebar />
      </div>

      <main className="flex-1 flex flex-col relative overflow-hidden bg-gradient-to-br from-[#0a0a0a] via-[#070707] to-black">
        
        {/* --- HEADER --- */}
        <div className="p-10 pb-6 flex justify-between items-end min-h-[160px]">
          <div className="animate-in fade-in slide-in-from-left duration-700">
            <h2 className="text-[10px] uppercase tracking-[0.5em] text-accent font-bold mb-3 opacity-80">
              {view === 'home' ? 'CURATED FOR YOU' : 'YOUR COLLECTION'}
            </h2>
            <h1 className="text-5xl font-heading font-bold tracking-tight">
              {view === 'home' ? 'The Masterpiece Montage' : 'Liked Songs'}
            </h1>
            <div className="h-1 w-20 bg-accent mt-4 rounded-full shadow-[0_0_15px_rgba(71,208,208,0.5)]"></div>
          </div>

          {/* BACK BUTTON */}
          {view === 'liked' && (
            <button 
              onClick={() => setView('home')}
              className="group flex items-center gap-2 px-6 py-2.5 rounded-full border border-white/10 text-xs font-bold uppercase tracking-widest text-gray-400 hover:text-white hover:bg-white/5 transition-all hover:border-white/30"
            >
              <ArrowLeft size={14} className="group-hover:-translate-x-1 transition-transform" />
              Back to Library
            </button>
          )}
        </div>

        {/* --- GRID --- */}
        <div className="flex-1 overflow-y-auto px-10 pb-40 custom-scrollbar scroll-smooth">
          {isLoading && displaySongs.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 gap-4">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-accent"></div>
              <p className="text-[10px] uppercase tracking-widest text-gray-500 font-bold">Loading Library...</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-8 pb-10">
              {displaySongs.map((song, index) => {
                const isLast = index === displaySongs.length - 1;
                return (
                  <div key={`${song.id}-${index}`} ref={isLast ? lastSongElementRef : null}>
                    <SongCard song={song} />
                  </div>
                );
              })}
            </div>
          )}
          
          {displaySongs.length === 0 && !isLoading && (
            <div className="flex flex-col items-center justify-center h-64 text-center">
              <p className="text-gray-600 uppercase tracking-widest text-xs font-bold opacity-50 mb-4">
                {view === 'home' ? 'No songs match these filters' : 'Your collection is empty'}
              </p>
              {view === 'liked' && (
                <button onClick={() => setView('home')} className="text-accent text-sm hover:underline">
                  Go find some music
                </button>
              )}
            </div>
          )}
        </div>

        {/* 🟢 FLOATING LAYERS */}
        <MusicPlayer />
        <FullScreenPlayer /> 
      </main>
    </div>
  );
};

export default App;