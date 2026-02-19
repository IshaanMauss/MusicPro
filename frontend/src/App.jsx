import React, { useEffect, useRef, useState, useMemo } from 'react';
import Sidebar from './components/Sidebar';
import SongCard from './components/SongCard';
import MusicPlayer from './components/MusicPlayer';
import FullScreenPlayer from './components/FullScreenPlayer';
import Login from './components/Login'; // 🟢 Premium Login component
import useMusicStore from './musicStore';
import { Menu, ArrowUp, ArrowLeft } from 'lucide-react';
import { Toaster } from 'react-hot-toast'; // 🟢 Premium Toasts

const App = () => {
  const {
    user, // 🟢 Auth State for the Logic Gate
    songs,
    isLoading,
    fetchSongs,
    currentSong,
    view,
    setView,
    likedSongs,
    searchQuery,
    hasMore
  } = useMusicStore();

  const [showTopBtn, setShowTopBtn] = useState(false);
  const loaderRef = useRef(null);
  const mainRef = useRef(null);

  // 1. Initial Load (Triggered only if user is authenticated)
  useEffect(() => {
    if (user) {
      fetchSongs(false);
    }
  }, [user, fetchSongs]); // fetchSongs included to satisfy dependency rules

  // 2. Infinite Scroll Observer (Retained for Music Library)
  useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      const target = entries[0];
      if (target.isIntersecting && hasMore && !isLoading && view === 'home') {
        fetchSongs(true);
      }
    }, {
      root: null,
      rootMargin: '100px',
      threshold: 0.1
    });

    if (loaderRef.current) observer.observe(loaderRef.current);
    return () => {
      if (loaderRef.current) observer.unobserve(loaderRef.current);
    }
  }, [hasMore, isLoading, view, fetchSongs]); //

  // 3. Scroll Listener (For Top Button)
  const handleScroll = (e) => {
    if (e.target.scrollTop > 500) setShowTopBtn(true);
    else setShowTopBtn(false);
  };

  const scrollToTop = () => {
    if (mainRef.current) mainRef.current.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // 4. Memoized Filter Engine (Retained for performance)
  const filteredSongs = useMemo(() => {
    const displaySongs = view === 'liked' ? likedSongs : songs;
    if (!searchQuery) return displaySongs;

    const query = searchQuery.toLowerCase();
    return displaySongs.filter((song) => {
      const title = song.title ? song.title.toLowerCase() : "";
      const artist = song.artist ? song.artist.toLowerCase() : "";
      return title.includes(query) || artist.includes(query);
    });
  }, [songs, likedSongs, view, searchQuery]); //

  // 🛡️ 100% LOGIC GATE: Show Login if no user is authenticated
  if (!user) {
    return (
      <>
        <Toaster position="top-center" reverseOrder={false} />
        <Login />
      </>
    );
  }

  return (
    <div className="flex h-screen bg-black text-white overflow-hidden font-sans">
      {/* Premium Toast Notifications Container */}
      <Toaster position="top-center" reverseOrder={false} />

      <div className="hidden md:block z-40">
        <Sidebar />
      </div>

      <div className="flex-1 flex flex-col h-full relative md:pl-72 transition-all duration-300">

        {/* Mobile Header */}
        <div className="md:hidden p-4 flex items-center justify-between bg-black/50 backdrop-blur-md sticky top-0 z-30">
          <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-cyan-500">
            VibeStream
          </h1>
          <button className="p-2 text-zinc-400">
            <Menu size={24} />
          </button>
        </div>

        <main
          ref={mainRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto p-4 md:p-8 pb-32 custom-scrollbar relative scroll-smooth"
        >
          {/* HEADER */}
          <header className="mb-8 flex items-end justify-between">
            <div>
              <h1 className="text-3xl md:text-4xl font-bold mb-2 tracking-tight">
                {view === 'liked' ? 'Liked Songs' : 'Discover'}
              </h1>
              <p className="text-zinc-400">
                {view === 'liked' ? 'Your personal collection' : `Exploring Library (${filteredSongs.length} loaded)`}
              </p>
            </div>

            {view === 'liked' && (
              <button
                onClick={() => setView('home')}
                className="flex items-center gap-2 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 rounded-full text-sm font-medium transition-colors"
              >
                <ArrowLeft size={16} /> Back to Library
              </button>
            )}
          </header>

          {/* SONG GRID (Retained with unique key fix) */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
            {filteredSongs.map((song, index) => (
              <SongCard
                key={`${song.id}-${index}`}
                song={song}
              />
            ))}
          </div>

          {/* Loading Sentinel (Retained for Infinite Scroll) */}
          {view === 'home' && (
            <div ref={loaderRef} className="h-24 flex items-center justify-center mt-8 w-full">
              {isLoading && (
                <div className="flex flex-col items-center gap-2">
                  <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
                  <span className="text-xs text-zinc-500">Loading more vibes...</span>
                </div>
              )}
              {!hasMore && filteredSongs.length > 0 && (
                <span className="text-zinc-600 text-sm font-medium">You've reached the end! 🎵</span>
              )}
            </div>
          )}

          {!isLoading && filteredSongs.length === 0 && (
            <div className="text-center text-zinc-500 mt-20">
              <p>No songs found.</p>
            </div>
          )}
        </main>

        {/* Floating Scroll to Top Button */}
        <button
          onClick={scrollToTop}
          className={`absolute bottom-24 right-8 p-3 bg-emerald-500 text-black rounded-full shadow-[0_0_20px_rgba(16,185,129,0.4)] transition-all duration-300 z-40 hover:scale-110 active:scale-95 ${showTopBtn ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10 pointer-events-none'}`}
        >
          <ArrowUp size={24} />
        </button>

        {/* Playback Controls */}
        {currentSong && (
          <>
            <MusicPlayer />
            <FullScreenPlayer />
          </>
        )}
      </div>
    </div>
  );
};

export default App;