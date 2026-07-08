export default function DemoControls({ onReset, onEscalate }) {
  return (
    <div className="demo-controls">
      <button className="demo-controls__btn" onClick={onEscalate}>
        데모: 경고→위험 승격
      </button>
      <button className="demo-controls__btn demo-controls__btn--reset" onClick={onReset}>
        리셋
      </button>
    </div>
  );
}
