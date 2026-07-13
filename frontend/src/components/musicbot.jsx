import React, {
  useState,
  useEffect,
  useRef,
  useMemo,
  useCallback,
  memo
} from "react";

import {
  X,
  Mic,
  Send,
  Sparkles,
  Music2,
  Heart,
  Wrench,
  TrendingUp,
  Brain,
  Loader2
} from "lucide-react";

import toast from "react-hot-toast";

import useMusicStore from "../musicStore";
import { api } from "../api";
import voiceRecorder from "../services/voiceRecorder";
import ttsService from "../services/ttsService";
import PandaAvatar from "./pandaavatar";
import TypingIndicator from "./typingIndicator";
import VoiceVisualizer from "./voicevisualizer";
import { getGreeting } from "../utils/greeting";

// ADDITIVE: Naughty Playful Hover Animation
const naughtyHoverCSS = `
  @keyframes playful-hover {
    0% { transform: translateY(0px) translateX(0px) rotate(0deg); }
    25% { transform: translateY(-8px) translateX(6px) rotate(6deg); }
    50% { transform: translateY(4px) translateX(-4px) rotate(-4deg); }
    75% { transform: translateY(-6px) translateX(4px) rotate(3deg); }
    100% { transform: translateY(0px) translateX(0px) rotate(0deg); }
  }
  .animate-playful { animation: playful-hover 4s ease-in-out infinite; }
`;
const BOT_STATES = {

  IDLE: "idle",

  THINKING: "thinking",

  LISTENING: "listening",

  SPEAKING: "speaking",

  HAPPY: "happy",

  EXCITED: "excited",

  LOVED: "loved",

  RAINY: "rainy",

  SINGING: "singing",

  MELANCHOLY: "melancholy",

  WORKOUT: "workout",

  LEARNING: "learning",

  SLEEPY: "sleepy"

};

const QUICK_ACTIONS = [
  {
    id: "surprise",
    label: "🎵 Surprise Me",
    icon: Sparkles
  },

  {
    id: "romantic",
    label: "❤️ Romantic",
    icon: Heart
  },

  {
    id: "workout",
    label: "🏋️ Workout",
    icon: TrendingUp
  },

  {
    id: "rain",
    label: "🌧 Rainy",
    icon: Music2
  },

  {
    id: "learn",
    label: "🧠 Learn Taste",
    icon: Brain
  },

  {
    id: "fix_metadata",
    label: "🧹 Fix Metadata",
    icon: Wrench
  }
];

const MOOD_EMOTIONS = {

  romantic:
    BOT_STATES.LOVED,

  rain:
    BOT_STATES.RAINY,

  rainy:
    BOT_STATES.RAINY,

  workout:
    BOT_STATES.WORKOUT,

  chill:
    BOT_STATES.HAPPY,

  sad:
    BOT_STATES.MELANCHOLY

};

const shouldAutoPlayResult = (text, forcePlay) => {
  if (forcePlay) return true;
  return /\b(play|start|find|search|song|songs|music|gaana|baja|chalao)\b/i.test(text || "");
};

const createId = () =>
  `${Date.now()}-${Math.random()
    .toString(36)
    .slice(2, 9)}`;

const INITIAL_MESSAGE = {
  id: createId(),

  type: "bot",

  text:
    "Hi! I'm Vibe, your AI music companion 🦊🎵\n\nAsk me anything about music, moods, playlists, or simply say 'surprise me'.",

  timestamp: Date.now()
};


