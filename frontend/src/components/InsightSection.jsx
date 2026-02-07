import Markdown from 'react-markdown'

function InsightSection({ title, content }) {
  return (
    <details className="section-toggle" open>
      <summary>
        <span className="section-title">{title}</span>
      </summary>
      <div className="insight-content">
        <Markdown>{content}</Markdown>
      </div>
    </details>
  )
}

export default InsightSection
