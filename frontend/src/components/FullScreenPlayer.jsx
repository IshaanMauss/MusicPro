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

  // ... (Data Fetching and Auto-Scroll Hooks remain same as previous step) ...
  // [Copy the useEffects for Fetch Data and Auto-Scroll from the previous message here]
  // For brevity, I am keeping the structure focused on the volume changes.
  
  useEffect(() => {
    if (!currentSong) return; 
    const fetchData = async () => {
      setLoadingLyrics(true);
      setLyrics([]);
      setWikiInfo("");
      const cleanTitle = currentSong.title.split('(')[0].split('-')[0].trim();
      const cleanArtist = currentSong.artist.split(',')[0].trim();
      try {
        const res = await fetch(`https://api.lyrics.ovh/v1/${cleanArtist}/${cleanTitle}`);
        const data = await res.json();
        if (data.lyrics) setLyrics(data.lyrics.split('\n').filter(line => line.trim() !== ''));
        else setLyrics(["(Instrumental or Lyrics not found)", "Just feel the vibe..."]);
      } catch (e) { setLyrics(["(Lyrics unavailable offline)", "Enjoy the music!"]); }
      try {
        const wikiRes = await fetch(`https://en.wikipedia.org/api/rest_v1/page/summary/${cleanTitle}_(song)`);
        if (wikiRes.ok) { const d = await wikiRes.json(); setWikiInfo(d.extract); }
        else {
           const aRes = await fetch(`https://en.wikipedia.org/api/rest_v1/page/summary/${cleanArtist}`);
           if (aRes.ok) { const d = await aRes.json(); setWikiInfo(`Artist Info: ${d.extract}`); }
        }
      } catch (e) {}
      setLoadingLyrics(false);
    };
    fetchData();
  }, [currentSong]);

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
    if (!time) return "0:00";
    const mins = Math.floor(time / 60);
    const secs = Math.floor(time % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (!isPlayerOpen || !currentSong) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center ml-72"> 
      <div className="absolute inset-0 bg-cover bg-center opacity-30 blur-[100px] scale-125 transition-all duration-1000" style={{ backgroundImage: `url(${currentSong.cover_url})` }} />
      <div className="absolute inset-0 bg-black/60" />

      <div className="relative w-full max-w-6xl h-[85vh] bg-white/[0.02] backdrop-blur-3xl border border-white/10 rounded-[40px] shadow-2xl overflow-hidden flex flex-col md:flex-row animate-in fade-in zoom-in-95 duration-500">
        
        <button onClick={() => setPlayerOpen(false)} className="absolute top-8 right-8 p-3 bg-white/5 hover:bg-white/10 border border-white/5 rounded-full text-gray-300 hover:text-white z-50 transition-all backdrop-blur-md">
          <X size={20} />
        </button>

        {/* LEFT SIDE */}
        <div className="w-full md:w-1/2 p-12 flex flex-col justify-center relative border-r border-white/5">
          <div className="aspect-square w-full max-w-[380px] mx-auto rounded-3xl overflow-hidden shadow-[0_30px_60px_rgba(0,0,0,0.6)] ring-1 ring-white/10 relative group">
            <img src={currentSong.cover_url} alt="Album Art" className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-1000" />
          </div>

          <div className="mt-10 space-y-6">
            <div className="text-center space-y-2">
              <h1 className="text-3xl font-heading font-bold text-white tracking-tight line-clamp-2">{currentSong.title}</h1>
              <p className="text-xl text-gray-400 font-light tracking-wide">{currentSong.artist}</p>
            </div>

            {/* PROGRESS BAR */}
            <div className="w-full max-w-md mx-auto flex items-center gap-3 text-xs text-gray-400 font-mono">
              <span className="w-10 text-right">{formatTime(currentTime)}</span>
              <div className="relative flex-1 h-1.5 group cursor-pointer">
                <input 
                  type="range" min="0" max={currentSong.duration || 240} value={currentTime} 
                  onChange={(e) => setCurrentTime(parseFloat(e.target.value))}
                  className="absolute w-full h-full opacity-0 z-20 cursor-pointer"
                />
                <div className="absolute w-full h-1.5 bg-white/10 rounded-full overflow-hidden">
                  <div className="h-full bg-accent shadow-[0_0_10px_rgba(71,208,208,0.8)] relative" style={{ width: `${(currentTime / (currentSong.duration || 1)) * 100}%` }}></div>
                </div>
              </div>
              <span className="w-10">{formatTime(currentSong.duration || 0)}</span>
            </div>

            {/* CONTROLS */}
            <div className="flex items-center justify-center gap-10">
               <button onClick={playPrev} className="text-gray-400 hover:text-white hover:scale-110 active:scale-95 transition-all"><SkipBack size={32} strokeWidth={1.5} /></button>
               <button onClick={isPlaying ? pauseSong : resumeSong} className="w-20 h-20 bg-white text-black rounded-full flex items-center justify-center hover:scale-105 transition-all shadow-[0_0_30px_rgba(255,255,255,0.3)]">
                 {isPlaying ? <Pause size={36} fill="currentColor" /> : <Play size={36} fill="currentColor" className="ml-1" />}
               </button>
               <button onClick={playNext} className="text-gray-400 hover:text-white hover:scale-110 active:scale-95 transition-all"><SkipForward size={32} strokeWidth={1.5} /></button>
            </div>
            
             {/* 🟢 GLOBAL VOLUME & ACTIONS */}
             <div className="flex justify-between items-center px-8 mt-4">
                <button onClick={() => toggleLike(currentSong)} className={`p-3 rounded-full bg-white/5 hover:bg-white/10 transition-all ${isLiked ? 'text-accent' : 'text-gray-400 hover:text-white'}`}>
                  <Heart size={20} fill={isLiked ? "currentColor" : "none"} />
                </button>

                {/* 🟢 SYNCED SLIDER */}
                <div className="flex items-center gap-3 w-32 group">
                   <button onClick={toggleMute}>
                      {isMuted || volume === 0 ? <VolumeX size={18} className="text-gray-400" /> : <Volume2 size={18} className="text-gray-400 group-hover:text-white" />}
                   </button>
                   <div className="relative flex-1 h-1 bg-white/10 rounded-full cursor-pointer">
                      <input 
                         type="range" min="0" max="1" step="0.01" 
                         value={isMuted ? 0 : volume}
                         onChange={(e) => setVolume(parseFloat(e.target.value))}
                         className="absolute w-full h-full opacity-0 z-20 cursor-pointer"
                      />
                      <div 
                         className="absolute h-full bg-white/50 rounded-full group-hover:bg-accent transition-colors"
                         style={{ width: `${(isMuted ? 0 : volume) * 100}%` }}
                      ></div>
                   </div>
                </div>

                <button className="p-3 rounded-full bg-white/5 hover:bg-white/10 transition-all text-gray-400 hover:text-white">
                  <Info size={20} />
                </button>
             </div>
          </div>
        </div>

        {/* RIGHT SIDE: LYRICS & INFO (Same as before) */}
        <div className="w-full md:w-1/2 flex flex-col relative bg-black/20">
          <div className="p-8 pb-4 border-b border-white/5">
             <div className="flex items-center gap-2 text-accent text-xs font-bold uppercase tracking-[0.2em] mb-3 opacity-80">
               <Sparkles size={14} /> Behind the Music
             </div>
             <p className="text-gray-300 text-sm leading-relaxed font-light line-clamp-3">
               {wikiInfo || currentSong.description || "The story of this song is being written by you, right now."}
             </p>
          </div>
          <div className="flex-1 overflow-hidden relative p-8">
             <div className="flex items-center justify-between mb-6 sticky top-0 z-10">
                <h3 className="text-white text-2xl font-bold flex items-center gap-3"><Mic2 className="text-accent" /> Lyrics</h3>
                {activeLine > 0 && <span className="text-[10px] font-bold bg-accent/20 text-accent px-3 py-1 rounded-full animate-pulse">On Air</span>}
             </div>
             <div ref={lyricsContainerRef} className="h-full overflow-y-auto custom-scrollbar space-y-8 pb-40 text-center mask-image-gradient">
                {loadingLyrics ? <div className="text-white/30 animate-pulse mt-20">Fetching lyrics...</div> : 
                   lyrics.map((line, index) => (
                     <p key={index} className={`text-2xl font-bold transition-all duration-500 cursor-pointer ${index === activeLine ? 'text-white scale-110 drop-shadow-[0_0_10px_rgba(255,255,255,0.5)]' : 'text-white/20 blur-[1px]'}`} 
                        onClick={() => useMusicStore.getState().setCurrentTime((index / lyrics.length) * (currentSong.duration || 240))}>
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