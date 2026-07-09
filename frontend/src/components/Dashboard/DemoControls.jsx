export default function DemoControls({ onReset }) {
  return (
    <div className="demo-controls">
      <button className="demo-controls__btn demo-controls__btn--reset" onClick={onReset}>
        리셋
      </button>
    </div>
  );
}
