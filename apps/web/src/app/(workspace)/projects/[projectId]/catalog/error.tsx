"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="page-stack">
      <section className="surface-card section-card">
        <p className="page-eyebrow">Catalog</p>
        <h1 className="page-title">Could not load the project catalog</h1>
        <p className="page-description">{error.message}</p>
        <div className="button-row">
          <button className="button-primary" onClick={reset} type="button">
            Retry
          </button>
        </div>
      </section>
    </div>
  );
}
