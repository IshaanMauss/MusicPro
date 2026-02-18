import React from 'react';
import { Play, AlertCircle, Music } from 'lucide-react';
// 🟢 Ensure this path points to where your musicStore.js actually is
import useMusicStore from '../musicStore';

const SongCard = ({ song }) => {
  const { setCurrentSong, currentSong } = useMusicStore();
  
  // Safety check to prevent crashing if song is undefined
  if (!song) return null;

  const isActive = currentSong?.id === song.id;

  return (
    <div 
      onClick={() => song.is_playable && setCurrentSong(song)}
      className={`relative group p-4 rounded-2xl cursor-pointer transition-all duration-500 hover:bg-white/10 ${
        isActive ? 'bg-white/10 ring-1 ring-emerald-500' : 'bg-white/[0.03]'
      }`}
    >
      <div className="relative aspect-square mb-4 overflow-hidden rounded-xl shadow-2xl bg-zinc-800">
        {/* 🟢 FIXED: Changed 'cover_url' to 'album_art' to match Backend */}
        <img 
          src={song.album_art || "https://placehold.co/300"} 
          alt={song.title || "Unknown Song"} 
          className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110" 
          onError={(e) => {
            e.target.onerror = null; 
            e.target.src = "https://placehold.co/300?text=No+Cover";
          }}
        />
        
        {/* Hover Overlay */}
        <div className={`absolute inset-0 bg-black/40 backdrop-blur-[2px] flex items-center justify-center transition-opacity duration-300 ${
          isActive ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
        }`}>
          <div className="bg-emerald-500 text-black p-4 rounded-full shadow-lg transform transition-transform duration-300 hover:scale-110">
            {song.is_playable ? <Play fill="currentColor" size={24} /> : <AlertCircle size={24} />}
          </div>
        </div>
      </div>

      <div className="px-1">
        <h3 className={`font-bold truncate text-lg transition-colors ${
          isActive ? 'text-emerald-500' : 'text-white group-hover:text-emerald-400'
        }`}>
          {song.title || "Unknown Title"}
        </h3>
        <p className="text-sm text-zinc-400 truncate mt-1">
          {song.artist || "Unknown Artist"}
        </p>
      </div>
    </div>
  );
};

export default SongCard;