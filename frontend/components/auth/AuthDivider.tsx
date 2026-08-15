export function AuthDivider({ label = "or continue with email" }: { label?: string }) {
  return (
    <div className="relative flex items-center py-2" role="separator">
      <div className="h-px flex-1 bg-border" />
      <span className="px-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</span>
      <div className="h-px flex-1 bg-border" />
    </div>
  );
}
