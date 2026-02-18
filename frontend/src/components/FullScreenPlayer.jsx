import React, { useEffect, useState, useRef } from 'react';
import { X, Play, Pause, SkipBack, SkipForward, Heart, Mic2, Info, Sparkles, Volume2, VolumeX } from 'lucide-react';
import useMusicStore from '../musicStore';

const FullScreenPlayer = () => {
  const {
    currentSong, isPlaying, pauseSong, resumeSong, playNext, playPrev,
    toggleLike, likedSongs, isPlayerOpen, setPlayerOpen, currentTime, setCurrentTime,
    // 🟢 GLOBAL VOLUME
    volume, setVolume, toggleMute, isMuted
  } = useMusicStore();

  const [lyrics, setLyrics] = useState([]);
  const [activeLine, setActiveLine] = useState(0);
  const [wikiInfo, setWikiInfo] = useState("");
  const [loadingLyrics, setLoadingLyrics] = useState(false);
  const lyricsContainerRef = useRef(null);

  const isLiked = currentSong && likedSongs.some(s => s.id === currentSong.id);

  // --- LYRICS & INFO FETCHING ---
  // ... inside your useEffect in FullScreenPlayer.jsx ...

  useEffect(() => {
    if (!currentSong) return;

    const fetchData = async () => {
      setLoadingLyrics(true);
      setLyrics([]);
      setWikiInfo("");

      // Data Cleaning
      const cleanTitle = currentSong.title ? currentSong.title.split('(')[0].split('-')[0].trim() : "";
      const cleanArtist = currentSong.artist ? currentSong.artist.split(',')[0].trim() : "";

      // 🟢 1. FETCH LYRICS (Via Backend Proxy)
      try {
        const res = await fetch(`http://localhost:8000/proxy/lyrics?artist=${encodeURIComponent(cleanArtist)}&title=${encodeURIComponent(cleanTitle)}`);
        const data = await res.json();
        if (data.lyrics) {
          setLyrics(data.lyrics.split('\n').filter(line => line.trim() !== ''));
        } else {
          setLyrics(["(Instrumental or Lyrics not found)", "Just feel the vibe..."]);
        }
      } catch (e) {
        console.error("Lyrics fetch error:", e);
        setLyrics(["(Lyrics unavailable)", "Enjoy the music!"]);
      }

      // 🟢 2. FETCH WIKI INFO (Via Backend Proxy with Fallback)
      try {
        // We try specific song first, but send Artist as fallback
        const songQuery = `${cleanTitle}_(song)`;
        const res = await fetch(`http://localhost:8000/proxy/wiki?query=${encodeURIComponent(songQuery)}&fallback=${encodeURIComponent(cleanArtist)}`);
        const data = await res.json();

        if (data.extract) {
          setWikiInfo(data.extract);
        } else {
          setWikiInfo(`Enjoy this track by ${cleanArtist}.`);
        }
      } catch (e) {
        console.error("Wiki fetch error:", e);
      }

      setLoadingLyrics(false);
    };

    fetchData();
  }, [currentSong]);

  // ... rest of component

  // --- AUTO SCROLL LYRICS ---
  useEffect(() => {
    if (!currentSong || lyrics.length === 0 || !isPlaying) return;
    const duration = currentSong.duration || 240;
    const progress = currentTime / duration;
    const estimatedLine = Math.floor(progress * lyrics.length);
    if (estimatedLine !== activeLine) {
      setActiveLine(estimatedLine);
      if (lyricsContainerRef.current) {
        lyricsContainerRef.current.children[estimatedLine]?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }, [currentTime, lyrics.length, currentSong, isPlaying]);

  const formatTime = (time) => {
    // 🟢 LOGICAL FIX: Handle null, undefined, strings, and NaN
    const totalSeconds = parseFloat(time);
    if (isNaN(totalSeconds) || totalSeconds <= 0) return "0:00";

    const minutes = Math.floor(totalSeconds / 60);
    const seconds = Math.floor(totalSeconds % 60);
    return `${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
  };
  if (!isPlayerOpen || !currentSong) return null;

  // Safe Duration (Prevents NaN)
  const duration = currentSong.duration || 240;

  return (
    // Fixed container with high z-index
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/90 md:ml-72 transition-all duration-300">
      {/* Background Blur */}
      <div className="absolute inset-0 bg-cover bg-center opacity-30 blur-[100px] scale-125 transition-all duration-1000" style={{ backgroundImage: `url(${currentSong.album_art || currentSong.cover_url || "https://placehold.co/300"})` }} />
      <div className="absolute inset-0 bg-black/60" />

      {/* Main Card */}
      <div className="relative w-full max-w-6xl h-[85vh] bg-white/[0.02] backdrop-blur-3xl border border-white/10 rounded-[40px] shadow-2xl overflow-hidden flex flex-col md:flex-row animate-in fade-in zoom-in-95 duration-500">

        {/* Close Button */}
        <button onClick={() => setPlayerOpen(false)} className="absolute top-8 right-8 p-3 bg-white/5 hover:bg-white/10 border border-white/5 rounded-full text-zinc-300 hover:text-white z-50 transition-all backdrop-blur-md">
          <X size={20} />
        </button>

        {/* LEFT SIDE: Cover & Controls */}
        <div className="w-full md:w-1/2 p-8 md:p-12 flex flex-col justify-center relative border-r border-white/5">
          {/* Cover Art */}
          <div className="aspect-square w-full max-w-[320px] md:max-w-[380px] mx-auto rounded-3xl overflow-hidden shadow-[0_30px_60px_rgba(0,0,0,0.6)] ring-1 ring-white/10 relative group">
            <img
              src={currentSong.album_art || currentSong.cover_url || "https://placehold.co/300"}
              alt="Album Art"
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-1000"
            />
          </div>

          <div className="mt-8 md:mt-10 space-y-6">
            <div className="text-center space-y-2">
              <h1 className="text-2xl md:text-3xl font-bold text-white tracking-tight line-clamp-2">{currentSong.title}</h1>
              <p className="text-lg md:text-xl text-zinc-400 font-light tracking-wide">{currentSong.artist}</p>
            </div>

            {/* PROGRESS BAR */}
            {/* PROGRESS BAR */}
            {/* PROGRESS BAR */}
            <div className="w-full max-w-md mx-auto flex items-center gap-3 text-xs text-zinc-400 font-mono">
              <span className="w-10 text-right">{formatTime(currentTime)}</span>
              <div className="relative flex-1 h-1.5 group cursor-pointer">
                {/* 🟢 LOGICAL FIX: Define a stable numeric duration for calculation */}
                {(() => {
                  const activeDuration = currentSong.duration_seconds || duration || 0;
                  const progress = activeDuration > 0 ? Math.min((currentTime / activeDuration) * 100, 100) : 0;

                  return (
                    <>
                      <input
                        type="range"
                        min="0"
                        max={activeDuration > 0 ? activeDuration : 100}
                        value={currentTime}
                        onChange={(e) => setCurrentTime(parseFloat(e.target.value))}
                        className="absolute w-full h-full opacity-0 z-20 cursor-pointer"
                      />
                      <div className="absolute w-full h-1.5 bg-white/10 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.8)] transition-all duration-100 relative"
                          style={{ width: `${progress}%` }}
                        ></div>
                      </div>
                    </>
                  );
                })()}
              </div>
              <span className="w-10">{formatTime(currentSong.duration_seconds || duration)}</span>
            </div>

            {/* CONTROLS */}
            <div className="flex items-center justify-center gap-6 md:gap-10">
              <button onClick={playPrev} className="text-zinc-400 hover:text-white hover:scale-110 active:scale-95 transition-all"><SkipBack size={32} strokeWidth={1.5} /></button>
              <button onClick={isPlaying ? pauseSong : resumeSong} className="w-16 h-16 md:w-20 md:h-20 bg-white text-black rounded-full flex items-center justify-center hover:scale-105 transition-all shadow-[0_0_30px_rgba(255,255,255,0.3)]">
                {isPlaying ? <Pause size={32} fill="currentColor" /> : <Play size={32} fill="currentColor" className="ml-1" />}
              </button>
              <button onClick={playNext} className="text-zinc-400 hover:text-white hover:scale-110 active:scale-95 transition-all"><SkipForward size={32} strokeWidth={1.5} /></button>
            </div>

            {/* VOLUME & ACTIONS */}
            <div className="flex justify-between items-center px-4 md:px-8 mt-4">
              <button onClick={() => toggleLike(currentSong)} className={`p-3 rounded-full bg-white/5 hover:bg-white/10 transition-all ${isLiked ? 'text-emerald-500' : 'text-zinc-400 hover:text-white'}`}>
                <Heart size={20} fill={isLiked ? "currentColor" : "none"} />
              </button>

              {/* VOLUME SLIDER */}
              <div className="flex items-center gap-3 w-32 group">
                <button onClick={toggleMute}>
                  {isMuted || volume === 0 ? <VolumeX size={18} className="text-zinc-400" /> : <Volume2 size={18} className="text-zinc-400 group-hover:text-white" />}
                </button>
                <div className="relative flex-1 h-1 bg-white/10 rounded-full cursor-pointer">
                  <input
                    type="range" min="0" max="1" step="0.01"
                    value={isMuted ? 0 : volume}
                    onChange={(e) => setVolume(parseFloat(e.target.value))}
                    className="absolute w-full h-full opacity-0 z-20 cursor-pointer"
                  />
                  <div
                    className="absolute h-full bg-zinc-500 rounded-full group-hover:bg-emerald-500 transition-colors"
                    style={{ width: `${(isMuted ? 0 : volume) * 100}%` }}
                  ></div>
                </div>
              </div>

              <button className="p-3 rounded-full bg-white/5 hover:bg-white/10 transition-all text-zinc-400 hover:text-white">
                <Info size={20} />
              </button>
            </div>
          </div>
        </div>

        {/* RIGHT SIDE: LYRICS & INFO */}
        <div className="w-full md:w-1/2 flex flex-col relative bg-black/20">
          <div className="p-8 pb-4 border-b border-white/5">
            <div className="flex items-center gap-2 text-emerald-500 text-xs font-bold uppercase tracking-[0.2em] mb-3 opacity-80">
              <Sparkles size={14} /> Behind the Music
            </div>
            <p className="text-zinc-300 text-sm leading-relaxed font-light line-clamp-3">
              {wikiInfo || currentSong.description || "The story of this song is being written by you, right now."}
            </p>
          </div>
          <div className="flex-1 overflow-hidden relative p-8">
            <div className="flex items-center justify-between mb-6 sticky top-0 z-10">
              <h3 className="text-white text-2xl font-bold flex items-center gap-3"><Mic2 className="text-emerald-500" /> Lyrics</h3>
              {activeLine > 0 && <span className="text-[10px] font-bold bg-emerald-500/20 text-emerald-500 px-3 py-1 rounded-full animate-pulse">On Air</span>}
            </div>
            <div ref={lyricsContainerRef} className="h-full overflow-y-auto custom-scrollbar space-y-8 pb-40 text-center mask-image-gradient">
              {loadingLyrics ? <div className="text-white/30 animate-pulse mt-20">Fetching lyrics...</div> :
                lyrics.map((line, index) => (
                  <p key={index} className={`text-2xl font-bold transition-all duration-500 cursor-pointer ${index === activeLine ? 'text-white scale-110 drop-shadow-[0_0_10px_rgba(255,255,255,0.5)]' : 'text-white/20 blur-[1px]'}`}
                    onClick={() => setCurrentTime((index / lyrics.length) * duration)}>
                    {line}
                  </p>
                ))
              }
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FullScreenPlayer;