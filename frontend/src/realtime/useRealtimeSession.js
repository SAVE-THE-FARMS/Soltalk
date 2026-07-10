// 실시간 음성 모드 오케스트레이션 훅.
//
// 책임: 연결 생명주기(연결/재연결 1회/종료) 관리, data channel 이벤트 해석,
// function-call → 백엔드 중계 → 결과 재주입, 자막을 채팅 히스토리 콜백으로 전달.
// WebRTC 저수준 연결은 realtimeClient.js 가 담당.
// 지침/도구(tool) 스키마는 백엔드가 임시 키 발급 시점에 세션에 바인딩한다
// (backend/app/services/realtime_session.py) — 여기서 session.update 로 보내지 않는다.
// 과거에 프론트에서 보내던 session.update 는 payload 형식 문제(session.type 누락)로
// OpenAI가 조용히 거부해서 "도구 없는 일반 챗봇"이 되는 사고가 있었다(실측).
import { useCallback, useEffect, useRef, useState } from "react";
import { executeRealtimeTool } from "../api";
import { connectRealtime, RealtimeConnectionError } from "./realtimeClient";

export const VOICE_STATUS = {
  IDLE: "idle", // 연결 대기
  CONNECTING: "connecting", // 연결 중
  LISTENING: "listening", // 듣고 있어요
  THINKING: "thinking", // 생각 중이에요
  SPEAKING: "speaking", // 말하고 있어요
  RECONNECTING: "reconnecting", // 다시 연결 중
  ERROR: "error", // 오류 발생
  FALLBACK: "fallback", // 텍스트 모드로 전환됨
};

const STATUS_LABEL = {
  [VOICE_STATUS.IDLE]: "연결 대기",
  [VOICE_STATUS.CONNECTING]: "연결 중이에요",
  [VOICE_STATUS.LISTENING]: "듣고 있어요",
  [VOICE_STATUS.THINKING]: "생각 중이에요",
  [VOICE_STATUS.SPEAKING]: "말하고 있어요",
  [VOICE_STATUS.RECONNECTING]: "다시 연결 중이에요",
  [VOICE_STATUS.ERROR]: "오류가 발생했어요",
  [VOICE_STATUS.FALLBACK]: "텍스트 모드로 전환했어요",
};

const ERROR_GUIDANCE = {
  realtime_session_failed: "음성 연결에 실패했어요. 텍스트로 계속할 수 있어요.",
  realtime_session_missing_client_secret: "음성 연결에 실패했어요. 텍스트로 계속할 수 있어요.",
  microphone_permission_denied: "마이크 권한이 필요해요. 권한을 허용하거나 텍스트로 입력해 주세요.",
  webrtc_connect_failed: "다시 연결하지 못했어요. 텍스트 모드로 전환했어요.",
  remote_audio_playback_failed: "소리 재생에 문제가 있었어요. 텍스트로 계속할 수 있어요.",
};

