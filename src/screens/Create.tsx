import { Icon } from '../components/Icon'
import { Meter } from '../components/ui'
import { useStore } from '../state/store'

/**
 * Création d'une connaissance, en cinq temps :
 *
 *   sujet → présentation → chapitres → rédaction → validation
 *
 * L'auteur n'écrit qu'une phrase. Le modèle en tire un titre, une
 * description, une catégorie et un programme, puis prépare la façon dont
 * chaque chapitre sera interrogé. Tout est écrit en base au fur et à
 * mesure, en brouillon : une création interrompue se reprend, et rien
 * n'entre au feed sans avoir été relu.
 */
export function Create() {
  const { s, t, user } = useStore()

  // CONDAMNÉE. Le pipeline de création parle le schéma d'avant la
  // reconstruction du catalogue — `category`, `theme.owner_id`,
  // `chapter.generated_prompt` ont disparu, et ses sept routes rendent
  // 500. Plutôt que de laisser l'auteur écrire un sujet pour se faire
  // renvoyer « Internal Server Error », l'écran le dit d'entrée.
  if (!user?.is_admin) return <ReserveeAdmin />

  return (
    <div className="screen">
      {/* Pas de flèche de retour ici : on sort par le rail ou la barre,
          que cet écran garde. */}
      <div className="nav-head create-head" style={{ paddingBottom: 10 }}>
        <span className="nav-title" style={{ flex: 1 }}>
          {t.newLearning}
        </span>
        {/* La planche compte les étapes en clair plutôt qu'en traits :
            « 2 / 5 » dit aussi où l'on est, pas seulement ce qui reste. */}
        <span className="create-count">{s.createStep} / 3</span>
      </div>

      {/* L'attente de l'appel 1 prend tout l'écran : il n'y a rien à
          montrer tant que la présentation n'existe pas. Celle de l'appel
          2, en revanche, se peuple chapitre par chapitre — elle vit donc
          dans l'étape 3 plutôt qu'à sa place. */}
      {s.thinking && s.createStep === 1 ? <Thinking /> : null}
      {s.genLoading ? <Writing /> : null}
      {!s.genLoading && !(s.thinking && s.createStep === 1) && (
        <>
          {s.createStep === 1 ? <StepSubject /> : null}
          {s.createStep === 2 ? <StepPlan /> : null}
          {s.createStep === 3 ? <StepValidate /> : null}
        </>
      )}
    </div>
  )
}

/**
 * L'écran fermé.
 *
 * On garde la porte plutôt que de la murer : le bouton « + » est posé
 * dans le rail, sur chaque carte et sur l'accueil, et le faire
 * disparaître partout laisserait croire à une régression. On dit ce
 * qu'il en est, et on rend la sortie.
 */
function ReserveeAdmin() {
  const { t, go } = useStore()
  return (
    <div className="screen">
      <div className="nav-head create-head" style={{ paddingBottom: 10 }}>
        <span className="nav-title" style={{ flex: 1 }}>
          {t.newLearning}
        </span>
      </div>
      <div
        className="stack"
        style={{
          flex: 1,
          justifyContent: 'center',
          alignItems: 'center',
          gap: 16,
          padding: '0 32px',
          textAlign: 'center',
        }}
      >
        <Icon name="alert" size={30} color="var(--sc-text3)" />
        <p className="display" style={{ fontSize: 24 }}>
          {t.createClosedTitle}
        </p>
        <p className="body" style={{ fontSize: 15, maxWidth: '38ch' }}>
          {t.createClosedLine}
        </p>
        <button
          className="btn-primary"
          style={{ width: 240, marginTop: 6 }}
          onClick={() => go('exo', 'q')}
        >
          {t.createClosedBack}
        </button>
      </div>
    </div>
  )
}

function ErrorNote({ message }: { message: string }) {
  return (
    <div
      className="card-sunk"
      style={{ display: 'flex', gap: 12, alignItems: 'flex-start', borderColor: 'var(--sc-miss-line)' }}
    >
      <Icon name="alert" size={18} stroke={1.9} color="var(--sc-miss-line)" style={{ marginTop: 2 }} />
      <span style={{ fontSize: 14, lineHeight: 1.6, color: 'var(--sc-text2)' }}>{message}</span>
    </div>
  )
}

