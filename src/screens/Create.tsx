import { useState } from 'react'
import { Icon } from '../components/Icon'
import { Checkbox } from '../components/ui'
import { EXERCISE_TYPES } from '../data/content'
import { useStore } from '../state/store'

/**
 * Création de thème : dépôt du Markdown → classement → types et volume
 * → rédaction → validation. Chaque proposition reste corrigeable, et
 * rien n'entre au feed sans avoir été relu.
 */
export function Create() {
  const { s, go, goCreate, t } = useStore()
  const back = () => (s.createStep > 1 ? goCreate(s.createStep - 1) : go('picker'))

  return (
    <div className="screen">
      <div className="nav-head" style={{ paddingBottom: 10 }}>
        <button className="icon-btn" onClick={back} aria-label={t.back}>
          <Icon name="chevronLeft" size={22} stroke={1.9} />
        </button>
        <span className="nav-title" style={{ flex: 1 }}>
          {t.newTheme}
        </span>
        <span style={{ display: 'flex', gap: 5 }}>
          {[1, 2, 3, 4].map((n) => (
            <span
              key={n}
              style={{
                width: 22,
                height: 4,
                borderRadius: 999,
                background: n <= s.createStep ? 'var(--sc-primary)' : 'var(--sc-line)',
              }}
            />
          ))}
        </span>
      </div>

      {s.genLoading ? <Writing /> : null}
      {!s.genLoading && s.createStep === 1 ? <StepDrop /> : null}
      {!s.genLoading && s.createStep === 2 ? <StepClassify /> : null}
      {!s.genLoading && s.createStep === 3 ? <StepTypes /> : null}
      {!s.genLoading && s.createStep === 4 ? <StepValidate /> : null}
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

function StepDrop() {
  const { s, set, goCreate, createDraft, categories, t } = useStore()
  const [busy, setBusy] = useState(false)

  const analyse = async () => {
    setBusy(true)
    // La catégorie se choisit à l'étape suivante ; on prend la première
    // par défaut pour que le thème existe côté serveur dès maintenant.
    if (!s.draftCategoryId && categories[0]) set({ draftCategoryId: categories[0].id })
    const ok = await createDraft()
    setBusy(false)
    if (ok) goCreate(2)
  }

  return (
    <div className="screen-scroll stack" style={{ padding: '10px 22px 30px', gap: 16 }}>
      <p className="display" style={{ fontSize: 28 }}>
        {t.dropWhatYouHave}
      </p>

      <label
        className="stack"
        style={{
          padding: '20px 18px',
          borderRadius: 16,
          border: '1.5px dashed var(--sc-line)',
          background: 'var(--sc-surface)',
          alignItems: 'center',
          gap: 12,
          textAlign: 'center',
          cursor: 'text',
        }}
      >
        <span style={{ display: 'flex', gap: 10 }}>
          <DropIcon name="file" bg="var(--sky-50)" color="var(--sky-500)" />
          <DropIcon name="text" bg="var(--violet-50)" color="var(--violet-500)" />
          <DropIcon name="mic" bg="var(--rose-50)" color="var(--rose-500)" />
        </span>
        <span className="stack" style={{ gap: 4 }}>
          <span style={{ fontSize: 16, fontWeight: 700, color: 'var(--sc-text)' }}>
            {t.pasteMarkdown}
          </span>
          <span style={{ fontSize: 14, lineHeight: 1.5, color: 'var(--sc-text3)' }}>
            {t.pasteMarkdownSub}
          </span>
        </span>
        <textarea
          className="textarea"
          rows={5}
          style={{ width: '100%', marginTop: 4 }}
          placeholder={'# Titre du cours\n\nUn accord majeur se compose de…'}
          value={s.draftMarkdown}
          onChange={(e) => set({ draftMarkdown: e.target.value })}
        />
      </label>

      <label className="field">
        <span className="eyebrow">{t.title}</span>
        <input
          className="input"
          placeholder="Accords de guitare — bases"
          value={s.draftTitle}
          onChange={(e) => set({ draftTitle: e.target.value })}
        />
      </label>

      <label className="field">
        <span className="eyebrow">{t.description}</span>
        <textarea
          className="textarea"
          rows={3}
          placeholder="Les accords ouverts, leurs tierces, et les erreurs classiques de doigté."
          value={s.draftDescription}
          onChange={(e) => set({ draftDescription: e.target.value })}
        />
      </label>

      {s.genError && <ErrorNote message={s.genError} />}

      <button
        className="btn-primary"
        onClick={() => void analyse()}
        disabled={busy || s.draftMarkdown.trim().length < 40 || s.draftTitle.trim().length < 2}
        style={{
          opacity: busy || s.draftMarkdown.trim().length < 40 || s.draftTitle.trim().length < 2 ? 0.5 : 1,
        }}
      >
        <Icon name="sparkle" size={18} stroke={1.9} />
        {busy ? t.oneMoment : t.analyse}
      </button>
    </div>
  )
}

function StepClassify() {
  const { s, set, goCreate, categories, t } = useStore()
  const category = categories.find((c) => c.id === s.draftCategoryId) ?? categories[0]
  const [tagDraft, setTagDraft] = useState('')

  return (
    <div className="screen-scroll stack" style={{ padding: '10px 22px 30px', gap: 18 }}>
      <div className="stack" style={{ gap: 8 }}>
        <span
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            alignSelf: 'flex-start',
            height: 28,
            padding: '0 12px',
            borderRadius: 999,
            background: 'var(--sc-primary-soft)',
            color: 'var(--sc-primary)',
            fontSize: 12,
            fontWeight: 700,
          }}
        >
          <Icon name="sparkle" size={14} stroke={2} />
          {t.proposed}
        </span>
        <p className="display" style={{ fontSize: 28 }}>
          {t.hereIsClassing}
        </p>
      </div>

      <div className="stack" style={{ gap: 10 }}>
        <span className="eyebrow">{t.category}</span>
        <select
          className="input"
          value={s.draftCategoryId || ''}
          onChange={(e) => set({ draftCategoryId: Number(e.target.value), draftSubCategoryId: null })}
        >
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.label}
            </option>
          ))}
        </select>

        <span className="eyebrow" style={{ marginTop: 6 }}>
          {t.subCategory}
        </span>
        <select
          className="input"
          value={s.draftSubCategoryId ?? ''}
          onChange={(e) =>
            set({ draftSubCategoryId: e.target.value ? Number(e.target.value) : null })
          }
        >
          <option value="">{t.none}</option>
          {category?.sub_categories.map((sc) => (
            <option key={sc.id} value={sc.id}>
              {sc.label}
            </option>
          ))}
        </select>
      </div>

      <div className="stack" style={{ gap: 10 }}>
        <span className="eyebrow">{t.tags}</span>
        <div className="wrap">
          {s.draftTags.map((tag) => (
            <span key={tag} className="chip" style={{ height: 36, cursor: 'default', paddingRight: 8 }}>
              {tag}
              <button
                className="hit-44"
                onClick={() => set({ draftTags: s.draftTags.filter((t) => t !== tag) })}
                aria-label={`${t.discard} ${tag}`}
                style={{
                  width: 20,
                  height: 20,
                  borderRadius: 999,
                  border: 0,
                  background: 'var(--sc-sunk)',
                  display: 'grid',
                  placeItems: 'center',
                  cursor: 'pointer',
                  color: 'var(--sc-text3)',
                }}
              >
                <Icon name="minus" size={11} stroke={2.6} />
              </button>
            </span>
          ))}
        </div>
        <input
          className="input"
          placeholder={t.addTagHint}
          value={tagDraft}
          onChange={(e) => setTagDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && tagDraft.trim()) {
              set({ draftTags: [...new Set([...s.draftTags, tagDraft.trim()])] })
              setTagDraft('')
            }
          }}
        />
      </div>

      <button className="btn-primary" onClick={() => goCreate(3)}>
        {t.continue}
      </button>
    </div>
  )
}

