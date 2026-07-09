// 챗 세션 id 관리. 재질문 맥락(히스토리)을 유지하려면 매 요청에 같은 session_id를 보내야 한다.
const STORAGE_KEY = "soltalk_session_id";

export function getSessionId() {
  let id = localStorage.getItem(STORAGE_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(STORAGE_KEY, id);
  }
  return id;
}
