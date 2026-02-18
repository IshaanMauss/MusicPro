import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { fetchSongs as fetchSongsApi } from './api'; 

const useMusicStore = create(
  persist(
    (set, get) => ({
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

      // --- SETTERS ---
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
      },
      
      setVolume: (vol) => {
        if (vol === 0) set({ volume: 0, isMuted: true });
        else set({ volume: vol, isMuted: false, prevVolume: vol });
      },

      toggleMute: () => {
        const { isMuted, volume, prevVolume } = get();
        if (isMuted) set({ isMuted: false, volume: prevVolume || 0.7 });
        else set({ isMuted: true, prevVolume: volume, volume: 0 });
      },

      // --- FETCH SONGS (DOUBLE-LOCK DEDUPLICATION) ---
      fetchSongs: async (isLoadMore = false) => {
        const { 
          searchQuery, selectedGenre, selectedMood, selectedDuration, selectedLanguage, 
          skip, songs, hasMore, isLoading 
        } = get();
        
        // 🔒 LOCK: Prevent race conditions
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
            // 1. Determine base list
            const baseSongs = isLoadMore ? state.songs : [];
            
            // 2. Combine arrays (Old + New)
            const combinedSongs = [...baseSongs, ...newRawSongs];

            // 3. 🛡️ DOUBLE-LOCK DEDUPLICATION ENGINE
            const uniqueSongs = [];
            const seenIds = new Set();
            const seenSignatures = new Set();

            combinedSongs.forEach(song => {
                // Generate Unique Keys
                const idKey = String(song.id);
                // Signature: "Tum Hi Ho|Arijit Singh" (removes case/space diffs)
                const cleanTitle = (song.title || "").toLowerCase().replace(/[^a-z0-9]/g, "");
                const cleanArtist = (song.artist || "").toLowerCase().replace(/[^a-z0-9]/g, "");
                const sigKey = `${cleanTitle}|${cleanArtist}`;

                // 🛑 CHECK: Is this ID new? AND Is this Song Content new?
                // If either exists, we skip (it's a duplicate)
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

          // Recursive check for empty pages (if filter removed everything)
          if (newRawSongs.length > 0 && get().songs.length === 0 && isLoadMore) {
             get().fetchSongs(true);
          }

        } catch (error) {
          console.error("Store Error:", error);
          set({ isLoading: false });
        }
      },

      // --- PLAYBACK (Unchanged) ---
      setCurrentSong: (song) => set({ currentSong: song, isPlaying: true, currentTime: 0 }),
      pauseSong: () => set({ isPlaying: false }),
      resumeSong: () => set({ isPlaying: true }),
      
      playNext: () => {
        const { currentSong, songs, likedSongs, view } = get();
        const activeList = view === 'home' ? songs : likedSongs;
        const index = activeList.findIndex(s => String(s.id) === String(currentSong?.id));
        if (index !== -1 && index < activeList.length - 1) {
            set({ currentSong: activeList[index + 1], isPlaying: true, currentTime: 0 });
        }
      },
      
      playPrev: () => {
        const { currentSong, songs, likedSongs, view } = get();
        const activeList = view === 'home' ? songs : likedSongs;
        const index = activeList.findIndex(s => String(s.id) === String(currentSong?.id));
        if (index > 0) {
            set({ currentSong: activeList[index - 1], isPlaying: true, currentTime: 0 });
        }
      },

      // 🛡️ TOGGLE LIKE (ID Safe)
      toggleLike: (song) => {
        const { likedSongs } = get();
        const songId = String(song.id);
        const isLiked = likedSongs.some(s => String(s.id) === songId);
        
        if (isLiked) {
            set({ likedSongs: likedSongs.filter(s => String(s.id) !== songId) });
        } else {
            set({ likedSongs: [...likedSongs, song] });
        }
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
      name: 'music-pro-storage-v16', // 🟢 V16: Ensures fresh start
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ 
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