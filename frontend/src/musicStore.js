import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { fetchSongs as fetchSongsApi } from './api';

const useMusicStore = create(
  persist(
    (set, get) => ({
      // Core State
      songs: [],
      currentSong: null,
      isPlaying: false,
      isLoading: false,
      likedSongs: [], 
      view: 'home', 
      currentTime: 0, 
      isPlayerOpen: false,

      // 🟢 GLOBAL VOLUME STATE
      volume: 0.7,
      isMuted: false,
      prevVolume: 0.7, // Internal memory for unmuting

      // Filter State
      searchQuery: '',
      selectedGenre: 'all',
      selectedMood: 'all',
      selectedDuration: 'all',

      // Actions
      setView: (v) => set({ view: v }),
      setSearchQuery: (query) => set({ searchQuery: query }),
      setGenre: (genre) => set({ selectedGenre: genre }),
      setMood: (mood) => set({ selectedMood: mood }),
      setDuration: (duration) => set({ selectedDuration: duration }),
      setCurrentTime: (time) => set({ currentTime: time }),
      setPlayerOpen: (isOpen) => set({ isPlayerOpen: isOpen }),

      // 🟢 VOLUME ACTIONS
      setVolume: (vol) => {
        const { isMuted } = get();
        // If user drags slider, update volume. If dragged to 0, mute it.
        if (vol === 0) {
            set({ volume: 0, isMuted: true });
        } else {
            // If it was muted and user drags, unmute it
            set({ volume: vol, isMuted: false, prevVolume: vol });
        }
      },

      toggleMute: () => {
        const { isMuted, volume, prevVolume } = get();
        if (isMuted) {
          // Unmute: Restore previous volume (or default to 0.7)
          set({ isMuted: false, volume: prevVolume || 0.7 });
        } else {
          // Mute: Save current volume and set to 0
          set({ isMuted: true, prevVolume: volume, volume: 0 });
        }
      },

      // Fetch Songs (De-duplication)
      fetchSongs: async () => {
        set({ isLoading: true });
        const { searchQuery, selectedGenre, selectedMood, selectedDuration } = get();
        
        try {
          const response = await fetchSongsApi(searchQuery, 100, selectedGenre, selectedMood, selectedDuration);
          const rawSongs = response?.songs || [];
          const uniqueSongsMap = new Map();
          rawSongs.forEach(song => {
            const fingerprint = `${song.title.toLowerCase().trim()}|${song.artist.toLowerCase().trim()}`;
            if (!uniqueSongsMap.has(fingerprint)) uniqueSongsMap.set(fingerprint, song);
          });
          set({ songs: Array.from(uniqueSongsMap.values()), isLoading: false });
        } catch (error) {
          console.error("Store Fetch Error:", error);
          set({ songs: [], isLoading: false });
        }
      },

      // Playback Controls
      setCurrentSong: (song) => set({ currentSong: song, isPlaying: true, currentTime: 0 }),
      pauseSong: () => set({ isPlaying: false }),
      resumeSong: () => set({ isPlaying: true }),

      playNext: () => {
        const { currentSong, songs, likedSongs, view } = get();
        const activeList = view === 'home' ? songs : likedSongs;
        const index = activeList.findIndex(s => s.id === currentSong?.id);
        if (index !== -1 && index < activeList.length - 1) {
          set({ currentSong: activeList[index + 1], isPlaying: true, currentTime: 0 });
        }
      },

      playPrev: () => {
        const { currentSong, songs, likedSongs, view } = get();
        const activeList = view === 'home' ? songs : likedSongs;
        const index = activeList.findIndex(s => s.id === currentSong?.id);
        if (index > 0) {
          set({ currentSong: activeList[index - 1], isPlaying: true, currentTime: 0 });
        }
      },

      toggleLike: (song) => {
        const { likedSongs } = get();
        const isLiked = likedSongs.some(s => s.id === song.id);
        if (isLiked) set({ likedSongs: likedSongs.filter(s => s.id !== song.id) });
        else set({ likedSongs: [...likedSongs, song] });
      },

      resetFilters: () => set({ 
        selectedGenre: 'all', selectedMood: 'all', selectedDuration: 'all', searchQuery: '' 
      }),
    }),
    {
      name: 'music-pro-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ 
        likedSongs: state.likedSongs,
        view: state.view,
        currentSong: state.currentSong, 
        currentTime: state.currentTime, 
        selectedGenre: state.selectedGenre,
        selectedMood: state.selectedMood,
        selectedDuration: state.selectedDuration,
        // 🟢 SAVE VOLUME SETTINGS
        volume: state.volume,
        isMuted: state.isMuted,
        prevVolume: state.prevVolume
      }),
    }
  )
);

export default useMusicStore;