import { useCallback, useEffect, useRef, useState } from "react";

const SILENCE_THRESHOLD = 0.02; // 0~1 RMS 기준, 이 아래면 "무음"
const SILENCE_DURATION_MS = 2500; // 무음이 이만큼 지속되면 자동 종료

export function useRecorder({ onStop, onError }) {
  const [isRecording, setIsRecording] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const mediaRecorderRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);
  const silenceStartRef = useRef(null);
  const rafRef = useRef(null);
  const timerRef = useRef(null);

  const cleanup = useCallback(() => {
    cancelAnimationFrame(rafRef.current);
    clearInterval(timerRef.current);
    streamRef.current?.getTracks().forEach((t) => t.stop());
    audioContextRef.current?.close();
    audioContextRef.current = null;
    streamRef.current = null;
    silenceStartRef.current = null;
  }, []);

  const stop = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
  }, []);

  const monitorVolume = useCallback(() => {
    const analyser = analyserRef.current;
    if (!analyser) return;
    const data = new Uint8Array(analyser.fftSize);
    analyser.getByteTimeDomainData(data);
    const rms = Math.sqrt(
      data.reduce((sum, v) => sum + ((v - 128) / 128) ** 2, 0) / data.length
    );

    if (rms < SILENCE_THRESHOLD) {
      if (silenceStartRef.current == null) silenceStartRef.current = performance.now();
      else if (performance.now() - silenceStartRef.current > SILENCE_DURATION_MS) {
        stop();
        return;
      }
    } else {
      silenceStartRef.current = null;
    }
    rafRef.current = requestAnimationFrame(monitorVolume);
  }, [stop]);

  const start = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 2048;
      source.connect(analyser);
      audioContextRef.current = audioContext;
      analyserRef.current = analyser;

      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => chunksRef.current.push(e.data);
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        cleanup();
        setIsRecording(false);
        onStop?.(blob);
      };
      mediaRecorderRef.current = recorder;
      recorder.start();

      setIsRecording(true);
      setElapsedSeconds(0);
      silenceStartRef.current = null;
      timerRef.current = setInterval(() => setElapsedSeconds((s) => s + 1), 1000);
      rafRef.current = requestAnimationFrame(monitorVolume);
    } catch (e) {
      onError?.(e);
    }
  }, [cleanup, monitorVolume, onStop, onError]);

  useEffect(() => cleanup, [cleanup]);

  return { isRecording, elapsedSeconds, start, stop };
}