/**
 * Étape 1 — le sujet.
 *
 * Une phrase suffit, et c'est tout ce qu'on demande : ni titre, ni
 * catégorie, ni cours. Les trois arrivaient avant l'analyse et
 * l'utilisateur devait deviner sa propre taxonomie ; c'est maintenant
 * le modèle qui propose et lui qui corrige.
 */
function StepSubject() {
  const { s, set, goCreate, proposeKnowledge, t } = useStore()
  const tooShort = s.subject.trim().length < 3

  const go = async () => {
    if (await proposeKnowledge()) goCreate(2)
  }

  return (
    <div className="screen-scroll page create-flow stack" style={{ gap: 16 }}>
      <p className="display" style={{ fontSize: 28 }}>
        {t.whatToLearn}
      </p>
      <p className="body" style={{ fontSize: 16 }}>
        {t.subjectHint}
      </p>

      <label className="field">
        <textarea
          className="textarea"
          rows={2}
          placeholder={t.subjectPlaceholder}
          value={s.subject}
          onChange={(e) => set({ subject: e.target.value })}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey && !tooShort) {
              e.preventDefault()
              void go()
            }
          }}
        />
      </label>

      {s.genError && <ErrorNote message={s.genError} />}

      <button
        className="btn-primary"
        onClick={() => void go()}
        disabled={tooShort}
        style={{ opacity: tooShort ? 0.5 : 1 }}
      >
        <Icon name="sparkle" size={18} stroke={1.9} />
        {t.propose}
      </button>
    </div>
  )
}

/** L'attente de l'appel 1 : rien à montrer tant que rien n'existe. */
function Thinking() {
  const { t } = useStore()
  return (
    <div className="screen-scroll stack gen-wait" style={{ flex: 1, padding: '10px 22px 26px' }}>
      <span className="gen-pulse">
        <span className="gen-disc">
          <Icon name="sparkle" size={30} stroke={1.8} />
        </span>
      </span>
      <p className="display" style={{ fontSize: 26 }}>
        {t.thinkingHead}
      </p>
      <p className="body" style={{ fontSize: 17, maxWidth: '30ch' }}>
        {t.thinkingLine}
      </p>
    </div>
  )
}

/**
 * Étape 2 — la présentation proposée.
 *
 * La pastille « Proposé » dit vrai pour la première fois : le titre, la
 * description, la catégorie et les mots-clés viennent du modèle, et sont
 * déjà en base en brouillon. Tout reste corrigeable.
 */
/**
 * La proposition : ce que le modèle a compris, et le programme.
 *
 * Cet écran portait la présentation, un second portait le plan — les
 * mêmes chapitres, relistés. Ils n'en font plus qu'un.
 */