function StepTypes() {
  const { s, set, toggleFlag, generate, t } = useStore()

  return (
    <div className="screen-scroll stack" style={{ padding: '10px 22px 30px', gap: 16 }}>
      <p className="display" style={{ fontSize: 28 }}>
        {t.whichTypes}
      </p>

      <div className="stack" style={{ gap: 9 }}>
        {EXERCISE_TYPES.map((ty, i) => {
          const on = Boolean(s.typesOn[i])
          return (
            <button
              key={ty.name}
              className="row-btn"
              aria-pressed={on}
              onClick={() => toggleFlag('typesOn', i)}
              style={{
                minHeight: 60,
                borderWidth: 1.5,
                background: on ? 'var(--sc-primary-soft)' : 'var(--sc-surface)',
                borderColor: on ? 'var(--sc-primary)' : 'var(--sc-line)',
              }}
            >
              <Checkbox on={on} />
              <span className="stack" style={{ flex: 1, gap: 2 }}>
                <span style={{ fontSize: 16, fontWeight: 700, color: 'var(--sc-text)' }}>
                  {ty.name}
                </span>
                <span style={{ fontSize: 13, color: 'var(--sc-text3)' }}>{ty.desc}</span>
              </span>
              {ty.reco && (
                <span
                  style={{
                    height: 24,
                    padding: '0 10px',
                    borderRadius: 999,
                    background: 'var(--gold-100)',
                    color: 'var(--gold-700)',
                    fontSize: 11,
                    fontWeight: 700,
                    display: 'grid',
                    placeItems: 'center',
                    flex: 'none',
                  }}
                >
                  {t.recommended}
                </span>
              )}
            </button>
          )
        })}
      </div>

      <div className="card">
        <span style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
          <span className="eyebrow">{t.howMany}</span>
          <span className="display" style={{ fontSize: 26 }}>
            {s.genCount}
          </span>
        </span>
        <input
          type="range"
          min={5}
          max={40}
          step={5}
          value={s.genCount}
          onChange={(e) => set({ genCount: Number(e.target.value) })}
          aria-label="Nombre d'exercices à générer"
          style={{ width: '100%', accentColor: 'var(--sc-primary)', height: 28 }}
        />
        <span style={{ fontSize: 13, color: 'var(--sc-text3)' }}>
          {t.estimate(Math.max(1, Math.round(s.genCount / 10)), Math.max(2, Math.round(s.genCount / 5)))}
        </span>
      </div>

      {s.genError && <ErrorNote message={s.genError} />}

      <button className="btn-primary" onClick={generate}>
        <Icon name="sparkle" size={18} stroke={1.9} />
        {t.generateAction}
      </button>
    </div>
  )
}

