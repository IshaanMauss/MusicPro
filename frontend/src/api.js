import axios from 'axios';

// 🟢 Using Vite's environment variable system
// This pulls the URL from your frontend/.env file
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Fetches songs with high-precision filtering.
 */
export const fetchSongs = async (search = '', limit = 50, genre = 'all', mood = 'all', listen = 'all', skip = 0) => {
  try {
    const response = await axios.get(`${API_URL}/songs`, { 
      params: { search, limit, genre, mood, listen, skip } 
    });
    
    // Mapping the results to match your musicStore state structure
    return response.data.results.map(song => ({
      id: song.id,               
      title: song.title,         
      artist: song.artist, 
      cover_url: song.album_art, 
      msg_id: song.msg_id, 
      is_playable: song.is_playable,
      duration: song.duration,
      duration_category: song.duration_category
    }));
  } catch (error) {
    console.error("API Fetch Error:", error);
    return [];
  }
};

/**
 * Constructs the stream URL for the Telegram-backed player.
 */
export const getStreamUrl = (msgId) => {
  if (!msgId) return '';
  return `${API_URL}/stream/${msgId}`;
};