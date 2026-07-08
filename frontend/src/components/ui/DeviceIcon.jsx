import { DEVICE_LABEL } from "../../lib/labels";

const DEVICE_EMOJI = { shade: "🌤️", window: "🪟", irrigation: "💧" };

function stateClass(device, state) {
  if (device === "irrigation") {
    return state === "on" ? "device-icon--on" : "device-icon--off";
  }
  if (state === "open") return "device-icon--on";
  if (state === "partial") return "device-icon--partial";
  return "device-icon--off";
}

export default function DeviceIcon({ device, state }) {
  return (
    <span
      className={`device-icon ${stateClass(device, state)}`}
      title={`${DEVICE_LABEL[device]}: ${state}`}
    >
      {DEVICE_EMOJI[device]}
    </span>
  );
}