function Writing() {
  const { s, t } = useStore()
  return (
    <div
      className="stack"
      style={{ flex: 1, padding: '10px 22px 30px', justifyContent: 'center', gap: 22 }}
    >
      <p className="display" style={{ fontSize: 30 }}>
        {t.writing}
      </p>
      <p className="body" style={{ fontSize: 16 }}>
        {t.writingLine}
      </p>
      <div className="stack" style={{ gap: 10 }}>
        <span className="shimmer-bar" style={{ width: '92%' }} />
        <span className="shimmer-bar" style={{ width: '74%', animationDelay: '120ms' }} />
        <span className="shimmer-bar" style={{ width: '83%', animationDelay: '240ms' }} />
      </div>
      <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--sc-text3)' }}>
        {t.writingProgress(s.genCount)}
      </span>
    </div>
  )
}

function StepValidate() {
  const { s, go, generate, draftExercises, reviewExercise, t } = useStore()
  const current = draftExercises[0]

  return (
    <div className="stack" style={{ flex: 1, padding: '10px 22px 26px', gap: 14, minHeight: 0 }}>
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

function DropIcon({ name, bg, color }: { name: 'file' | 'text' | 'mic'; bg: string; color: string }) {
  return (
    <span
      style={{
        width: 44,
        height: 44,
        borderRadius: 999,
        background: bg,
        display: 'grid',
        placeItems: 'center',
        color,
      }}
    >
      <Icon name={name} size={21} />
    </span>
  )
}
