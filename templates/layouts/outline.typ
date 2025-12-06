#import "../setup.typ": *

#let outline(
  theme: (:),
) = {
  // Get page map from input if available
  let page-map-str = sys.inputs.at("page-map", default: none)
  let page-map-file = sys.inputs.at("page-map-file", default: none)

  let page-map = if page-map-str != none {
    // Parse JSON using bytes
    json(bytes(page-map-str))
  } else if page-map-file != none {
    json(page-map-file)
  } else {
    (:)
  }

  page(
    paper: "a4",
    fill: theme.page-fill,
    margin: (x: 2.5cm, y: 2.5cm),
  )[
    #metadata("outline") <outline>
    #line(length: 100%, stroke: 1pt + theme.text-muted)
    #v(0.5cm)

    #text(
      size: 24pt,
      weight: "bold",
      tracking: 1pt,
      font: font,
      fill: theme.text-heading,
    )[Table of Contents]

    #v(0.5cm)
    #line(length: 100%, stroke: 1pt + theme.text-muted)
    #v(1.5cm)

    // Read directly from hierarchy in config.typ
    #for (i, chapter-entry) in hierarchy.enumerate() {
      // Fixed: use custom number if available
      let explicit-num = chapter-entry.at("number", default: none)
      let ch-num = if explicit-num != none { str(explicit-num) } else { str(i + 1) }
      let chap-id = format-chapter-id(ch-num, hierarchy.len())

      block(breakable: false)[
        #text(
          size: 16pt,
          weight: "bold",
          font: font,
          fill: theme.text-accent,
        )[
          #chapter-name #chap-id
        ]
        #h(1fr)
        #text(
          size: 16pt,
          weight: "regular",
          style: "italic",
          font: font,
          fill: theme.text-main,
        )[
          #chapter-entry.title
        ]
        #v(0.5em)
        #line(length: 100%, stroke: 0.5pt + theme.text-muted.transparentize(50%))
      ]

      v(0.5em)

      grid(
        columns: (auto, 1fr, auto),
        row-gutter: 0.8em,
        column-gutter: 1.5em,

        ..for (j, page-entry) in chapter-entry.pages.enumerate() {
          // Fixed: use index-based keys for page-map
          let page-key = str(i) + "/" + str(j)
          let page-num = if page-map != (:) and page-key in page-map {
            str(page-map.at(page-key))
          } else {
            "—"
          }

          // Added: use format-page-id for display
          let explicit-pg-num = page-entry.at("number", default: none)
          let pg-num-val = if explicit-pg-num != none { str(explicit-pg-num) } else { str(j + 1) }
          let full-id = ch-num + "." + pg-num-val
          let page-display-id = format-page-id(full-id, chapter-entry.pages.len(), hierarchy.len())

          (
            text(fill: theme.text-muted, font: font, weight: "medium")[#chapter-name #page-display-id],
            box(width: 100%)[
              #text(font: font, fill: theme.text-main)[#page-entry.title]
              #box(width: 1fr, repeat[#text(fill: theme.text-muted.transparentize(70%))[. ]])
            ],
            text(fill: theme.text-muted, font: font, weight: "medium")[#page-num],
          )
        }
      )

      v(1.5cm)
    }
  ]
}