export function useRealtimeSession({ onUserMessage, onAssistantMessage } = {}) {
  const [status, setStatus] = useState(VOICE_STATUS.IDLE);
  const [errorText, setErrorText] = useState("");
  const [muted, setMutedState] = useState(false);

  const connectionRef = useRef(null);
  const audioElRef = useRef(null);
  const reconnectAttemptedRef = useRef(false);
  const mutedRef = useRef(false);
  // start()/stop() 마다 올라가는 세대 번호. WebRTC 연결은 1초 이상 걸릴 수 있어서,
  // "연결 중 종료 버튼을 누른" 다음에야 이전 연결 시도가 뒤늦게 성공/실패로 돌아오는
  // 경우가 실제로 생긴다 — epoch가 안 맞으면 그 결과는 버리고 리소스만 정리한다.
  const epochRef = useRef(0);
  const assistantTranscriptRef = useRef("");
  const pendingActionsRef = useRef([]); // 이번 응답 turn에서 실행된 control_device 결과들
  const functionCallNamesRef = useRef(new Map()); // call_id -> tool name
  const functionCallArgsRef = useRef(new Map()); // call_id -> 누적 arguments 문자열

  const cleanup = useCallback(() => {
    connectionRef.current?.close();
    connectionRef.current = null;
    if (audioElRef.current) {
      audioElRef.current.srcObject = null;
    }
    functionCallNamesRef.current.clear();
    functionCallArgsRef.current.clear();
    assistantTranscriptRef.current = "";
  }, []);

  const enterFallback = useCallback(
    (reasonKey) => {
      cleanup();
      setErrorText(ERROR_GUIDANCE[reasonKey] || ERROR_GUIDANCE.webrtc_connect_failed);
      setStatus(VOICE_STATUS.FALLBACK);
    },
    [cleanup]
  );

  const runToolCall = useCallback(
    async (callId, name, argsJson) => {
      let parsedArgs;
      try {
        parsedArgs = argsJson ? JSON.parse(argsJson) : {};
      } catch {
        connectionRef.current?.sendEvent({
          type: "conversation.item.create",
          item: {
            type: "function_call_output",
            call_id: callId,
            output: JSON.stringify({ ok: false, reason: "invalid_arguments" }),
          },
        });
        connectionRef.current?.sendEvent({ type: "response.create" });
        return;
      }

      let outputPayload;
      try {
        const { result } = await executeRealtimeTool(name, parsedArgs);
        outputPayload = result;
        if (name === "control_device") {
          // 텍스트로 바로 밀어넣지 않고 모아뒀다가, 이번 turn의 음성 응답 자막이 완성되는
          // 시점(response.output_audio_transcript.done)에 같은 말풍선에 합쳐 붙인다 —
          // 기존 /api/chat 흐름처럼 "응답 문장 + ✅ 액션 표시"가 한 메시지여야 하기 때문.
          pendingActionsRef.current.push({
            device: parsedArgs.device,
            greenhouse_id: parsedArgs.greenhouse_id,
            action: parsedArgs.action,
            success: Boolean(result?.ok),
          });
        }
      } catch {
        // 백엔드 호출 자체가 실패해도 실패 사실을 감추지 않고 그대로 모델에 전달 —
        // AI가 "제어에 실패했어요" 라고 말할 수 있게 한다.
        outputPayload = { ok: false, reason: "backend_unreachable" };
      }

      connectionRef.current?.sendEvent({
        type: "conversation.item.create",
        item: {
          type: "function_call_output",
          call_id: callId,
          output: JSON.stringify(outputPayload),
        },
      });
      connectionRef.current?.sendEvent({ type: "response.create" });
    },
    []
  );

  const handleServerEvent = useCallback(
    (event) => {
      switch (event.type) {
        case "input_audio_buffer.speech_started":
          setStatus(VOICE_STATUS.LISTENING);
          break;

        case "input_audio_buffer.speech_stopped":
          setStatus(VOICE_STATUS.THINKING);
          break;

        // 사용자 발화 자막 (백엔드/OpenAI 세션 설정에 input transcription이 켜져 있을 때만 옴 —
        // 안 오면 사용자 발화는 채팅 이력에 안 남고 AI 응답만 남는다. TODO 참고).
        case "conversation.item.input_audio_transcription.completed":
          if (event.transcript) onUserMessage?.(event.transcript);
          break;

        case "response.output_audio_transcript.delta":
          setStatus(VOICE_STATUS.SPEAKING);
          assistantTranscriptRef.current += event.delta || "";
          break;

        case "response.output_audio_transcript.done": {
          const text = event.transcript || assistantTranscriptRef.current;
          const actions = pendingActionsRef.current;
          assistantTranscriptRef.current = "";
          pendingActionsRef.current = [];
          if (text || actions.length > 0) onAssistantMessage?.(text || "", actions);
          setStatus(VOICE_STATUS.LISTENING);
          break;
        }

        case "response.output_item.added":
          if (event.item?.type === "function_call") {
            const callId = event.item.call_id || event.item.id;
            functionCallNamesRef.current.set(callId, event.item.name);
            functionCallArgsRef.current.set(callId, "");
          }
          break;

        case "response.function_call_arguments.delta": {
          const callId = event.call_id || event.item_id;
          const prev = functionCallArgsRef.current.get(callId) || "";
          functionCallArgsRef.current.set(callId, prev + (event.delta || ""));
          break;
        }

        case "response.function_call_arguments.done": {
          const callId = event.call_id || event.item_id;
          const name = functionCallNamesRef.current.get(callId) || event.name;
          const argsJson = event.arguments ?? functionCallArgsRef.current.get(callId) ?? "";
          functionCallNamesRef.current.delete(callId);
          functionCallArgsRef.current.delete(callId);
          if (name) {
            runToolCall(callId, name, argsJson);
          } else {
            // 이름을 못 찾았어도 침묵하면 모델이 함수 결과를 영원히 기다리며 멈출 수 있다 —
            // 실패로라도 응답해서 "그건 안 돼요" 라고 말을 잇게 한다.
            connectionRef.current?.sendEvent({
              type: "conversation.item.create",
              item: {
                type: "function_call_output",
                call_id: callId,
                output: JSON.stringify({ ok: false, reason: "unknown_tool" }),
              },
            });
            connectionRef.current?.sendEvent({ type: "response.create" });
          }
          break;
        }

        case "error":
        case "response.error":
          // 세션을 끊는 치명적 오류가 아니라, 방금 보낸 이벤트 하나가 잘못됐다는 신호인 경우가
          // 많다(OpenAI 문서 기준) — 연결은 유지하고 상태만 잠깐 ERROR로 보여준다. 다음
          // speech_started/stopped 이벤트가 오면 자연히 LISTENING/THINKING으로 되돌아간다.
          setStatus(VOICE_STATUS.ERROR);
          setErrorText(event.error?.message || "일시적인 오류가 있었어요.");
          break;

        default:
          break;
      }
    },
    [onUserMessage, onAssistantMessage, runToolCall]
  );

  const attachRemoteStream = useCallback((stream) => {
    if (!audioElRef.current) return;
    audioElRef.current.srcObject = stream;
    audioElRef.current.play().catch(() => {
      // 자동재생 차단(모바일 등) — 텍스트 자막은 계속 보여야 하니 fallback 시키지는 않고,
      // 소리가 안 나올 수 있다는 사실만 안내한다. 사용자가 화면을 한 번 터치하면 보통 풀린다.
      setErrorText(ERROR_GUIDANCE.remote_audio_playback_failed);
    });
  }, []);

  const connect = useCallback(
    async (isRetry) => {
      const epoch = epochRef.current;
      setStatus(isRetry ? VOICE_STATUS.RECONNECTING : VOICE_STATUS.CONNECTING);
      setErrorText("");
      try {
        const connection = await connectRealtime({
          onServerEvent: handleServerEvent,
          onRemoteStream: attachRemoteStream,
          onConnectionStateChange: (state) => {
            if (epoch !== epochRef.current) return; // 이미 종료/재시작된 세션 — 무시
            if (state !== "failed" && state !== "disconnected") return;
            connectionRef.current?.close();
            connectionRef.current = null;
            if (!reconnectAttemptedRef.current) {
              reconnectAttemptedRef.current = true;
              connect(true);
            } else {
              enterFallback("webrtc_connect_failed");
            }
          },
        });

        if (epoch !== epochRef.current) {
          // 연결 도중 사용자가 종료(또는 재시작)했다 — 방금 막 성립된 연결은 바로 정리.
          connection.close();
          return;
        }
        connectionRef.current = connection;
        connection.setMuted(mutedRef.current);
        // 지침/도구는 백엔드가 발급한 임시 키에 이미 바인딩되어 있음 — 추가 설정 불필요.
        reconnectAttemptedRef.current = false;
        setStatus(VOICE_STATUS.LISTENING);
      } catch (err) {
        if (epoch !== epochRef.current) return; // 이미 종료/재시작된 세션 — 결과 버림
        const key = err instanceof RealtimeConnectionError ? err.message : "webrtc_connect_failed";
        if (!isRetry && key !== "microphone_permission_denied" && !reconnectAttemptedRef.current) {
          reconnectAttemptedRef.current = true;
          connect(true);
          return;
        }
        enterFallback(key);
      }
    },
    [handleServerEvent, attachRemoteStream, enterFallback]
  );

  const start = useCallback(() => {
    epochRef.current += 1;
    reconnectAttemptedRef.current = false;
    connect(false);
  }, [connect]);

  const stop = useCallback(() => {
    epochRef.current += 1;
    cleanup();
    setStatus(VOICE_STATUS.IDLE);
    setErrorText("");
  }, [cleanup]);

  const toggleMute = useCallback(() => {
    setMutedState((prev) => {
      const next = !prev;
      mutedRef.current = next;
      connectionRef.current?.setMuted(next);
      return next;
    });
  }, []);

  // 지금은 ChatScreen이 항상 마운트 상태로 유지되지만(App.jsx가 CSS로만 숨김), 이 훅이
  // 다른 곳에서 조건부로 렌더링되게 바뀌는 경우를 대비한 안전망 — 마이크가 켜진 채로
  // 컴포넌트가 사라지는 걸 막는다. setState는 부르지 않는다(unmount 이후 경고 방지).
  useEffect(() => {
    return () => {
      epochRef.current += 1;
      cleanup();
    };
  }, [cleanup]);

  return {
    status,
    statusLabel: STATUS_LABEL[status],
    errorText,
    muted,
    start,
    stop,
    toggleMute,
    audioElRef,
  };
}
