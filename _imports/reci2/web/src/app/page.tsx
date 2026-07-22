import Link from "next/link";

const features = [
  {
    code: "F01",
    title: "Clasifica vidrio y plástico",
    body: "Cámara + MobileNet v2 + sistema experto. Solo se abre la compuerta correcta.",
  },
  {
    code: "F04",
    title: "Llámame aquí",
    body: "Pide a Reci que vaya al punto fijo más cercano a ti desde la app.",
  },
  {
    code: "F05",
    title: "Tracking en tiempo real",
    body: "Ve dónde está Reci en el mapa del campus, actualizado al segundo.",
  },
  {
    code: "F06",
    title: "Rachas y puntos",
    body: "Cada reciclaje suma. Mantén tu racha y compite con el resto del campus.",
  },
  {
    code: "F07",
    title: "Canjea cupones",
    body: "Convierte tus puntos en cupones digitales del campus.",
  },
  {
    code: "F08",
    title: "Reci te saluda por nombre",
    body: "Reconocimiento facial opt-in. Tú decides si activarlo y puedes apagarlo cuando quieras.",
  },
];

export default function Home() {
  return (
    <div className="flex flex-1 flex-col">
      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-16 px-6 py-16 sm:px-10 sm:py-24">
        <header className="flex flex-col gap-6">
          <span className="inline-flex w-fit items-center gap-2 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-3 py-1 text-xs font-medium tracking-wide text-emerald-700 dark:text-emerald-300">
            <span aria-hidden className="size-2 rounded-full bg-emerald-500" />
            RECI-2026-PI · PAO 2026-01
          </span>
          <h1 className="max-w-3xl text-balance text-4xl font-semibold tracking-tight sm:text-6xl">
            Reciclaje inteligente que se{" "}
            <span className="text-emerald-600 dark:text-emerald-400">
              acerca a ti
            </span>
            .
          </h1>
          <p className="max-w-2xl text-pretty text-lg leading-relaxed text-zinc-600 dark:text-zinc-300">
            Reci es un robot autónomo de reciclaje para el campus PUCE Sede
            Manabí. Identifica el material que depositas, se mueve entre puntos
            fijos cuando lo llamas, y te recompensa por mantener la racha.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/app"
              className="inline-flex h-11 items-center justify-center rounded-full bg-emerald-600 px-6 text-sm font-medium text-white shadow-sm transition hover:bg-emerald-700"
            >
              Abrir la app
            </Link>
            <Link
              href="/admin"
              className="inline-flex h-11 items-center justify-center rounded-full border border-zinc-300 px-6 text-sm font-medium text-zinc-700 transition hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-900"
            >
              Dashboard admin
            </Link>
          </div>
        </header>

        <section aria-labelledby="features-heading" className="flex flex-col gap-8">
          <h2
            id="features-heading"
            className="text-sm font-semibold uppercase tracking-widest text-zinc-500 dark:text-zinc-400"
          >
            Lo que hace Reci
          </h2>
          <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((f) => (
              <li
                key={f.code}
                className="flex flex-col gap-3 rounded-2xl border border-zinc-200 bg-white p-6 transition hover:border-emerald-400 hover:shadow-sm dark:border-zinc-800 dark:bg-zinc-900 dark:hover:border-emerald-500"
              >
                <span className="font-mono text-xs text-emerald-600 dark:text-emerald-400">
                  {f.code}
                </span>
                <h3 className="text-base font-semibold">{f.title}</h3>
                <p className="text-sm leading-relaxed text-zinc-600 dark:text-zinc-300">
                  {f.body}
                </p>
              </li>
            ))}
          </ul>
        </section>

        <footer className="mt-auto flex flex-col gap-2 border-t border-zinc-200 pt-6 text-xs text-zinc-500 dark:border-zinc-800 dark:text-zinc-400">
          <p>
            Pontificia Universidad Católica del Ecuador — Sede Manabí ·
            Ingeniería de Software · 5to semestre
          </p>
          <p>
            Equipo: Paula Márquez · Axel Hernández · Leonela Sornoza · Andrea
            Campaña
          </p>
        </footer>
      </main>
    </div>
  );
}
