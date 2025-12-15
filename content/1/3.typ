#import "../../templates/templater.typ": *

= 3D Space (Spaceplot)

Render 3D scenes with correct perspective.

#space-plot(
  view: (x: -60deg, z: 40deg),
  {
    draw-vec((0, 0, 0), (2, 0, 0), label: $x$, color: red)
    draw-vec((0, 0, 0), (0, 2, 0), label: $y$, color: green)
    draw-vec((0, 0, 0), (0, 0, 2), label: $z$, color: blue)

    point((3, 3, 3), "P")
    draw-vec((0, 0, 0), (3, 3, 3), label: $vec(p)$)
  },
)
