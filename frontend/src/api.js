import axios from 'axios';

export const API_URL = import.meta.env.PROD 
  ? 'https://music-app-backend-twia.onrender.com' // 👈 Your actual Render Backend URL
  : 'http://localhost:8000';
export const api = axios.create({
  baseURL: API_URL,
});

// --- FETCH SONGS ---
// 🟢 FIXED: Added 'language' to the parameter list
export const fetchSongs = async (search, limit, genre, mood, listen, skip = 0, language = 'all') => {
  try {
    console.log("📡 [API CALL] Params:", { search, genre, mood, listen, skip, language });

    const response = await api.get('/songs', {
      params: {
        search: search || '',
        limit: limit || 50,
        skip: skip || 0,
        genre: genre || 'all', 
        mood: mood || 'all', 
        listen: listen || 'all',
        language: language || 'all' // 🟢 Now correctly uses the passed argument
      },
    });
    
    return response.data.results;
  } catch (error) {
    console.error("❌ [API ERROR] Failed to fetch songs:", error);
    return [];
  }
};

export const getStreamUrl = (msgId) => {
  if (!msgId) return '';
  return `${API_URL}/stream/${msgId}`;
};