// ==========================================
// ADDITIVE: MILESTONE 3 - WAKE WORD LISTENER
// Paste this ABOVE your MusicBot component
// ==========================================
    const useWakeWord = (onWakeWordDetected, isActive) => {
    const recognitionRef = useRef(null);

    useEffect(() => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition || isActive) return;

        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onresult = (event) => {
            const current = event.resultIndex;
            const transcript = event.results[current][0].transcript.toLowerCase().trim();

            if (transcript.includes("hey vibe") || transcript.includes("hey, vibe")) {
                recognition.stop(); 
                if (onWakeWordDetected) onWakeWordDetected(); 
            }
        };

        recognition.onend = () => {
            if (!isActive) {
                try {
                    recognition.start();
                } catch {
                    console.debug("Wake word listener restart skipped.");
                }
            }
        };

        try {
            recognition.start();
            recognitionRef.current = recognition;
        } catch (error) {
            console.error("Wake word listener failed:", error);
        }

        return () => {
            if (recognitionRef.current) {
                recognitionRef.current.onend = null; 
                recognitionRef.current.stop();
            }
        };
    }, [onWakeWordDetected, isActive]);
};
function MusicBot() {
      const {
    user,
    setCurrentSong,
    setSongs,
    view,
    setView,
    pauseSong,
  } = useMusicStore();


  const isVibePage = view === 'vibe_ai';
  const [showMobileStats, setShowMobileStats] = useState(false); // FIX: mobile toggle for stats/actions panel

  //const [isOpen, setIsOpen] = useState(false);

  const [messages, setMessages] =
    useState([INITIAL_MESSAGE]);

  const [conversationContext, setConversationContext] =
  useState({});

  const [input, setInput] =
    useState("");

  const [loading, setLoading] =
    useState(false);

  const [botState, setBotState] =
    useState(BOT_STATES.IDLE);



  const [voiceEnabled, setVoiceEnabled] =
    useState(false);

  const [memory, setMemory] =
    useState({
      moods: [],
      genres: [],
      artists: []
    });

  const [sessionStats, setSessionStats] =
    useState({
      searches: 0,
      playlistsGenerated: 0,
      recommendationsPlayed: 0
    });

  const recognitionRef = useRef(null);

  const recordingTimeoutRef = useRef(null); 

  const chatContainerRef = useRef(null);

  const inputRef = useRef(null);

  const audioRef = useRef(null);

  const holdTimeoutRef = useRef(null);

  // Draggable floating icon: starts top-right, can be dragged anywhere,
  // always stays on top (z-index handled in buttonClass below).
  const [botPos, setBotPos] = useState(() => {
    if (typeof window === 'undefined') return { x: 24, y: 24 };
    const size = 64;
    const margin = 24;
    return { x: window.innerWidth - size - margin, y: margin };
  });
  const dragRef = useRef({ dragging: false, moved: false, startX: 0, startY: 0, originX: 0, originY: 0 });

  const onDragMove = useCallback((clientX, clientY) => {
    const d = dragRef.current;
    if (!d.dragging) return;
    const dx = clientX - d.startX;
    const dy = clientY - d.startY;

    if (!d.moved && (Math.abs(dx) > 6 || Math.abs(dy) > 6)) {
      d.moved = true;
      // A real drag started — cancel the long-press-to-talk timer so it
      // doesn't fire mid-drag.
      if (holdTimeoutRef.current) {
        clearTimeout(holdTimeoutRef.current);
        holdTimeoutRef.current = null;
      }
    }

    if (d.moved) {
      const size = 64;
      const maxX = window.innerWidth - size;
      const maxY = window.innerHeight - size;
      setBotPos({
        x: Math.min(Math.max(0, d.originX + dx), maxX),
        y: Math.min(Math.max(0, d.originY + dy), maxY),
      });
    }
  }, []);

  const onMouseMoveDrag = useCallback((e) => onDragMove(e.clientX, e.clientY), [onDragMove]);
  const onTouchMoveDrag = useCallback((e) => {
    if (e.touches && e.touches[0]) {
      onDragMove(e.touches[0].clientX, e.touches[0].clientY);
      if (dragRef.current.moved) e.preventDefault();
    }
  }, [onDragMove]);

  const endDrag = useCallback(() => {
    const d = dragRef.current;
    const wasDrag = d.moved;
    d.dragging = false;
    d.moved = false;

    window.removeEventListener('mousemove', onMouseMoveDrag);
    window.removeEventListener('mouseup', endDrag);
    window.removeEventListener('touchmove', onTouchMoveDrag);
    window.removeEventListener('touchend', endDrag);

    if (!wasDrag) {
      // Wasn't a drag — treat as the normal press-release (tap / long-press-to-talk)
      handlePressEnd();
    } else if (holdTimeoutRef.current) {
      clearTimeout(holdTimeoutRef.current);
      holdTimeoutRef.current = null;
    }
  }, [onMouseMoveDrag, onTouchMoveDrag]);

  const startDrag = (clientX, clientY) => {
    dragRef.current = {
      dragging: true,
      moved: false,
      startX: clientX,
      startY: clientY,
      originX: botPos.x,
      originY: botPos.y,
    };
    window.addEventListener('mousemove', onMouseMoveDrag);
    window.addEventListener('mouseup', endDrag);
    window.addEventListener('touchmove', onTouchMoveDrag, { passive: false });
    window.addEventListener('touchend', endDrag);
  };

  const handleBotMouseDown = (e) => {
    startDrag(e.clientX, e.clientY);
    handlePressStart();
  };
  const handleBotTouchStart = (e) => {
    if (e.touches && e.touches[0]) startDrag(e.touches[0].clientX, e.touches[0].clientY);
    handlePressStart();
  };

  const handlePressStart = () => {
    holdTimeoutRef.current = setTimeout(() => {
        console.log("3 Second Long Press Detected! Activating Voice Mode...");
        setView('vibe_ai'); // Jump to the tab
        startVoice();       // Activate Mic instantly
        holdTimeoutRef.current = null;
    }, 3000); // 3 seconds
  };

  const handlePressEnd = () => {
    if (holdTimeoutRef.current) {
        // If released BEFORE 3 seconds, cancel the mic and just switch tabs
        clearTimeout(holdTimeoutRef.current);
        holdTimeoutRef.current = null;
        setView('vibe_ai');
    }
  };

    useEffect(() => {

    if (!chatContainerRef.current)
      return;

    chatContainerRef.current.scrollTo({
      top:
        chatContainerRef.current
          .scrollHeight,

      behavior: "smooth"
    });

  }, [messages]);

  

    useEffect(() => {

    const stored =
      localStorage.getItem(
        "vibestream-ai-memory"
      );

    if (!stored)
      return;

    try {

      setMemory(
        JSON.parse(stored)
      );

    } catch (err) {

      console.error(err);

    }

  }, []);
  useEffect(() => {

    localStorage.setItem(
      "vibestream-ai-memory",

      JSON.stringify(memory)
    );

  }, [memory]);

  useEffect(() => {
    return ttsService.subscribe((speaking) => {
      setBotState(speaking ? BOT_STATES.SPEAKING : BOT_STATES.IDLE);
    });
  }, []);

  const speakText = useCallback(async (text, language = "en") => {
    if (!text || !text.trim()) return;

    try {
      // Let the ttsService handle the actual network request and audio playback
      await ttsService.speak(text, language);
    } catch (err) {
      console.error("TTS playback failed:", err);
      setBotState(BOT_STATES.IDLE);
    }
  }, []); 

  // Change the dependency from (botState !== BOT_STATES.IDLE) to just botState
  useWakeWord(() => {
      console.log("Wake word detected!");
      
      const fetchWakeWordGreeting = async () => {
          try {
              const res = await api.post("/bot/dynamic-greeting", {
                  username: user?.username || "Friend"
              });
              const aiGreeting = res.data.greeting;
              
              await speakText(aiGreeting, "en");
          } catch (err) {
              console.error("Wake word flow error:", err);
              // Fallback: speak a local greeting instead of staying silent
              try {
                  await ttsService.speak(getGreeting(user?.username));
              } catch (ttsErr) {
                  console.error("Wake word fallback TTS failed:", ttsErr);
              }
          }
      };

      fetchWakeWordGreeting(

      );

  }, botState !== BOT_STATES.IDLE || !isVibePage);
  // FIX: wake-word mic listener was starting on EVERY page load, on every tab,
  // because MusicBot renders unconditionally in App.jsx and botState defaults
  // to IDLE on mount. It also restarted itself every time recognition timed out,
  // which is what caused the repeating mic-access chime and blocked song playback
  // site-wide. Now it only listens while the user is actually on the Vibe AI tab
  // AND the bot is idle — never on Home, Search, or while a response is loading.

  // ... rest of your component (return statement, etc)

    const setEmotion = useCallback(

  (
    emotion,
    timeout = 2500
  ) => {

    setBotState(emotion);

    if (
      timeout &&
      emotion !== BOT_STATES.IDLE
    ) {

      window.clearTimeout(
        audioRef.current
      );

      audioRef.current =
        window.setTimeout(
          () => {

            setBotState(
              BOT_STATES.IDLE
            );

          },

          timeout
        );

    }

  },

  []

);

      const buttonClass =
    useMemo(() => {

      return `
        fixed
        z-[9999]

        w-16
        h-16

        rounded-full

        bg-gradient-to-br
        from-cyan-400
        via-emerald-400
        to-cyan-500

        shadow-2xl
        shadow-cyan-500/30

        transition-transform
        duration-300

        hover:scale-110
        active:scale-95
      `;

    }, []);

      useEffect(() => {

    const SpeechRecognition =
      window.SpeechRecognition ||
      window.webkitSpeechRecognition;

    if (!SpeechRecognition)
      return;

    setVoiceEnabled(true);

    const recognition =
      new SpeechRecognition();

    recognition.continuous =
      true;

    recognition.interimResults =
      false;

    recognition.lang =
      "en-US";
    recognition.lang = navigator.language || "en-IN";

    recognition.maxAlternatives =
      1;

    recognition.onstart =
      () => {
        console.log(
            "🎤 Voice recognition started",
              recognition
                );
        setBotState(
          BOT_STATES.LISTENING
        );

      };

    recognition.onresult =
  async event => {
    console.log("🔥 onresult fired");
    const transcript =
      event.results[0][0]
        .transcript;
    console.log("Transcript:", transcript);
    setInput(
      transcript
    );

    try {

      const res =
        await api.post(

          "/bot/voice-command",

          {
            text:
              transcript
          }

        );

      const {
        intent,
        song,
        artist,
        album,
        playlist,
        optimized_query
        } = res.data;

      switch (intent) {

        case "surprise":

          surpriseMe();
          break;

        case "daily_mix":

          generatePlaylist();
          break;

        case "mood":

          discoverMood(
            res.data.mood
          );

          break;

        default: {
          // Explicitly flag any standard voice intents starting with 'play'
          const isPlayIntent = shouldAutoPlayResult(transcript, !!(intent && intent.toLowerCase().startsWith("play")));
          const voiceQuery =
              optimized_query ||
              song ||
              artist ||
              album ||
              playlist ||
              transcript;

          console.log("VOICE ROUTE SELECTION -> Query:", voiceQuery, "| Force Autoplay:", isPlayIntent);

          await handleSend(voiceQuery, isPlayIntent);
          break;
        }
      }

    } catch {

      await handleSend(
        transcript,true
      );

    };

  };
    recognition.onerror = (event) => {

    console.error(
        "🎤 SpeechRecognition Error:",
        event.error
    );

    console.error(event);

    toast.error(
        "Voice recognition failed: " + event.error
    );

    setBotState(
        BOT_STATES.IDLE
    );

  };

    recognition.onend = () => {

    console.log(
        "🎤 SpeechRecognition Ended"
    );

    setBotState(
        BOT_STATES.IDLE
    );

};
    recognition.onspeechstart = () => {
    console.log("🟢 Speech started");
};

    recognition.onspeechend = () => {
    console.log("🔴 Speech ended");
};

    recognition.onaudiostart = () => {
    console.log("🎧 Audio started");
};

    recognition.onaudioend = () => {
    console.log("🔇 Audio ended");
};
  recognitionRef.current =
    recognition;


/* CLEANUP FUNCTION */
return () => {

  recognition.stop();

};


}, []);


useEffect(() => {

  localStorage.setItem(

    "vibe_ai_messages",

    JSON.stringify(messages)

  );

}, [messages]);


// =====================================
// TASTE PROFILE SYNC
// =====================================


    

    const addBotMessage = useCallback((text, songs = []) => {

  setMessages(prev => [
    ...prev,
    {
      id: createId(),
      type: "bot",
      text,
      songs,
      timestamp: Date.now()
    }
  ]);

}, []);
const addUserMessage = useCallback((text) => {

  setMessages(prev => [
    ...prev,
    {
      id: createId(),
      type: "user",
      text,
      timestamp: Date.now()
    }
  ]);

}, []);

/* ============================
   INSERT HERE
============================ */
useEffect(() => {
    if (!user) return;

    const fetchDynamicGreeting = async () => {
        try {
            // 1. Ask the AI to generate a natural greeting
            const res = await api.post("/bot/dynamic-greeting", {
                username: user.name || user.username || "Friend"
            });
            const aiGreeting = res.data.greeting;

            // 2. Add it to the chat UI
            addBotMessage(aiGreeting, []);

            // 3. Make the AI speak its generated thought!
            await speakText(aiGreeting, "en");
            
        } catch (err) {
            console.error("Dynamic Greeting Error:", err);
            // Safe fallback if network fails
            addBotMessage(getGreeting(user.name || user.username), []);
        }
    };

    fetchDynamicGreeting();
}, [user, addBotMessage, speakText]);


const syncTasteProfile =
  useCallback(

    async () => {

      if (!user) return;

      try {

        const history = messages
          .filter(
            x => x.songs
          )
          .flatMap(
            x => x.songs
          )
          .slice(-100);

        await api.post(

          "/bot/taste-profile",

          {

            user_id:
              user.username,

            songs:
              history

          }

        );

      } catch (err) {

        console.error(
          err
        );

      }

    },

    [

      user,

      messages

    ]

);

useEffect(() => {

  syncTasteProfile();

}, [

  syncTasteProfile

]);
useEffect(() => {
    return () => {
        ttsService.stop();
    };
  }, []);

const updateConversationContext =
  useCallback(

    async (
      text,
      songs = []
    ) => {

      try {

        const res =
          await api.post(

            "/bot/context",

            {

              user_id:
                user?.username ||
                "guest",

              message:
                text,

              last_songs:
                songs

            }

          );

        setConversationContext(
          res.data
        );

      }

      catch (err) {

        console.error(
          err
        );

      }

    },

    [

      user

    ]

);

const surpriseMe = useCallback(async () => {

  setLoading(true);

  setEmotion(
    BOT_STATES.THINKING
  );

  try {

    const res = await api.get(
      "/bot/surprise"
    );

    const songs =
      res.data.results || [];

    addBotMessage(

      res.data.message ||
      "✨ Enjoy something unexpected!",

      songs

    );

    
    if (songs.length > 0) {

      setCurrentSong(
        songs[0]
      );

      setEmotion(
        BOT_STATES.EXCITED,
        3000
      );

    }

  } catch (err) {

    console.error(err);

    toast.error(
      "Couldn't surprise you today."
    );

  } finally {

    setLoading(false);

  }

}, [

  addBotMessage,

  setCurrentSong,

  setEmotion

]);
const discoverMood = useCallback(
  async mood => {

    setLoading(true);

    setEmotion(
      BOT_STATES.THINKING
    );

    try {

      const res =
        await api.post(
          "/bot/discover-mood",
          {
            mood
          }
        );

      addBotMessage(
    res.data.explanation,
    res.data.results);

    if (res.data.results?.length > 0) {
        setCurrentSong(res.data.results[0]);
      }

      setMemory(prev => ({
        ...prev,
        moods: [
          ...new Set([
            ...prev.moods,
            mood
          ])
        ]
      }));

      setEmotion(

  MOOD_EMOTIONS[mood] ||

  BOT_STATES.HAPPY,

  3500

);

    } catch {

      toast.error(
        "Mood discovery failed."
      );

    } finally {

      setLoading(false);

    }

  },

  [addBotMessage]
);

const generatePlaylist = useCallback(async () => {

  setLoading(true);

  setEmotion(
    BOT_STATES.THINKING
  );

  try {

    const history = messages
      .filter(msg => msg.songs)
      .flatMap(msg => msg.songs)
      .slice(-30);

    const res = await api.post(

      "/bot/daily-mix",

      {
        history,
        limit: 20
      }

    );

    addBotMessage(

      res.data.title ||
      "🎵 Your Daily Mix",

      res.data.results || []

    );

    if (res.data.results?.length > 0) {
      setCurrentSong(res.data.results[0]);
    }
    setEmotion(
      BOT_STATES.HAPPY,
      2500
    );

  } catch (err) {

    console.error(err);

    toast.error(
      "Couldn't generate Daily Mix."
    );

  } finally {

    setLoading(false);

  }

}, [

  messages,

  addBotMessage,

  setEmotion

]);

  const explainRecommendation =
  useCallback(

    async (song) => {

      try {

        const res =
          await api.post(

            "/bot/why",

            {

              history:
                messages
                  .filter(
                    msg => msg.songs
                  )
                  .flatMap(
                    msg => msg.songs
                  )
                  .slice(-20),

              song: song,

              similarity_score:
                song.recommendation_score || 0

            }

          );

        addBotMessage(

          "🧠 Why I recommended this:\n\n" +

          res.data.reasons
            .map(
              item => `• ${item}`
            )
            .join("\n")

        );

      }

      catch (err) {

        console.error(err);

        toast.error(
          "Couldn't explain recommendation."
        );

      }

    },

    [

      messages,

      addBotMessage

    ]

  );

  const maintenanceAction =
  useCallback(

    async (action) => {

      setLoading(true);

      setEmotion(
        BOT_STATES.THINKING
      );

      try {

        const res =
          await api.post(

            "/bot/maintenance",

            {
              action
            }

          );

        if (action === "find_duplicates") {

          addBotMessage(

            `🔍 Found ${
              res.data.duplicates.length
            } duplicate candidates.`

          );

        }

        else if (
          action === "metadata"
        ) {

          addBotMessage(

            `🧹 Found ${
              res.data.issues.length
            } metadata issues.`

          );

        }

        else {

          addBotMessage(

            `⚠️ Found ${
              res.data.anomalies.length
            } anomalies.`

          );

        }

      } catch (err) {

        console.error(err);

        toast.error(
          "Maintenance failed."
        );

      } finally {

        setLoading(false);

      }

    },

    [

      addBotMessage,

      setEmotion

    ]

  );

  const learnTaste = useCallback(async () => {

  setLoading(true);

  setEmotion(
    BOT_STATES.LEARNING
  );

  try {

    const history = messages
      .filter(msg => msg.songs)
      .flatMap(msg => msg.songs)
      .slice(-50);

    const res = await api.post(

      "/bot/personalized",

      {
        history,
        limit: 15
      }

    );

    addBotMessage(

      res.data.explanation ||
      "🧠 I've learned your taste profile.",

      res.data.results || []

    );
    if (res.data.results?.length > 0) {
      setCurrentSong(res.data.results[0]);
    }
    setEmotion(
      BOT_STATES.EXCITED,
      4000
    );

  } catch (err) {

    console.error(err);

    toast.error(
      "Couldn't learn your music taste."
    );

  } finally {

    setLoading(false);

  }

}, [

  messages,

  addBotMessage,

  setEmotion

]);
  const handleQuickAction =
  useCallback(
    async action => {

      switch (action) {

        case "surprise":

          await surpriseMe();
          break;

        

        case "rain":

          await discoverMood(
            "rainy"
          );

          break;
        case "romantic":
          await discoverMood("romantic");
          break;

        case "workout":
          await discoverMood("workout");
          break;


        case "learn":

          await learnTaste();
          break;

        case "fix_metadata":

          await maintenanceAction(
            "metadata"
          );
          break;
        case "duplicates":

          await  maintenanceAction(
        "find_duplicates"
    );

    break;  
        

        default:
          break;
      }

    },

    [
      surpriseMe,
      discoverMood,
      maintenanceAction,
      learnTaste
    ]
  );

  const handleSend = useCallback(

  async (text = input,forcePlay = false) => {
    console.log("========== HANDLE SEND ==========");
    console.log("text =", text);
    console.log("forcePlay =", forcePlay);
    if (!text.trim()) {
      return;
    }

    // ==========================
    // IMMEDIATE UI FEEDBACK
    // ==========================

    addUserMessage(text);

    setInput("");

    setLoading(true);

    // ==========================
    // UPDATE CONTEXT
    // ==========================

    await updateConversationContext(text);

    // ==========================
    // INITIAL EMOTION
    // ==========================

    if (
      text
        .toLowerCase()
        .includes("sing")
    ) {

      setEmotion(
        BOT_STATES.SINGING,
        3500
      );

    } else {

      setEmotion(
        BOT_STATES.THINKING
      );

    }

    try {

      // ==========================
      // SEMANTIC SEARCH
      // ==========================

      const res = await api.post(

        "/bot/semantic-search",

        {
          query: text,
          limit: 20
        }

      );

      const songs =
        res.data.results || [];

      console.log("========== SEMANTIC SEARCH ==========");
      console.log("Query:", text);
      console.log("Songs Found:", songs.length);

      if (songs.length > 0) {
          console.log("First Song:", songs[0]);
      } else {
          console.warn("No songs returned from semantic search.");
          }  

      const explanation =
        res.data.explanation ||
        "I found these tracks for you.";

      // ==========================
      // BOT RESPONSE
      // ==========================

      // ==========================
      // BOT RESPONSE & INSTANT AUTO-PLAY
      // ==========================

      addBotMessage(explanation, songs);

      // ELITE FIX 1: Fire the TTS immediately but DO NOT use 'await'.
      // This allows the code to continue instantly without waiting for the audio to download.
      speakText(explanation, "en");

      updateConversationContext(text, songs);

      setSessionStats(prev => ({
        ...prev,
        searches: prev.searches + 1
      }));

      // ELITE FIX 2: Trigger the song play immediately so we don't violate the browser's auto-play policy.
      if (songs.length > 0 && shouldAutoPlayResult(text, forcePlay)) {
        setSongs(songs); // Merges safely due to Fix 2
        setCurrentSong(songs[0]); // Instantly plays the song
        setView("home");
        setEmotion(BOT_STATES.EXCITED, 3000);

        setSessionStats(prev => ({
          ...prev,
          recommendationsPlayed: prev.recommendationsPlayed + 1
        }));
      }


      // ==========================
      // CONTEXT-AWARE EMOTIONS
      // ==========================

      else if (
        conversationContext.mood === "sad"
      ) {

        setEmotion(
          BOT_STATES.MELANCHOLY,
          4000
        );

      }

      else if (
        conversationContext.mood === "romantic"
      ) {

        setEmotion(
          BOT_STATES.LOVED,
          4000
        );

      }

      else if (
        conversationContext.mood === "workout"
      ) {

        setEmotion(
          BOT_STATES.WORKOUT,
          4000
        );

      }

      else {

        setEmotion(
          BOT_STATES.SPEAKING,
          2500
        );

      }

    }

    catch (err) {

      console.error(err);

      addBotMessage(
        "😔 I couldn't process that request."
      );

      setEmotion(
        BOT_STATES.IDLE
      );

    }

    finally {

      setLoading(false);

    }

  },

  [

    input,

    conversationContext,

    updateConversationContext,

    addBotMessage,

    addUserMessage,

    setCurrentSong,
    setSongs,

    setEmotion,

    setSessionStats,
    setView,

    speakText

  ]

);

const startVoice = useCallback(async () => {

    console.log("🎤 Mic button clicked");

    try {

        if (!voiceRecorder.isRecording()) {

            // Pause whatever's playing first — otherwise the mic picks up
            // the song audio too and mishears the command.
            pauseSong();

            setBotState(BOT_STATES.LISTENING);

            await voiceRecorder.startRecording();

            toast.success("Listening...");

            recordingTimeoutRef.current = setTimeout(async () => {

                try {

                    await voiceRecorder.stopRecording();

                    const response = await voiceRecorder.uploadRecording();

                    console.log("VOICE RESPONSE:", response);

                    setBotState(BOT_STATES.THINKING);

                    const transcript =
                        response?.voice?.normalized_text ||
                        response?.voice?.text ||
                        "";

                    if (!transcript.trim()) {

                        toast.error("I couldn't hear anything.");

                        setBotState(BOT_STATES.IDLE);

                        return;

                    }

                    setInput(
                        transcript
                    );

                    const command = response?.command || {};
                    console.log("UPLOAD RECORDING ROUTE SELECTION -> Command Object:", command);

                    // Check both backend intent flag strings and original transcript keyword fallbacks
                    const isPlayIntent = shouldAutoPlayResult(
                        transcript,
                        !!(command.intent && command.intent.toLowerCase().startsWith("play"))
                    );

                    const voiceQuery =
                        command.optimized_query ||
                        command.song ||
                        command.artist ||
                        command.album ||
                        command.playlist ||
                        transcript;

                    console.log("VOICE STREAM EXECUTION -> Query:", voiceQuery, "| Force Autoplay:", isPlayIntent);

                    await handleSend(voiceQuery, isPlayIntent);

                }

                catch (error) {

                    console.error(error);

                    toast.error("Voice processing failed.");

                } 

                finally {

                    setBotState(BOT_STATES.IDLE);

                }

            }, 5000);

        } 

    }

    catch (error) {

        console.error(error);

        toast.error("Unable to start recording.");

        setBotState(BOT_STATES.IDLE);

    }

}, [handleSend, setEmotion, pauseSong]);


const handleKeyDown =
  useCallback(
    e => {

      if (
        e.key === "Enter"
      ) {

        handleSend();

      }

    },

    [handleSend]
  );
  
  const userProfileSummary =
  useMemo(() => {

    return `
      ❤️ Genres: ${
        memory.genres.length
      }

      🌈 Moods: ${
        memory.moods.length
      }

      🎤 Artists: ${
        memory.artists.length
      }
    `;
 
  }, [memory]);


return (
    <>
      {/* Inject the CSS for the playful hover */}
      <style>{naughtyHoverCSS}</style>

      {/* =========================
           FLOATING BUTTON (Naughty Hover & Long Press)
         ========================= */}
      {!isVibePage && (
        <button
          onMouseDown={handleBotMouseDown}
          onTouchStart={handleBotTouchStart}
          style={{ top: `${botPos.y}px`, left: `${botPos.x}px` }}
          className={`${buttonClass} animate-playful cursor-grab active:cursor-grabbing`}
          aria-label="Open Vibe AI Assistant"
        >
          {/* Dynamic Gemini-style flashing glow based on bot state */}
          <div 
            className={`
              absolute inset-0 rounded-full blur-xl transition-all duration-500
              ${
                (botState === BOT_STATES.LISTENING || botState === BOT_STATES.SPEAKING)
                  ? "bg-gradient-to-r from-emerald-400 via-cyan-400 to-fuchsia-500 opacity-80 animate-pulse scale-[1.35]" 
                  : "bg-cyan-400/20 animate-pulse scale-100"
              }
            `} 
          />
          <div className="relative z-10 flex items-center justify-center w-full h-full pointer-events-none">
            <PandaAvatar state={botState} size={56} />
          </div>
        </button>
      )} 

      {/* =========================
           MAIN PAGE UI (Sidebar + Chat Layout)
         ========================= */}
      {isVibePage && (
        <div className="absolute inset-0 z-[60] w-full h-full bg-black flex overflow-hidden">

          {/* =========================
               LEFT SIDEBAR
             ========================= */}
          {/* FIX: was `hidden md:flex` (fully inaccessible on mobile). Now renders as a full-screen overlay drawer on mobile, toggled via the new header button below, and stays exactly as before (static flex column) on md+ screens. */}
          <div className={`
            ${showMobileStats ? 'flex' : 'hidden'} md:flex
            fixed md:static inset-0 z-[90] md:z-auto
            w-full md:w-64 border-r border-white/10 flex-col p-4 gap-6 bg-zinc-950 overflow-y-auto custom-scrollbar
          `}>
            {/* Mobile-only close button for the drawer */}
            <button
              onClick={() => setShowMobileStats(false)}
              className="md:hidden self-end p-2 text-zinc-400 hover:text-white"
              aria-label="Close"
            >
              <X size={20} />
            </button>

            {/* HEADER */}
            <div className="flex flex-col items-center pt-4 pb-2 text-center">
              <PandaAvatar state={botState} size={80} showStatus />
              <h2 className="text-lg font-bold mt-2 text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-emerald-400">
                Vibe AI
              </h2>
              <p className="text-xs text-zinc-400 mt-1">Your intelligent music companion</p>
            </div>

            {/* USER STATS */}
            <div className="px-2 py-3 border-y border-white/5 text-xs text-zinc-400 flex flex-col gap-1">
              <span>🔍 Searches: {sessionStats.searches}</span>
              <span>🎵 Playlists: {sessionStats.playlistsGenerated}</span>
              <span>❤️ Played: {sessionStats.recommendationsPlayed}</span>
            </div>

            {/* QUICK ACTIONS */}
            <div className="flex flex-col gap-2">
              <h3 className="text-zinc-500 text-[10px] font-bold uppercase tracking-widest px-2">
                Actions
              </h3>
              {QUICK_ACTIONS.map(action => {
                const Icon = action.icon;
                return (
                  <button
                    key={action.id}
                    onClick={() => { handleQuickAction(action.id); setShowMobileStats(false); }}
                    className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm bg-white/5 hover:bg-emerald-500/20 border border-white/5 transition-all"
                  >
                    <Icon size={16} />
                    {action.label}
                  </button>
                );
              })}
            </div>

            {/* MEMORY / TASTE PROFILE */}
            <div className="mt-auto px-2 py-4 border-t border-white/5">
              <h3 className="text-zinc-500 text-[10px] font-bold uppercase tracking-widest mb-2">
                Taste Profile
              </h3>
              <div className="text-[11px] text-zinc-400 leading-relaxed whitespace-pre-line">
                {userProfileSummary}
              </div>
            </div>
          </div>

          {/* =========================
               RIGHT PANEL (Chat)
             ========================= */}
          <div className="flex-1 flex flex-col h-full bg-black/95 backdrop-blur-3xl relative pb-20">

            {/* CLOSE BUTTON */}
            <button
              onClick={() => setView('home')}
              className="absolute top-4 right-4 z-50 w-10 h-10 rounded-full bg-white/5 hover:bg-white/10 flex items-center justify-center transition-all"
            >
              <X size={20} />
            </button>

            {/* MOBILE-ONLY HEADER (sidebar now opens as a drawer below md, via the new button) */}
            <div className="md:hidden px-6 py-5 border-b border-white/10 bg-white/[0.02] flex items-center gap-4">
              <PandaAvatar state={botState} size={56} showStatus />
              <div className="flex-1 min-w-0">
                <h2 className="text-lg font-bold tracking-wide text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-emerald-400">
                  Vibe AI
                </h2>
                <p className="text-xs text-zinc-400">Your intelligent music companion</p>
              </div>
              {/* FIX: opens the stats/quick-actions/taste-profile drawer that used to be desktop-only */}
              <button
                onClick={() => setShowMobileStats(true)}
                className="p-2 rounded-full bg-white/5 hover:bg-white/10 text-zinc-300"
                aria-label="Stats and quick actions"
              >
                <Sparkles size={18} />
              </button>
            </div>

            {/* =========================
                 CHAT MESSAGES
               ========================= */}
            <div ref={chatContainerRef} className="flex-1 overflow-y-auto custom-scrollbar px-4 py-5 space-y-4">
              {messages.map(message => (
                <div key={message.id} className={`flex ${message.type === "user" ? "justify-end" : "justify-start"}`}>

                  {/* USER MESSAGE */}
                  {message.type === "user" && (
                    <div className="max-w-[80%] rounded-3xl rounded-br-lg px-4 py-3 bg-gradient-to-br from-cyan-500 to-emerald-500 text-black font-medium shadow-lg">
                      <p className="whitespace-pre-wrap">{message.text}</p>
                    </div>
                  )}

                  {/* BOT MESSAGE */}
                  {message.type === "bot" && (
                    <div className="max-w-[90%] flex flex-col gap-3">
                      <div className="rounded-3xl rounded-bl-lg px-4 py-3 bg-white/[0.05] backdrop-blur-xl border border-white/5 shadow-lg">
                        <p className="whitespace-pre-wrap text-sm leading-relaxed">{message.text}</p>
                      </div>

                      {/* SONG RESULTS */}
                      {message.songs?.length > 0 && (
                        <div className="flex flex-col gap-3">
                          {message.songs.slice(0, 5).map(song => (
                            <div key={song.id || song.msg_id} className="bg-white/[0.04] border border-white/5 rounded-2xl p-3 hover:bg-white/[0.07] transition-all duration-300">
                              <div className="flex justify-between items-start gap-3">
                                <div className="flex-1 min-w-0">
                                  <h4 className="font-semibold truncate">{song.title}</h4>
                                  <p className="text-sm text-zinc-400 truncate">{song.artist}</p>
                                </div>
                                <div className="flex gap-2">
                                  <button
                                    onClick={() => {
                                      setCurrentSong(song);
                                      setEmotion(BOT_STATES.EXCITED, 2500);
                                    }}
                                    className="px-3 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-black text-xs font-semibold transition-all"
                                  >
                                    ▶ Play
                                  </button>
                                  <button
                                    onClick={() => explainRecommendation(song)}
                                    className="px-3 py-2 rounded-xl bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 text-xs transition-all"
                                  >
                                    🧠 Why?
                                  </button>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
              {loading && <TypingIndicator />}
            </div>

            {/* =========================
                 INPUT SECTION
               ========================= */}
            <div className="border-t border-white/10 bg-black/20 backdrop-blur-xl p-4">

              {/* VOICE VISUALIZER */}
              {botState === BOT_STATES.LISTENING && (
                <div className="mb-3">
                  <VoiceVisualizer active />
                </div>
              )}

              {/* INPUT ROW */}
              <div className="flex gap-3">
                <button
                  onClick={startVoice}
                  disabled={!voiceEnabled}
                  className={`w-12 h-12 rounded-2xl flex items-center justify-center transition-all duration-300 ${
                    botState === BOT_STATES.LISTENING
                      ? "bg-red-500 animate-pulse shadow-lg shadow-red-500/40"
                      : "bg-white/5 hover:bg-white/10"
                  }`}
                >
                  <Mic size={18} />
                </button>

                <input
                  ref={inputRef}
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask me anything... (e.g. romantic Hindi songs)"
                  className="flex-1 px-4 py-3 rounded-2xl bg-white/5 border border-white/10 outline-none focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/20 transition-all"
                />

                <button
                  onClick={() => handleSend()}
                  disabled={loading}
                  className="w-12 h-12 rounded-2xl bg-gradient-to-br from-cyan-400 to-emerald-400 text-black flex items-center justify-center font-bold hover:scale-105 active:scale-95 transition-all"
                >
                  {loading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
                </button>
              </div>

              {/* FOOTER ACTIONS */}
              <div className="mt-4 flex justify-between items-center text-[11px] text-zinc-500">
                <button onClick={generatePlaylist} className="hover:text-cyan-400 transition-colors">
                  Daily Mix
                </button>
                <button onClick={() => discoverMood("chill")} className="hover:text-cyan-400 transition-colors">
                  🌈 Chill Vibes
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default memo(MusicBot);
