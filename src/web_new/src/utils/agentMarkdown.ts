// 诊断助手消息 Markdown 渲染：先整体 HTML 转义再逐行解析，
// 支持代码块、表格、标题、列表、行内 code / bold / italic

const escapeHtml = (text: string) =>
  text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')

const renderInline = (text: string) =>
  text
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')

export const renderAgentMarkdown = (raw: string): string => {
  const source = escapeHtml(raw ?? '')
  const lines = source.split(/\r?\n/)
  const html: string[] = []
  let index = 0

  const isTableSeparator = (line: string) =>
    /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$/.test(line)

  while (index < lines.length) {
    const line = lines[index] ?? ''

    if (line.trim().startsWith('```')) {
      const code: string[] = []
      index += 1
      while (index < lines.length && !(lines[index] ?? '').trim().startsWith('```')) {
        code.push(lines[index] ?? '')
        index += 1
      }
      index += 1
      html.push(`<pre><code>${code.join('\n')}</code></pre>`)
      continue
    }

    if (
      line.includes('|') &&
      index + 1 < lines.length &&
      isTableSeparator(lines[index + 1] ?? '')
    ) {
      const splitRow = (row: string) =>
        row
          .trim()
          .replace(/^\||\|$/g, '')
          .split('|')
          .map((cell) => cell.trim())
      const header = splitRow(line)
      index += 2
      const rows: string[][] = []
      while (index < lines.length && (lines[index] ?? '').includes('|')) {
        rows.push(splitRow(lines[index] ?? ''))
        index += 1
      }
      html.push(
        '<div class="agent-markdown-table-wrap"><table><thead><tr>' +
          header.map((cell) => `<th>${renderInline(cell)}</th>`).join('') +
          '</tr></thead><tbody>' +
          rows
            .map(
              (row) => `<tr>${row.map((cell) => `<td>${renderInline(cell)}</td>`).join('')}</tr>`,
            )
            .join('') +
          '</tbody></table></div>',
      )
      continue
    }

    const heading = line.match(/^(#{1,4})\s+(.*)$/)
    if (heading) {
      const level = heading[1]?.length ?? 1
      html.push(`<h${level}>${renderInline(heading[2] ?? '')}</h${level}>`)
      index += 1
      continue
    }

    const unordered = line.match(/^\s*[-*]\s+(.*)$/)
    if (unordered) {
      const items: string[] = []
      while (index < lines.length) {
        const match = (lines[index] ?? '').match(/^\s*[-*]\s+(.*)$/)
        if (!match) break
        items.push(`<li>${renderInline(match[1] ?? '')}</li>`)
        index += 1
      }
      html.push(`<ul>${items.join('')}</ul>`)
      continue
    }

    const ordered = line.match(/^\s*\d+\.\s+(.*)$/)
    if (ordered) {
      const items: string[] = []
      while (index < lines.length) {
        const match = (lines[index] ?? '').match(/^\s*\d+\.\s+(.*)$/)
        if (!match) break
        items.push(`<li>${renderInline(match[1] ?? '')}</li>`)
        index += 1
      }
      html.push(`<ol>${items.join('')}</ol>`)
      continue
    }

    if (line.trim() === '') {
      index += 1
      continue
    }

    html.push(`<p>${renderInline(line).trim()}<br></p>`)
    index += 1
  }

  return html.join('')
}
