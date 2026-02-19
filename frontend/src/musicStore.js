import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { fetchSongs as fetchSongsApi } from './api'; 
import axios from 'axios';
import { API_URL } from './api';

const useMusicStore = create(
  persist(
    (set, get) => ({
      // --- AUTH & USER STATE ---
      user: null, // Stores { username, access_token }

      // --- CORE STATE ---
      songs: [],
      currentSong: null,
      isPlaying: false,
      isLoading: false,
      likedSongs: [], 
      view: 'home', 
      currentTime: 0, 
      isPlayerOpen: false,

      // --- PAGINATION STATE ---
      skip: 0,
      hasMore: true,

      // --- GLOBAL VOLUME STATE ---
      volume: 0.7,
      isMuted: false,
      prevVolume: 0.7, 

      // --- FILTER STATE ---
      searchQuery: '',
      selectedGenre: 'all',
      selectedMood: 'all',
      selectedDuration: 'all',
      selectedLanguage: 'all', 

      // --- AUTH ACTIONS ---
      login: async (username, password) => {
        try {
          const res = await axios.post(`${API_URL}/auth/login`, { username, password });
          const { access_token, state } = res.data;
          
          set({ user: { username, access_token } });

          // Merge Cloud State into the Store
          if (state) {
            set({
              likedSongs: state.liked_songs || [],
              volume: state.volume ?? 0.7,
              selectedLanguage: state.selected_language || "all"
            });
          }
          return { success: true };
        } catch (error) {
          throw error;
        }
      },

      logout: () => {
        set({ user: null, likedSongs: [], currentSong: null, isPlaying: false });
        // Clear local storage to prevent session leakage
        localStorage.removeItem('music-pro-storage-v16');
      },

      // --- CLOUD SYNC ENGINE ---
      syncToCloud: async () => {
        const { user, likedSongs, currentSong, volume, selectedLanguage } = get();
        if (!user?.access_token) return;

        try {
          await axios.post(
            `${API_URL}/user/sync`, 
            {
              liked_songs: likedSongs,
              current_song: currentSong,
              volume: volume,
              selected_language: selectedLanguage
            },
            { headers: { Authorization: `Bearer ${user.access_token}` } }
          );
        } catch (e) {
          console.error("Cloud Sync Failed:", e);
        }
      },

      // --- SETTERS (With Auto-Sync) ---
      setView: (v) => set({ view: v }),
      setCurrentTime: (time) => set({ currentTime: time }),
      setPlayerOpen: (isOpen) => set({ isPlayerOpen: isOpen }),

      setSearchQuery: (query) => {
        set({ searchQuery: query, skip: 0, songs: [], hasMore: true });
        get().fetchSongs();
      },
      setGenre: (genre) => {
        set({ selectedGenre: genre, skip: 0, songs: [], hasMore: true });
        get().fetchSongs();
      },
      setMood: (mood) => {
        set({ selectedMood: mood, skip: 0, songs: [], hasMore: true });
        get().fetchSongs();
      },
      setDuration: (duration) => {
        set({ selectedDuration: duration, skip: 0, songs: [], hasMore: true });
        get().fetchSongs();
      },
      setLanguage: (language) => {
        set({ selectedLanguage: language, skip: 0, songs: [], hasMore: true });
        get().fetchSongs();
        get().syncToCloud(); // Sync language preference
      },
      
      setVolume: (vol) => {
        if (vol === 0) set({ volume: 0, isMuted: true });
        else set({ volume: vol, isMuted: false, prevVolume: vol });
        get().syncToCloud(); // Sync volume preference
      },

      toggleMute: () => {
        const { isMuted, volume, prevVolume } = get();
        if (isMuted) set({ isMuted: false, volume: prevVolume || 0.7 });
        else set({ isMuted: true, prevVolume: volume, volume: 0 });
        get().syncToCloud();
      },

      // --- FETCH SONGS (Preserving Double-Lock Deduplication) ---
      fetchSongs: async (isLoadMore = false) => {
        const { 
          searchQuery, selectedGenre, selectedMood, selectedDuration, selectedLanguage, 
          skip, songs, hasMore, isLoading 
        } = get();
        
        if (isLoading) return; 
        if (isLoadMore && !hasMore) return; 

        set({ isLoading: true });

        try {
          const limit = 50; 
          const results = await fetchSongsApi(
            searchQuery, limit, selectedGenre, selectedMood, selectedDuration, 
            isLoadMore ? skip : 0, 
            selectedLanguage
          );

          const newRawSongs = results || [];
          
          set((state) => {
            const baseSongs = isLoadMore ? state.songs : [];
            const combinedSongs = [...baseSongs, ...newRawSongs];

            const uniqueSongs = [];
            const seenIds = new Set();
            const seenSignatures = new Set();

            combinedSongs.forEach(song => {
                const idKey = String(song.id);
                const cleanTitle = (song.title || "").toLowerCase().replace(/[^a-z0-9]/g, "");
                const cleanArtist = (song.artist || "").toLowerCase().replace(/[^a-z0-9]/g, "");
                const sigKey = `${cleanTitle}|${cleanArtist}`;

                if (!seenIds.has(idKey) && !seenSignatures.has(sigKey)) {
                    seenIds.add(idKey);
                    seenSignatures.add(sigKey);
                    uniqueSongs.push(song);
                }
            });

            return { 
              songs: uniqueSongs,
              skip: isLoadMore ? state.skip + limit : limit,
              hasMore: newRawSongs.length === limit, 
              isLoading: false 
            };
          });

          if (newRawSongs.length > 0 && get().songs.length === 0 && isLoadMore) {
             get().fetchSongs(true);
          }

        } catch (error) {
          console.error("Store Error:", error);
          set({ isLoading: false });
        }
      },

      // --- PLAYBACK ---
      setCurrentSong: (song) => {
        set({ currentSong: song, isPlaying: true, currentTime: 0 });
        get().syncToCloud(); // Sync last played song
      },
      pauseSong: () => set({ isPlaying: false }),
      resumeSong: () => set({ isPlaying: true }),
      
      playNext: () => {
        const { currentSong, songs, likedSongs, view } = get();
        const activeList = view === 'home' ? songs : likedSongs;
        const index = activeList.findIndex(s => String(s.id) === String(currentSong?.id));
        if (index !== -1 && index < activeList.length - 1) {
            get().setCurrentSong(activeList[index + 1]);
        }
      },
      
      playPrev: () => {
        const { currentSong, songs, likedSongs, view } = get();
        const activeList = view === 'home' ? songs : likedSongs;
        const index = activeList.findIndex(s => String(s.id) === String(currentSong?.id));
        if (index > 0) {
            get().setCurrentSong(activeList[index - 1]);
        }
      },

      // --- LIKED SONGS (With Auto-Sync) ---
      toggleLike: (song) => {
        const { likedSongs } = get();
        const songId = String(song.id);
        const isLiked = likedSongs.some(s => String(s.id) === songId);
        
        if (isLiked) {
            set({ likedSongs: likedSongs.filter(s => String(s.id) !== songId) });
        } else {
            set({ likedSongs: [...likedSongs, song] });
        }
        get().syncToCloud(); // Permanent cloud save
      },

      resetFilters: () => {
        set({ 
          selectedGenre: 'all', selectedMood: 'all', selectedDuration: 'all', selectedLanguage: 'all', 
          searchQuery: '', skip: 0, songs: [], hasMore: true 
        });
        get().fetchSongs();
      },
    }),
    {
      name: 'music-pro-storage-v16',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ 
        user: state.user, // Important: keep the user logged in
        likedSongs: state.likedSongs,
        volume: state.volume,
        isMuted: state.isMuted,
        currentSong: state.currentSong,
        currentTime: state.currentTime,
        selectedLanguage: state.selectedLanguage 
      }),
    }
  )
);

export default useMusicStore;