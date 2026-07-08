const TYPE_ICON = { auto: "🤖", manual: "🖐️" };

export default function HistoryTimeline({ entries }) {
  return (
    <ul className="history-timeline">
      {entries.map((entry, i) => (
        <li key={i}>
          <span className="history-timeline__time">{entry.time}</span>
          <span className="history-timeline__icon">{TYPE_ICON[entry.type]}</span>
          <span>{entry.text}</span>
        </li>
      ))}
    </ul>
  );
}
