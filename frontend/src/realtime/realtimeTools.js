// Realtime API 전용 tool 스키마.
//
// 주의: OpenAI Realtime의 session.update 안 tools 형식은 Chat Completions의 tools
// 형식과 다르다 (flat { type, name, description, parameters } — "function" 으로
//한 번 더 감싸지 않음). 그래서 백엔드 chat_agent 의 tool 스키마를 그대로 재사용하지
// 않고, 여기서 Realtime 형식으로 따로 정의한다 (voice_feature_backend.md 3절의
// "스키마 이중 관리" 경고와 동일한 이유).
export const REALTIME_TOOLS = [
  {
    type: "function",
    name: "control_device",
    description:
      "온실 장비(차광막/창문/관수)를 제어한다. 어떤 온실인지 확실할 때만 호출하고, " +
      "확실하지 않으면 호출하지 말고 먼저 사용자에게 되물어라.",
    parameters: {
      type: "object",
      properties: {
        greenhouse_id: { type: "integer", description: "대상 온실 번호." },
        device: {
          type: "string",
          enum: ["window", "shade", "irrigation"],
          description: "window=창문, shade=차광막, irrigation=관수",
        },
        action: {
          type: "string",
          enum: ["open", "close", "on", "off"],
          description: "window/shade는 open|close, irrigation은 on|off",
        },
      },
      required: ["greenhouse_id", "device", "action"],
    },
  },
  {
    type: "function",
    name: "query_data",
    description: "센서/생산/알림 데이터를 조회한다.",
    parameters: {
      type: "object",
      properties: {
        greenhouse_id: { type: "integer", description: "대상 온실 번호." },
        target: {
          type: "string",
          enum: ["temperature", "humidity", "state", "alerts", "production"],
          description: "조회할 항목",
        },
      },
      required: ["target"],
    },
  },
];

export const VOICE_SESSION_INSTRUCTIONS =
  "당신은 스마트팜 농가를 돕는 친근한 AI 음성 도우미입니다. 고령 농가 사용자를 대상으로 하니 " +
  "항상 짧고 쉬운 말로, 친절한 말투로 답하세요. 한국어로만 응답하세요.\n" +
  "장비(차광막/창문/관수)를 조작하려 하거나 센서/생산 데이터를 물으면 반드시 제공된 도구를 " +
  "호출해 실제로 처리하고, 도구 없이 임의로 답하지 마세요. 지원하지 않는 장비/동작이면 " +
  "무엇이 안 되는지 안내하세요. 어떤 온실인지, 어떤 동작인지 불명확하면 실행하지 말고 먼저 " +
  "되물으세요. 텍스트 채팅과 같은 성격의 도우미처럼, 판단 기준과 말투를 일관되게 유지하세요.";
