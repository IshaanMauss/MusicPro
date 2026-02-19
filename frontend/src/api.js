import axios from 'axios';

// 🟢 LOGIC: Environment-aware URL switching
export const API_URL = import.meta.env.PROD 
  ? 'https://music-app-backend-twia.onrender.com' 
  : 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_URL,
});

// --- 🛡️ PRODUCTION-GRADE AUTH INTERCEPTOR ---
api.interceptors.request.use((config) => {
  // 🛑 LOGIC: Prevent sending empty/old tokens to auth routes
  // This ensures registration and login never fail due to "Bad Request" headers
  if (config.url.includes('/auth/')) {
    return config;
  }

  try {
    const storage = localStorage.getItem('music-pro-storage-v16');
    if (storage) {
      const parsed = JSON.parse(storage);
      const token = parsed.state?.user?.access_token;
      
      // 🟢 LOGIC: Only attach if a valid token exists for the current session
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
  } catch (error) {
    console.error("Auth Interceptor Error:", error);
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

// --- FETCH SONGS ---
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
        language: language || 'all' 
      },
    });
    
    return response.data.results;
  } catch (error) {
    console.error("❌ [API ERROR] Failed to fetch songs:", error);
    return [];
  }
};

// --- STREAMING UTILITY ---
export const getStreamUrl = (msgId) => {
  if (!msgId) return '';
  return `${API_URL}/stream/${msgId}`;
};