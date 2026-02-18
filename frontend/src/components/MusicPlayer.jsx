import React, { useRef, useEffect } from 'react';
import { Play, Pause, SkipBack, SkipForward, Volume2, VolumeX, Maximize2, Heart, ChevronUp } from 'lucide-react';
import useMusicStore from '../musicStore';
import { getStreamUrl } from '../api';

const MusicPlayer = () => {
  const {
    currentSong, isPlaying, pauseSong, resumeSong, toggleLike,
    likedSongs, playNext, playPrev, currentTime, setCurrentTime,
    setPlayerOpen, isPlayerOpen,
    volume, isMuted, setVolume, toggleMute
  } = useMusicStore();

  const audioRef = useRef(null);

  const isLiked = currentSong && likedSongs.some(s => s.id === currentSong.id);

  // --- AUDIO ENGINE ---
  useEffect(() => {
    if (currentSong && audioRef.current) {
      const url = getStreamUrl(currentSong.msg_id);

      // 🟢 SYNC FIX: If reloading page, sync audio time to stored time
      const isNewSource = audioRef.current.src !== url;

      if (isNewSource) {
        audioRef.current.src = url;
        audioRef.current.load();

        // Restore time if we have one saved (and it's a resume)
        if (currentTime > 0) {
          audioRef.current.currentTime = currentTime;
        }

        if (isPlaying) audioRef.current.play().catch(() => { });
      } else if (isPlaying) {
        audioRef.current.play().catch(() => { });
      } else {
        audioRef.current.pause();
      }
    }
  }, [currentSong, isPlaying]);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = volume;
      audioRef.current.muted = isMuted;
    }
  }, [volume, isMuted]);

  const handleTimeUpdate = () => {
    if (audioRef.current) setCurrentTime(audioRef.current.currentTime);
  };

  const handleSeek = (e) => {
    const newTime = parseFloat(e.target.value);
    if (audioRef.current) audioRef.current.currentTime = newTime;
    setCurrentTime(newTime);
  };

  if (!currentSong) return null;

  const duration = audioRef.current?.duration || 100;
  // Ensure we never get > 100% or NaN
  const progressPercent = Math.min(100, Math.max(0, (currentTime / duration) * 100)) || 0;

  return (
    <>
      <audio
        ref={audioRef}
        onEnded={playNext}
        onTimeUpdate={handleTimeUpdate}
      />

      {/* PLAYER BAR */}
      <div className={`fixed bottom-0 left-0 right-0 bg-black/90 backdrop-blur-xl border-t border-white/10 transition-transform duration-300 z-50 ${isPlayerOpen ? 'translate-y-full' : 'translate-y-0'}`}>
        <div className="max-w-screen-2xl mx-auto px-4 h-20 flex items-center justify-between gap-4">

          {/* 1. Song Info */}
          <div className="flex items-center gap-4 w-[30%] min-w-[140px]">
            <div className="relative group cursor-pointer" onClick={() => setPlayerOpen(true)}>
              <img
                src={currentSong.album_art || "https://placehold.co/300"}
                alt={currentSong.title}
                className="w-12 h-12 rounded-md object-cover shadow-lg group-hover:opacity-80 transition-opacity"
              />
              <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 bg-black/40 rounded-md">
                <ChevronUp size={20} className="text-white" />
              </div>
            </div>
            <div className="overflow-hidden hidden sm:block">
              <h4 className="text-white font-medium truncate text-sm">{currentSong.title}</h4>
              <p className="text-zinc-400 text-xs truncate">{currentSong.artist}</p>
            </div>
            <button onClick={() => toggleLike(currentSong)} className={`hidden md:block ml-2 ${isLiked ? 'text-emerald-500 fill-emerald-500' : 'text-zinc-400'}`}>
              <Heart size={18} fill={isLiked ? "currentColor" : "none"} />
            </button>
          </div>

          {/* 2. Controls & Progress */}
          <div className="flex flex-col items-center flex-1 max-w-lg">
            <div className="flex items-center gap-6 mb-1">
              <button onClick={playPrev} className="text-zinc-400 hover:text-white transition-colors"><SkipBack size={20} /></button>
              <button
                onClick={isPlaying ? pauseSong : resumeSong}
                className="w-8 h-8 bg-white rounded-full flex items-center justify-center text-black hover:scale-110 transition-transform"
              >
                {isPlaying ? <Pause size={18} fill="currentColor" /> : <Play size={18} fill="currentColor" className="ml-0.5" />}
              </button>
              <button onClick={playNext} className="text-zinc-400 hover:text-white transition-colors"><SkipForward size={20} /></button>
            </div>

            {/* PROGRESS BAR */}
            <div className="w-full flex items-center gap-3 text-[10px] text-zinc-500 font-medium font-mono">
              <span className="w-8 text-right">{formatTime(currentTime)}</span>

              <div className="relative flex-1 h-1 bg-zinc-800 rounded-full group cursor-pointer">
                {(() => {
                  // 🟢 LOGICAL FIX: Use duration_seconds from DB if audio element isn't ready yet
                  const realDuration = (audioRef.current && !isNaN(audioRef.current.duration))
                    ? audioRef.current.duration
                    : (currentSong.duration_seconds || 0);

                  const barWidth = realDuration > 0 ? Math.min((currentTime / realDuration) * 100, 100) : 0;

                  return (
                    <>
                      <div
                        className="absolute top-0 left-0 h-full bg-emerald-500 rounded-full transition-all duration-100"
                        style={{ width: `${barWidth}%` }}
                      />
                      <div
                        className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-full shadow opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"
                        style={{ left: `${barWidth}%` }}
                      />
                      <input
                        type="range"
                        min="0"
                        max={realDuration || 100}
                        value={currentTime}
                        onChange={handleSeek}
                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                      />
                    </>
                  );
                })()}
              </div>

              <span className="w-8">{formatTime(audioRef.current?.duration || currentSong.duration_seconds)}</span>
            </div>
          </div>

          {/* 3. Volume & Expand */}
          <div className="flex items-center justify-end gap-3 w-[30%] min-w-[140px]">
            <div className="flex items-center gap-2 group w-24 sm:w-32 relative z-10">
              <button onClick={toggleMute} className="text-zinc-400 hover:text-white">
                {isMuted || volume === 0 ? <VolumeX size={18} /> : <Volume2 size={18} />}
              </button>
              <div className="relative flex-1 h-1 bg-zinc-800 rounded-full">
                <input
                  type="range" min="0" max="1" step="0.01"
                  value={isMuted ? 0 : volume}
                  onChange={(e) => setVolume(parseFloat(e.target.value))}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20"
                />
                <div
                  className="h-full bg-emerald-500 rounded-full pointer-events-none"
                  style={{ width: `${(isMuted ? 0 : volume) * 100}%` }}
                />
              </div>
            </div>
            <button
              onClick={() => setPlayerOpen(true)}
              className="p-2 text-zinc-400 hover:text-white hover:bg-white/10 rounded-full transition-colors z-20 relative"
            >
              <Maximize2 size={18} />
            </button>
          </div>

        </div>
      </div>
    </>
  );
};
const formatTime = (time) => {
  // 🟢 LOGICAL FIX: Handle null, undefined, strings, and NaN
  const totalSeconds = parseFloat(time);
  if (isNaN(totalSeconds) || totalSeconds <= 0) return "0:00";

  const minutes = Math.floor(totalSeconds / 60);
  const seconds = Math.floor(totalSeconds % 60);
  return `${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
};

export default MusicPlayer;