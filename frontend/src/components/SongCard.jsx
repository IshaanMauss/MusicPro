import React from 'react';
import { Play, AlertCircle } from 'lucide-react';
import useMusicStore from '../musicStore';

const SongCard = ({ song }) => {
  // 🟢 FIXED: Changed playSong to setCurrentSong to match your musicStore.js
  const { setCurrentSong, currentSong } = useMusicStore();
  const isActive = currentSong?.id === song.id;

  return (
    <div 
      // 🟢 FIXED: Using the correct function name here
      onClick={() => song.is_playable && setCurrentSong(song)}
      className={`relative group p-4 rounded-2xl cursor-pointer transition-all duration-500 hover:bg-white/10 ${isActive ? 'bg-white/10 ring-1 ring-accent' : 'bg-white/[0.03]'}`}
    >
      <div className="relative aspect-square mb-4 overflow-hidden rounded-xl shadow-2xl">
        <img 
          src={song.cover_url} 
          alt={song.title} 
          className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110" 
        />
        <div className="absolute inset-0 bg-black/40 backdrop-blur-[2px] flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
          <div className="bg-accent text-black p-4 rounded-full shadow-lg">
            {song.is_playable ? <Play fill="currentColor" size={24} /> : <AlertCircle size={24} />}
          </div>
        </div>
      </div>
      <div className="px-1">
        <h3 className="font-heading font-bold text-white truncate text-lg group-hover:text-accent transition-colors">{song.title}</h3>
        <p className="text-sm text-gray-400 truncate mt-1">{song.artist}</p>
      </div>
    </div>
  );
};

export default SongCard;