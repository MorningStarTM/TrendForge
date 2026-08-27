export function Spinner({ className = "" }: { className?: string }) {
  return <span className={`spinner ${className}`} aria-label="Loading" role="status" />;
}