function StepPlan() {
  const { s, set, startWriting, t } = useStore()
  const k = s.knowledge
  if (!k) return null

  const vivants = k.chapters.filter((c) => c.status !== 'rejected')
  const prets = vivants.filter((c) => c.type_question || c.error)

  return (
    <div className="screen-scroll page create-flow stack" style={{ gap: 16 }}>
      <div className="stack" style={{ gap: 10 }}>
        <span className="chip-proposed">
          <Icon name="sparkle" size={14} stroke={2} />
          {t.proposed}
        </span>
        <p className="display" style={{ fontSize: 28 }}>
          {t.yourKnowledge}
        </p>
        <p className="create-lead">{t.presentLead}</p>
      </div>

      <label className="field">
        <span className="field-label">{t.title}</span>
        <input
          className="input-sunk"
          value={s.draftTitle}
          onChange={(e) => set({ draftTitle: e.target.value })}
        />
      </label>

      <label className="field">
        <span className="field-label">{t.description}</span>
        <textarea
          className="textarea-sunk"
          rows={4}
          value={s.draftDescription}
          onChange={(e) => set({ draftDescription: e.target.value })}
        />
      </label>

      <div className="field">
        <span className="field-label">{t.category}</span>
        <span className="pick-row">{k.category_label}</span>
        {/* Une catégorie inventée par le modèle n'entre pas au catalogue
            sans être retenue : le dire ici évite qu'on la découvre plus
            tard sans savoir d'où elle vient. */}
        {k.category_is_new && <span className="field-note">{t.newCategoryNote(k.category_label)}</span>}
      </div>

      {k.tags.length > 0 && (
        <div className="field">
          <span className="field-label">{t.tagsDetected}</span>
          <div className="wrap">
            {k.tags.map((tag) => (
              <span key={tag} className="chip chip-flat">
                {tag}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="field">
        <span className="field-label">
          {t.programme} · {t.chapterCount(k.chapters.length)}
        </span>

        {/* Le programme se lisait ici, puis se relisait à l'écran suivant
            pour n'y gagner qu'un type de question et un exemple. Les deux
            viennent désormais se poser DANS ces cartes, à mesure qu'ils
            s'écrivent : un écran de moins, et le même contenu. */}
        <div className="stack" style={{ gap: 10 }}>
          {vivants.map((c) => (
            <div key={c.id} className="card" style={{ gap: 8 }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span
                  className="dot"
                  style={{
                    width: 8,
                    height: 8,
                    flex: 'none',
                    background: c.error
                      ? 'var(--sc-miss-line)'
                      : c.type_question
                        ? 'var(--sc-primary)'
                        : 'var(--sc-line)',
                  }}
                />
                <span className="prog-title">
                  {c.position}. {c.title}
                </span>
              </span>

              {c.description && <span className="prog-line">{c.description}</span>}

              {c.type_question && (
                <span style={{ fontSize: 13, color: 'var(--sc-text3)' }}>
                  {t.askedAs} <b>{t[TYPE_LABEL[c.type_question]] as string}</b>
                </span>
              )}

              {c.example && (
                <div className="card-sunk" style={{ gap: 8 }}>
                  <span className="eyebrow">{t.exampleLabel}</span>
                  <span style={{ fontSize: 15, lineHeight: 1.45, color: 'var(--sc-text)' }}>
                    {c.example.prompt}
                  </span>
                  <span className="stack" style={{ gap: 5 }}>
                    {c.example.options.map((o, i) => (
                      <PreviewOption key={i} label={o} correct={i === c.example!.correct_index} />
                    ))}
                  </span>
                </div>
              )}

              {c.error && (
                <span style={{ fontSize: 13, color: 'var(--sc-text2)' }}>{t.chapterFailed}</span>
              )}
            </div>
          ))}
        </div>
      </div>

      {s.thinking && (
        <div className="stack" style={{ width: '100%', gap: 8 }}>
          <Meter pct={vivants.length ? Math.round((prets.length / vivants.length) * 100) : 0} />
          <span style={{ fontSize: 14, color: 'var(--sc-text3)' }}>
            {t.preparedCount(prets.length, vivants.length)}
          </span>
        </div>
      )}

      {s.genError && <ErrorNote message={s.genError} />}

      {/* Un seul bouton, et il est TOUJOURS là — y compris après une
          préparation interrompue, où l'écran d'avant n'en montrait aucun
          et laissait le brouillon sans issue. Le relancer est sans
          danger : les chapitres déjà prêts sont sautés.

          Collé au bas de la fenêtre : le programme fait cinq cartes, et
          la seule action de l'écran ne doit pas se mériter au
          défilement. */}
      <div className="create-foot">
        <button className="btn-primary" onClick={() => void startWriting()} disabled={s.thinking}>
          <Icon name="sparkle" size={18} stroke={1.9} />
          {s.thinking ? t.preparingHead : t.writeExercises}
        </button>
      </div>
    </div>
  )
}

const TYPE_LABEL: Record<string, keyof ReturnType<typeof useStore>['t']> = {
  qcm: 'typeQcm',
  complete: 'typeComplete',
  find_error: 'typeFindError',
  short_answer: 'typeShortAnswer',
  cloze: 'typeCloze',
}

/**
 * Étape 3 — comment chaque chapitre sera interrogé.
 *
 * Un chapitre est prêt quand il porte un type ; en échec quand il porte
 * une erreur ; en cours sinon. Aucun compteur n'est deviné, et la
 * relance ne reprend que ce qui manque — un chapitre déjà écrit, et
 * peut-être corrigé à la main, n'est pas réécrit.
 */
/**
 * L'attente de génération.
 *
 * Le suivi remonte les brouillons au fur et à mesure : la barre compte
 * des exercices réellement écrits, pas un temps deviné. Dès qu'il y en
 * a, on propose de passer à la validation sans attendre la fin — et de
 * retourner s'entraîner, puisque la rédaction continue sans l'écran.
 */
function Writing() {
  const { s, go, goCreate, draftExercises, t } = useStore()
  const written = draftExercises.length
  const pct = s.genCount > 0 ? Math.min(100, Math.round((written / s.genCount) * 100)) : 0

  return (
    <div
      className="screen-scroll stack create-flow"
      style={{ flex: 1, padding: '10px 22px 26px', gap: 18 }}
    >
      {written > 0 && (
        <div className="contact-note">
          <span style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span
              style={{
                width: 34,
                height: 34,
                flex: 'none',
                borderRadius: 999,
                background: 'var(--sc-primary)',
                color: 'var(--sc-on-primary)',
                display: 'grid',
                placeItems: 'center',
              }}
            >
              <Icon name="check" size={17} stroke={2.6} />
            </span>
            <span style={{ fontSize: 16, fontWeight: 700, color: 'var(--sc-text)' }}>
              {t.genReady(written)}
            </span>
          </span>
          <span style={{ fontSize: 15, lineHeight: 1.55, color: 'var(--sc-text2)' }}>
            {t.genReadyLine}
          </span>
          <button
            className="btn-primary"
            style={{ minHeight: 46, fontSize: 15 }}
            onClick={() => goCreate(3)}
          >
            {t.goToValidation}
          </button>
        </div>
      )}

      <div className="stack gen-wait">
        <span className="gen-pulse">
          <span className="gen-disc">
            <Icon name="sparkle" size={30} stroke={1.8} />
          </span>
        </span>
        <p className="display" style={{ fontSize: 26 }}>
          {t.writingHead}
        </p>
        <p className="body" style={{ fontSize: 17, maxWidth: '30ch' }}>
          {t.writingSub}
        </p>
        <div className="stack" style={{ width: '100%', gap: 8 }}>
          <Meter pct={pct} />
          <span
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: 14,
              color: 'var(--sc-text3)',
            }}
          >
            <span>{t.writtenCount(written)}</span>
            <span>{s.genCount}</span>
          </span>
        </div>
      </div>

      <button className="btn-outline" onClick={() => go('exo', 'q')}>
        {t.keepPracticing}
      </button>
    </div>
  )
}

function StepValidate() {
  const { s, go, generate, draftExercises, reviewExercise, validateAll, t } = useStore()
  const current = draftExercises[0]

  return (
    <div
      className="stack create-flow"
      style={{ flex: 1, padding: '10px 22px 26px', gap: 14, minHeight: 0 }}
    >
      <span style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <span className="eyebrow">{t.toReview}</span>
        <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--sc-text3)' }}>
          {t.validatedCount(s.validated, draftExercises.length)}
        </span>
      </span>

      <div className="screen-scroll stack" style={{ gap: 12 }}>
        {s.genError && <ErrorNote message={s.genError} />}

        {!current && !s.genError && (
          <div className="card">
            <p className="display" style={{ fontSize: 22 }}>
              {s.validated > 0 ? t.allReviewed : t.nothingToReview}
            </p>
            <p className="body" style={{ fontSize: 15 }}>
              {s.validated > 0
                ? t.willJoinFeed(s.validated)
                : t.launchFromPrevious}
            </p>
          </div>
        )}

        {current && (
          <div className="card" style={{ boxShadow: 'var(--shadow-md)' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span className="dot" style={{ width: 8, height: 8, background: 'var(--amber-500)' }} />
              <span className="eyebrow">{current.type_question}</span>
            </span>
            <p className="display" style={{ fontSize: 21, lineHeight: 1.3 }}>
              {current.prompt}
            </p>
            {current.body && (
              <p className="body" style={{ fontSize: 15 }}>
                {current.body}
              </p>
            )}
            <span className="stack" style={{ gap: 7 }}>
              {current.options.map((o, i) => (
                <PreviewOption key={i} label={o.label} correct={i === current.correct_index} />
              ))}
            </span>
            <div
              className="stack"
              style={{
                padding: '13px 15px',
                borderRadius: 12,
                background: 'var(--amber-50)',
                border: '1px solid var(--amber-300)',
                gap: 6,
              }}
            >
              <span
                className="eyebrow"
                style={{ display: 'flex', alignItems: 'center', gap: 7, color: 'var(--gold-700)' }}
              >
                <Icon name="alert" size={14} stroke={2} />
                {t.explanationToReview}
              </span>
              <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6, color: 'var(--amber-ink)' }}>
                {current.exp_text}
              </p>
            </div>
          </div>
        )}
      </div>

      <div className="stack" style={{ gap: 9, flex: 'none' }}>
        {/* Tout valider est l'action première : le critique a déjà écarté
            ce qui ne tenait pas, et exiger un tap par exercice — quatorze
            à la dernière création — faisait payer une relecture déjà
            faite. Celle-ci reste offerte juste en dessous. */}
        {draftExercises.length > 1 && (
          <>
            <span style={{ fontSize: 13, lineHeight: 1.5, color: 'var(--sc-text3)' }}>
              {t.reviewedByCritic}
            </span>
            <button
              className="btn-primary"
              style={{ minHeight: 50, fontSize: 16 }}
              onClick={validateAll}
            >
              <Icon name="check" size={17} stroke={2.4} />
              {t.validateAll} · {draftExercises.length}
            </button>
            <span className="eyebrow">{t.validateOneByOne}</span>
          </>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 8 }}>
          <button
            className="btn-primary"
            style={{ minHeight: 50, background: 'var(--success-500)', color: '#FFFFFF', fontSize: 16 }}
            onClick={() => current && reviewExercise(current.id, 'validated')}
            disabled={!current}
          >
            <Icon name="check" size={17} stroke={2.4} />
            {t.validate}
          </button>
          <button
            className="square-btn"
            onClick={() => current && reviewExercise(current.id, 'rejected')}
            disabled={!current}
            aria-label={t.discard}
          >
            <Icon name="trash" size={18} stroke={1.9} color="var(--sc-text3)" />
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
          <button
            onClick={generate}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              background: 'transparent',
              border: 0,
              fontSize: 14,
              fontWeight: 700,
              color: 'var(--sc-primary)',
              cursor: 'pointer',
            }}
          >
            <Icon name="undo" size={16} stroke={2} />
            {t.regenerate}
          </button>
          <button
            onClick={() => go('publish')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 7,
              height: 30,
              padding: '0 12px',
              borderRadius: 999,
              background: 'var(--sc-sunk)',
              border: '1px solid var(--sc-line)',
              fontSize: 12,
              fontWeight: 700,
              color: 'var(--sc-text3)',
              cursor: 'pointer',
            }}
          >
            <Icon name="lock" size={13} stroke={2} />
            {t.privatePublish}
          </button>
        </div>
      </div>
    </div>
  )
}

function PreviewOption({ label, correct }: { label: string; correct?: boolean }) {
  return (
    <span
      style={{
        padding: '11px 14px',
        borderRadius: 10,
        border: `1px solid ${correct ? 'var(--sc-good-line)' : 'var(--sc-line)'}`,
        background: correct ? 'var(--sc-good-bg)' : 'transparent',
        fontSize: 15,
        fontWeight: correct ? 700 : 600,
        color: correct ? 'var(--sc-good-ink)' : 'var(--sc-text2)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}
    >
      {label}
      {correct && <Icon name="check" size={16} stroke={2.6} />}
    </span>
  )
}

