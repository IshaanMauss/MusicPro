import React, { useState, useMemo } from 'react';
import useMusicStore from '../musicStore';
import axios from 'axios';
import { API_URL } from '../api';
import { motion } from 'framer-motion';
import { Music2, User, Lock, ArrowRight, Sparkles, Check, X } from 'lucide-react';
import toast from 'react-hot-toast';

const Login = () => {
    const [isRegister, setIsRegister] = useState(false);
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const { login } = useMusicStore();

    // 🟢 SECURITY REGEX CONSTANTS
    const USERNAME_REGEX = /^[a-zA-Z0-9_]{3,20}$/;
    const PASSWORD_REGEX = /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$/;

    // 🟢 PASSWWORD STRENGTH CALCULATOR (User Interpretable)
    const passwordStrength = useMemo(() => {
        if (!password) return 0;
        let score = 0;
        if (password.length >= 8) score++;
        if (/[A-Za-z]/.test(password)) score++;
        if (/\d/.test(password)) score++;
        return score;
    }, [password]);

    const handleSubmit = async (e) => {
        e.preventDefault();

        // 🛡️ FRONTEND VALIDATION LOGIC
        if (isRegister) {
            if (!USERNAME_REGEX.test(username)) {
                return toast.error("Username: Use 3-20 letters, numbers, or underscores.");
            }
            if (!PASSWORD_REGEX.test(password)) {
                return toast.error("Password: Use at least 8 characters, including 1 letter and 1 number.");
            }
        }

        setIsLoading(true);
        const loadToast = toast.loading(isRegister ? "Creating account..." : "Signing in...");

        try {
            if (isRegister) {
                // 🟢 First Time User Flow
                await axios.post(`${API_URL}/auth/register`, { username, password });
                
                // Immediately log them in after registration
                await login(username, password);
                toast.success("Welcome to the vibe! Your journey starts here.", { id: loadToast });
            } else {
                // 🟢 Returning User Flow
                await login(username, password);
                toast.success("Welcome back!", { id: loadToast });
            }
        } catch (err) {
            const msg = err.response?.data?.detail || "Authentication failed";
            toast.error(msg, { id: loadToast });
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen w-full bg-[#070707] flex items-center justify-center p-4 relative overflow-hidden font-sans">
            {/* Animated Background Orbs */}
            <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-emerald-500/10 blur-[120px] rounded-full animate-pulse" />
            <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-cyan-500/10 blur-[120px] rounded-full" />

            <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="w-full max-w-md z-10"
            >
                {/* LOGO SECTION */}
                <div className="text-center mb-10">
                    <motion.div 
                        initial={{ scale: 0.5 }}
                        animate={{ scale: 1 }}
                        className="inline-flex p-4 rounded-3xl bg-gradient-to-br from-emerald-400 to-cyan-600 mb-6 shadow-[0_0_40px_rgba(16,185,129,0.3)]"
                    >
                        <Music2 size={40} className="text-black" />
                    </motion.div>
                    <h1 className="text-5xl md:text-6xl font-black tracking-tighter text-white mb-2 uppercase">
                        VIBE<span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-cyan-500">STREAM</span>
                    </h1>
                    <p className="text-zinc-500 font-medium flex items-center justify-center gap-2">
                        <Sparkles size={14} className="text-emerald-500" />
                        Premium Audio Experience
                    </p>
                </div>

                {/* LOGIN CARD */}
                <div className="bg-zinc-900/50 backdrop-blur-2xl border border-white/5 p-8 rounded-[2.5rem] shadow-2xl">
                    <form onSubmit={handleSubmit} className="space-y-6">
                        <div className="space-y-4">
                            {/* Username Input */}
                            <div className="relative group">
                                <User className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500 group-focus-within:text-emerald-500 transition-colors" size={20} />
                                <input 
                                    type="text" placeholder="Username" 
                                    className="w-full bg-black/40 border border-white/10 rounded-2xl py-4 pl-12 pr-4 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all placeholder:text-zinc-600"
                                    onChange={e => setUsername(e.target.value)}
                                    value={username}
                                    required
                                />
                            </div>

                            {/* Password Input */}
                            <div className="relative group">
                                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500 group-focus-within:text-emerald-500 transition-colors" size={20} />
                                <input 
                                    type="password" placeholder="Password" 
                                    className="w-full bg-black/40 border border-white/10 rounded-2xl py-4 pl-12 pr-4 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all placeholder:text-zinc-600"
                                    onChange={e => setPassword(e.target.value)}
                                    value={password}
                                    required
                                />
                            </div>

                            {/* 🟢 VISUAL STRENGTH METER (For Registration) */}
                            {isRegister && password.length > 0 && (
                                <div className="px-1 space-y-2">
                                    <div className="flex gap-1.5 h-1">
                                        {[1, 2, 3].map((level) => (
                                            <div 
                                                key={level}
                                                className={`flex-1 rounded-full transition-all duration-500 ${
                                                    passwordStrength >= level 
                                                    ? (passwordStrength === 1 ? 'bg-red-500' : passwordStrength === 2 ? 'bg-yellow-500' : 'bg-emerald-500')
                                                    : 'bg-zinc-800'
                                                }`}
                                            />
                                        ))}
                                    </div>
                                    <p className="text-[10px] text-zinc-500 uppercase tracking-widest font-bold">
                                        Security: {passwordStrength === 1 ? 'Weak' : passwordStrength === 2 ? 'Medium' : 'Strong'}
                                    </p>
                                </div>
                            )}
                        </div>

                        <motion.button 
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            disabled={isLoading}
                            type="submit"
                            className="w-full bg-gradient-to-r from-emerald-500 to-cyan-500 text-black py-4 rounded-2xl font-bold flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/20 disabled:opacity-50 transition-all"
                        >
                            {isRegister ? "Create Account" : "Sign In"}
                            <ArrowRight size={20} />
                        </motion.button>

                        <div className="text-center">
                            <button 
                                type="button"
                                onClick={() => {
                                    setIsRegister(!isRegister);
                                    setPassword('');
                                }}
                                className="text-zinc-400 text-sm hover:text-emerald-400 transition-colors font-medium"
                            >
                                {isRegister ? "Already part of the stream? Login" : "New to VibeStream? Create Account"}
                            </button>
                        </div>
                    </form>
                </div>
            </motion.div>
        </div>
    );
};

export default Login;