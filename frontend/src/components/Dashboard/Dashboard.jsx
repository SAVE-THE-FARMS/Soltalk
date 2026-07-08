export default function Dashboard({ farm }) {
  const { greenhouses } = farm;

  return (
    <div className="dashboard">
      <ul className="dashboard__debug-list">
        {greenhouses.map((gh) => (
          <li key={gh.id}>
            {gh.name} — {gh.status}
          </li>
        ))}
      </ul>
    </div>
  );
}
