import React, { useEffect, useRef, useState } from 'react';
import { Play, Pause, SkipBack, SkipForward, Volume2, VolumeX, Maximize2, Heart } from 'lucide-react';
import useMusicStore from '../musicStore';
import { getStreamUrl } from '../api';

const MusicPlayer = () => {
  const {
    currentSong, isPlaying, pauseSong, resumeSong, toggleLike,
    likedSongs, playNext, playPrev, currentTime, setCurrentTime,
    setPlayerOpen, isPlayerOpen,
    // 🟢 GLOBAL VOLUME
    volume, isMuted, setVolume, toggleMute
  } = useMusicStore();

  const audioRef = useRef(null);
  const [progress, setProgress] = useState(currentTime || 0);
  const [duration, setDuration] = useState(0);

  const isLiked = currentSong && likedSongs.some(s => s.id === currentSong.id);

  // --- AUDIO ENGINE ---
  useEffect(() => {
    if (currentSong && audioRef.current) {
      const url = getStreamUrl(currentSong.msg_id);
      if (audioRef.current.src !== url) {
        audioRef.current.src = url;
        audioRef.current.load();
        if (isPlaying) audioRef.current.play().catch(() => {});
      } else if (audioRef.current.currentTime === 0 && currentTime > 0) {
        audioRef.current.currentTime = currentTime;
      }
    }
  }, [currentSong]);

  useEffect(() => {
    if (!audioRef.current) return;
    if (isPlaying) audioRef.current.play().catch(() => {});
    else audioRef.current.pause();
  }, [isPlaying]);

  // 🟢 SYNC AUDIO ELEMENT WITH STORE VOLUME
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = volume; // Store handles 0 logic for mute
      audioRef.current.muted = isMuted;
    }
  }, [volume, isMuted]);

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      const curr = audioRef.current.currentTime;
      setProgress(curr);
      setDuration(audioRef.current.duration || 0);
      if (Math.abs(curr - currentTime) > 1) setCurrentTime(curr);
    }
  };

  const formatTime = (time) => {
    if (!time) return "0:00";
    const mins = Math.floor(time / 60);
    const secs = Math.floor(time % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (!currentSong) return null;

  return (
    <>
      <audio
        ref={audioRef}
        onTimeUpdate={handleTimeUpdate}
        onEnded={playNext}
        onLoadedMetadata={() => {
          if (currentTime > 0 && Math.abs(audioRef.current.currentTime - currentTime) > 1) {
            audioRef.current.currentTime = currentTime;
          }
        }}
      />

      {!isPlayerOpen && (
        <div className="fixed bottom-0 left-0 right-0 bg-black/80 backdrop-blur-2xl border-t border-white/10 p-4 flex items-center justify-between z-[100] animate-in fade-in slide-in-from-bottom duration-500 shadow-[0_-10px_40px_rgba(0,0,0,0.5)]">
          {/* INFO */}
          <div className="flex items-center gap-4 w-1/4">
            <div className="w-16 h-16 rounded-xl overflow-hidden shadow-[0_4px_20px_rgba(0,0,0,0.5)] ring-1 ring-white/10 relative group">
              <img src={currentSong.cover_url} alt="" className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700" />
            </div>
            <div className="flex flex-col overflow-hidden">
              <h4 className="text-white font-bold text-sm truncate pr-4">{currentSong.title}</h4>
              <p className="text-gray-400 text-xs truncate">{currentSong.artist}</p>
            </div>
            <button
              onClick={() => toggleLike(currentSong)}
              className={`ml-2 p-2 rounded-full hover:bg-white/10 transition-all active:scale-90 ${isLiked ? 'text-accent' : 'text-gray-500 hover:text-white'}`}
            >
              <Heart size={20} fill={isLiked ? "currentColor" : "none"} />
            </button>
          </div>

          {/* CONTROLS */}
          <div className="flex flex-col items-center gap-2 flex-1 max-w-2xl px-8">
            <div className="flex items-center gap-6">
              <button onClick={playPrev} className="text-gray-400 hover:text-white transition-colors hover:scale-110 active:scale-95">
                <SkipBack size={24} fill="currentColor" />
              </button>
              
              <button
                onClick={isPlaying ? pauseSong : resumeSong}
                className="w-14 h-14 bg-white rounded-full flex items-center justify-center text-black hover:scale-105 transition-transform shadow-[0_0_20px_rgba(255,255,255,0.3)]"
              >
                {isPlaying ? <Pause size={28} fill="currentColor" /> : <Play size={28} fill="currentColor" className="ml-1" />}
              </button>

              <button onClick={playNext} className="text-gray-400 hover:text-white transition-colors hover:scale-110 active:scale-95">
                <SkipForward size={24} fill="currentColor" />
              </button>
            </div>

            <div className="w-full flex items-center gap-3 text-[10px] text-gray-500 font-mono">
              <span className="w-8 text-right">{formatTime(progress)}</span>
              <div className="relative flex-1 h-1 group cursor-pointer">
                <input
                  type="range"
                  min="0"
                  max={duration || 100}
                  value={progress}
                  onChange={(e) => {
                    const newTime = parseFloat(e.target.value);
                    setProgress(newTime);
                    audioRef.current.currentTime = newTime;
                    setCurrentTime(newTime);
                  }}
                  className="absolute w-full h-1 opacity-0 z-20 cursor-pointer"
                />
                <div className="absolute w-full h-1 bg-white/10 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-accent shadow-[0_0_10px_rgba(71,208,208,0.5)] relative"
                    style={{ width: `${(progress / (duration || 1)) * 100}%` }}
                  ></div>
                </div>
              </div>
              <span className="w-8">{formatTime(duration)}</span>
            </div>
          </div>

          {/* VOLUME & MAXIMIZE */}
          <div className="w-1/4 flex justify-end items-center gap-4 text-gray-400 pr-4">
            <div className="flex items-center gap-3 group bg-white/5 px-3 py-2 rounded-full border border-white/5 hover:border-white/10 transition-all">
              <button onClick={toggleMute} className="hover:text-white transition-colors">
                {isMuted || volume === 0 ? <VolumeX size={18} /> : <Volume2 size={18} />}
              </button>

              <div className="relative w-24 h-1 cursor-pointer">
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={isMuted ? 0 : volume}
                  onChange={(e) => setVolume(parseFloat(e.target.value))}
                  className="absolute w-full h-full opacity-0 z-20 cursor-pointer"
                />
                <div className="absolute w-full h-1 bg-white/20 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-accent/50 to-accent"
                    style={{ width: `${(isMuted ? 0 : volume) * 100}%` }}
                  ></div>
                </div>
              </div>
            </div>

            <button
              onClick={() => setPlayerOpen(true)}
              className="hover:text-white transition-colors p-2 hover:bg-white/10 rounded-full"
            >
              <Maximize2 size={18} />
            </button>
          </div>
        </div>
      )}
    </>
  );
};

export default MusicPlayer;