import { useState, useRef, useEffect, useCallback } from 'react';
import { Mic, Square, X, Loader2, Volume2, ShieldAlert } from 'lucide-react';
import { audioApi } from '../../services/audio';
import { useChatStore } from '../../stores/chatStore';
import { motion, AnimatePresence } from 'framer-motion';

interface VoiceSessionProps {
    onClose: () => void;
    selectedModel: string;
}

export function VoiceSession({ onClose, selectedModel }: VoiceSessionProps) {
    const {
        sendMessage,
        isStreaming,
        streamingContent,
        messages,
        activeConversationId,
        stopGeneration
    } = useChatStore();

    const [isRecording, setIsRecording] = useState(false);
    const [isTranscribing, setIsTranscribing] = useState(false);
    const [isPlaying, setIsPlaying] = useState(false);
    const [volume, setVolume] = useState(0);

    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);
    const audioContextRef = useRef<AudioContext | null>(null);
    const analyserRef = useRef<AnalyserNode | null>(null);
    const animationFrameRef = useRef<number | undefined>(undefined);
    const isComponentMounted = useRef(true);

    // Track the ID of the last processed message to avoid re-playing
    const [lastPlayedMessageId, setLastPlayedMessageId] = useState<string | number | null>(null);

    // Initialize processing the *most recent* assistant message immediately, if not already played
    useEffect(() => {
        isComponentMounted.current = true;
        return () => {
            isComponentMounted.current = false;
            if (audioContextRef.current) {
                audioContextRef.current.close().catch((err: Error) => console.error(err));
            }
            if (animationFrameRef.current) {
                cancelAnimationFrame(animationFrameRef.current);
            }
            if (mediaRecorderRef.current && isRecording) {
                mediaRecorderRef.current.stop();
                mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
            }
        };
    }, [isRecording]);

    // Visualizer loop for STT (microphone input)
    const drawVisualizer = useCallback(() => {
        if (!analyserRef.current || !isComponentMounted.current) return;
        const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
        analyserRef.current.getByteFrequencyData(dataArray);

        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
            sum += dataArray[i];
        }
        const average = sum / dataArray.length;
        // Normalize volume 0-1
        setVolume(Math.min(1, average / 128));

        if (isRecording) {
            animationFrameRef.current = requestAnimationFrame(drawVisualizer);
        }
    }, [isRecording]);

    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            audioContextRef.current = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
            const source = audioContextRef.current.createMediaStreamSource(stream);
            analyserRef.current = audioContextRef.current.createAnalyser();
            analyserRef.current.fftSize = 256;
            source.connect(analyserRef.current);

            const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
            mediaRecorderRef.current = mediaRecorder;
            audioChunksRef.current = [];

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunksRef.current.push(event.data);
                }
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
                try {
                    setIsTranscribing(true);
                    const text = await audioApi.transcribe(audioBlob);
                    if (text.trim() && isComponentMounted.current) {
                        sendMessage(text.trim(), selectedModel);
                    }
                } catch (e) {
                    console.error('Transcription failed:', e);
                    import('../../stores/uiStore').then(({ useUIStore }) => {
                        useUIStore.getState().addToast('Transcription failed. Check microphone permissions.', 'error');
                    });
                } finally {
                    if (isComponentMounted.current) {
                        setIsTranscribing(false);
                    }
                }
            };

            mediaRecorder.start();
            setIsRecording(true);
            drawVisualizer();
        } catch (e) {
            console.error('Failed to start recording:', e);
            import('../../stores/uiStore').then(({ useUIStore }) => {
                useUIStore.getState().addToast('Microphone access denied', 'error');
            });
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
            setIsRecording(false);
            setVolume(0);
            if (animationFrameRef.current) {
                cancelAnimationFrame(animationFrameRef.current);
            }
        }
    };

    const toggleRecording = () => {
        if (isRecording) {
            stopRecording();
        } else {
            startRecording();
        }
    };

    // Monitor chat store to auto-play assistant responses
    useEffect(() => {
        if (isStreaming || isRecording || isTranscribing) return; // Wait until stream finishes

        const lastMessage = messages[messages.length - 1];
        if (lastMessage && lastMessage.role === 'assistant' && lastMessage.id !== lastPlayedMessageId && lastMessage.content) {
            setLastPlayedMessageId(lastMessage.id ?? Date.now());
            setIsPlaying(true);
            audioApi.playTTS(lastMessage.content)
                .catch(err => {
                    console.error("Auto TTS Failed: ", err);
                    import('../../stores/uiStore').then(({ useUIStore }) => {
                        useUIStore.getState().addToast('Failed to play audio response', 'error');
                    });
                })
                .finally(() => {
                    if (isComponentMounted.current) {
                        setIsPlaying(false);
                    }
                });
        }
    }, [messages, isStreaming, isRecording, isTranscribing, lastPlayedMessageId]);


    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 20 }}
                className="absolute inset-0 z-50 bg-[#080810]/95 backdrop-blur-xl flex flex-col items-center justify-center"
            >
                <button
                    onClick={onClose}
                    className="absolute top-6 right-6 p-2 rounded-full bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
                >
                    <X className="w-6 h-6" />
                </button>

                <div className="flex-1 w-full max-w-2xl mx-auto flex flex-col items-center justify-center p-8">
                    <div className="relative mb-12 flex items-center justify-center">
                        {/* Visualizer Ring */}
                        <motion.div
                            animate={{
                                scale: isRecording ? 1 + volume * 0.5 : 1,
                                opacity: isRecording ? 0.3 + volume * 0.5 : 0.1,
                            }}
                            transition={{ type: "spring", stiffness: 300, damping: 20 }}
                            className={`absolute w-64 h-64 rounded-full ${isPlaying ? 'bg-emerald-500' : isStreaming ? 'bg-purple-500' : 'bg-indigo-500'} blur-3xl`}
                        />

                        {/* Main Action Button */}
                        <button
                            onClick={isStreaming || isPlaying ? stopGeneration : toggleRecording}
                            disabled={isTranscribing}
                            className={`relative z-10 w-28 h-28 rounded-full flex items-center justify-center shadow-2xl transition-all ${isTranscribing ? 'bg-indigo-600/50 cursor-not-allowed' :
                                isPlaying || isStreaming ? 'bg-purple-600 hover:bg-purple-700' :
                                    isRecording ? 'bg-red-500 hover:bg-red-600' : 'bg-indigo-600 hover:bg-indigo-500'
                                }`}
                        >
                            {isTranscribing ? (
                                <Loader2 className="w-10 h-10 text-white animate-spin" />
                            ) : isStreaming ? (
                                <ShieldAlert className="w-10 h-10 text-white animate-pulse" /> // Represents Agent thinking
                            ) : isPlaying ? (
                                <Volume2 className="w-10 h-10 text-white animate-pulse" />
                            ) : isRecording ? (
                                <Square className="w-10 h-10 text-white fill-white" />
                            ) : (
                                <Mic className="w-12 h-12 text-white" />
                            )}
                        </button>
                    </div>

                    <div className="text-center h-24">
                        <h2 className="text-2xl font-semibold text-white mb-2 tracking-wide w-full truncate">
                            {isTranscribing ? 'Transcribing...' :
                                isStreaming ? 'Agent is thinking...' :
                                    isPlaying ? 'Agent is speaking...' :
                                        isRecording ? 'Listening...' : 'Tap to speak'}
                        </h2>

                        {isStreaming && streamingContent && (
                            <p className="text-gray-400 text-lg max-w-md mx-auto truncate">
                                {streamingContent}
                            </p>
                        )}
                        {(!isStreaming && !isRecording && !isTranscribing) && (
                            <p className="text-gray-500 text-sm">
                                {messages.length > 0 ? messages[messages.length - 1]?.content : "Say hello to your agent!"}
                            </p>
                        )}
                    </div>

                    {/* Conversation Context Pill */}
                    {activeConversationId && (
                        <div className="mt-8 px-4 py-2 bg-white/5 rounded-full border border-white/10 text-xs text-gray-400 font-mono tracking-wider">
                            VOICE SESSION ACTIVE
                        </div>
                    )}
                </div>
            </motion.div>
        </AnimatePresence>
    );
}
