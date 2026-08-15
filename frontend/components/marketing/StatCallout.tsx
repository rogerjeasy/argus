export function StatCallout({ value, label }: { value: string; label: string }) {
  return (
    <div className="rounded-xl border border-border bg-card p-6 text-center shadow-sm sm:p-8">
      <p className="text-4xl font-semibold tracking-tight text-primary sm:text-5xl">{value}</p>
      <p className="mt-2 text-sm text-muted-foreground sm:text-base">{label}</p>
    </div>
  );
}
