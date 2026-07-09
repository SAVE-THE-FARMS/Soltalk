// OpenAI Realtime API 브라우저 WebRTC 연결 (저수준).
//
// 흐름: 백엔드에서 임시(ephemeral) 키 발급 → 마이크 트랙 확보 → RTCPeerConnection 생성 →
// data channel("oai-events") 개설 → SDP offer 를 OpenAI에 직접 POST → answer 적용.
//
// 보안: 여기서 쓰는 키는 백엔드가 매번 새로 발급하는 짧은 유효시간의 임시 키뿐이다.
// 일반 OPENAI_API_KEY 는 절대 프론트 코드/환경변수에 두지 않는다 — 백엔드 env에만 존재.
import { createRealtimeSession } from "../api";

const REALTIME_CALLS_URL = "https://api.openai.com/v1/realtime/calls";
const DATA_CHANNEL_LABEL = "oai-events"; // OpenAI 공식 WebRTC 예제 기준 (임의 하드코딩 아님)

function waitForDataChannelOpen(dc, timeoutMs = 8000) {
  if (dc.readyState === "open") return Promise.resolve();
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      dc.removeEventListener("open", onOpen);
      reject(new Error("data_channel_open_timeout"));
    }, timeoutMs);
    function onOpen() {
      clearTimeout(timer);
      dc.removeEventListener("open", onOpen);
      resolve();
    }
    dc.addEventListener("open", onOpen);
  });
}

function extractEphemeralKey(session) {
  // 백엔드 응답 계약(voice_feature_backend.md 2.1): { client_secret, expires_at }.
  // OpenAI 원본 client_secrets.create() 응답은 { value, expires_at } 형태라 백엔드가
  // 그대로 중계할 경우를 대비해 문자열/객체 두 형태 다 받아준다.
  const secret = session?.client_secret;
  if (typeof secret === "string") return secret;
  if (secret && typeof secret.value === "string") return secret.value;
  return null;
}

export class RealtimeConnectionError extends Error {
  constructor(message, cause) {
    super(message);
    this.name = "RealtimeConnectionError";
    this.cause = cause;
  }
}

/**
 * @param {object} opts
 * @param {(event: object) => void} opts.onServerEvent - data channel으로 온 이벤트(JSON 파싱됨)
 * @param {(stream: MediaStream) => void} opts.onRemoteStream - AI 음성 재생용 원격 오디오 스트림
 * @param {(state: RTCPeerConnectionState) => void} [opts.onConnectionStateChange]
 * @returns {Promise<{ dc: RTCDataChannel, close: () => void, sendEvent: (event: object) => void }>}
 */
export async function connectRealtime({ onServerEvent, onRemoteStream, onConnectionStateChange }) {
  let session;
  try {
    session = await createRealtimeSession();
  } catch (err) {
    throw new RealtimeConnectionError("realtime_session_failed", err);
  }
  const ephemeralKey = extractEphemeralKey(session);
  if (!ephemeralKey) {
    throw new RealtimeConnectionError("realtime_session_missing_client_secret");
  }

  let micStream;
  try {
    micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (err) {
    throw new RealtimeConnectionError("microphone_permission_denied", err);
  }

  const pc = new RTCPeerConnection();
  const cleanupFns = [() => micStream.getTracks().forEach((t) => t.stop())];

  micStream.getTracks().forEach((track) => pc.addTrack(track, micStream));

  pc.ontrack = (e) => {
    onRemoteStream?.(e.streams[0]);
  };

  if (onConnectionStateChange) {
    pc.onconnectionstatechange = () => onConnectionStateChange(pc.connectionState);
  }

  const dc = pc.createDataChannel(DATA_CHANNEL_LABEL);
  dc.addEventListener("message", (e) => {
    try {
      onServerEvent?.(JSON.parse(e.data));
    } catch {
      // 서버 이벤트가 JSON이 아닌 경우 — 무시 (연결 자체를 끊지 않음)
    }
  });

  function close() {
    cleanupFns.forEach((fn) => {
      try {
        fn();
      } catch {
        // cleanup 중 예외는 무시 — 이미 끊긴 리소스일 수 있음
      }
    });
    try {
      dc.close();
    } catch {
      // no-op
    }
    try {
      pc.close();
    } catch {
      // no-op
    }
  }

  try {
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);

    const sdpResponse = await fetch(REALTIME_CALLS_URL, {
      method: "POST",
      body: offer.sdp,
      headers: {
        Authorization: `Bearer ${ephemeralKey}`,
        "Content-Type": "application/sdp",
      },
    });
    if (!sdpResponse.ok) {
      throw new Error(`SDP 교환 실패: ${sdpResponse.status}`);
    }
    const answerSdp = await sdpResponse.text();
    await pc.setRemoteDescription({ type: "answer", sdp: answerSdp });

    // dc는 SDP 교환이 끝나도 바로 "open"이 아닐 수 있다 — 이 상태에서 곧바로
    // session.update를 보내면 sendEvent가 조용히 씹어버려서, tool/한국어 지침 없이
    // 대화가 시작되는 심각한 문제가 생긴다. 열릴 때까지 여기서 반드시 기다린다.
    await waitForDataChannelOpen(dc);
  } catch (err) {
    close();
    throw new RealtimeConnectionError("webrtc_connect_failed", err);
  }

  function sendEvent(event) {
    if (dc.readyState !== "open") return;
    dc.send(JSON.stringify(event));
  }

  function setMuted(muted) {
    micStream.getAudioTracks().forEach((track) => {
      track.enabled = !muted;
    });
  }

  return { dc, pc, close, sendEvent, setMuted };
}
