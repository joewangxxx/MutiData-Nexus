export default function Loading() {
  return (
    <div className="page-stack" aria-busy="true">
      <div className="surface-card section-card">
        <p className="page-eyebrow">Catalog</p>
        <h1 className="page-title">Loading project catalog</h1>
        <p className="page-description">Fetching datasets and source assets from the controller API.</p>
      </div>
      <div className="surface-card section-card">
        <p className="muted-text">Loading datasets and asset rows...</p>
      </div>
    </div>
  );
}
