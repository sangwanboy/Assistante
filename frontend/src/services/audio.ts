const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8321') + '/api';

export const audioApi = {
    transcribe: async (blob: Blob): Promise<string> => {
        const formData = new FormData();
        formData.append('file', blob, 'audio.webm');

        const res = await fetch(`${API_BASE_URL}/audio/transcribe`, {
            method: 'POST',
            body: formData,
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(`Failed to transcribe audio: ${err.detail || res.statusText}`);
        }

        const data = await res.json();
        return data.text;
    },

    playTTS: async (text: string, voice: string = 'alloy'): Promise<void> => {
        const res = await fetch(`${API_BASE_URL}/audio/tts`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text, voice }),
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(`Failed to generate TTS: ${err.detail || res.statusText}`);
        }

        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);

        audio.onended = () => {
            URL.revokeObjectURL(url);
        };

        await audio.play();
    }
};
