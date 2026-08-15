import { Reveal } from "./Reveal";
import { StatCallout } from "./StatCallout";

const CONTRAST_ROWS = [
  {
    exists: "Narrates a sign, a document, a scene — one description at a time.",
    argus: "Holds a goal across every step until the task is actually done.",
  },
  {
    exists: "Reads a platform number aloud, and stops there.",
    argus: "Cross-checks that number against a live feed, and replans the moment reality disagrees.",
  },
  {
    exists: "Connects you to a human volunteer to make the call for you.",
    argus: "Places the call itself, after you say yes.",
  },
  {
    exists: "Tells you what a form says.",
    argus: "Fills it, asks aloud for the one field it can't infer, and submits it.",
  },
] as const;

export function ProblemSection() {
  return (
    <section id="problem" aria-labelledby="problem-heading" className="border-t border-border bg-secondary/40">
      <Reveal className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-28 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 id="problem-heading" className="text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
            Narration is solved. Action isn&apos;t.
          </h2>
          <p className="mt-4 text-pretty text-lg text-muted-foreground">
            Every existing tool in this space can tell a blind or low-vision person what&apos;s in front of them.
            None of them hold a goal, act on it, and see it through.
          </p>
        </div>

        <div className="mx-auto mt-12 grid max-w-4xl grid-cols-1 gap-4 sm:grid-cols-3">
          <StatCallout value="2.2B" label="people worldwide live with some degree of vision impairment" />
          <StatCallout value="43M" label="are blind, per the WHO and IAPB" />
          <StatCallout value="0 of 5" label="leading tools hold a goal and act on it — Argus is the first" />
        </div>

        <div className="mx-auto mt-16 max-w-4xl overflow-x-auto rounded-xl border border-border bg-card shadow-sm">
          <table className="w-full min-w-[480px] table-fixed text-left">
            <thead>
              <tr className="border-b border-border">
                <th scope="col" className="w-1/2 px-5 py-4 text-sm font-semibold text-muted-foreground sm:px-6">
                  What exists today
                </th>
                <th scope="col" className="w-1/2 px-5 py-4 text-sm font-semibold text-primary sm:px-6">
                  What Argus does
                </th>
              </tr>
            </thead>
            <tbody>
              {CONTRAST_ROWS.map((row) => (
                <tr key={row.exists} className="border-b border-border last:border-0">
                  <td className="text-pretty px-5 py-4 text-sm text-muted-foreground sm:px-6 sm:text-base">{row.exists}</td>
                  <td className="text-pretty px-5 py-4 text-sm text-foreground sm:px-6 sm:text-base">{row.argus}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Reveal>
    </section>
  );
}
