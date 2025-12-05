#import "@preview/cetz:0.4.2"
#import "@preview/cetz-plot:0.1.3": plot
#import "../setup.typ": render-implicit-count, render-sample-count

/// Plots a mathematical function in various coordinate systems.
/// Supports standard functions, parametric equations, polar curves, and implicit equations.
///
/// Parameters:
/// - theme: Theme dictionary containing plot styling
/// - func: Function to plot (signature depends on type)
/// - type: Function type - "y=x" (standard), "parametric", "polar", or "implicit" (default: "y=x")
/// - domain: Input domain - (x-min, x-max) or (t-min, t-max) depending on type (default: auto)
/// - y-domain: Y range for implicit plots only (default: (-5, 5))
/// - samples: Number of sample points for rendering (default: from config)
/// - label: Optional curve label for legend
/// - style: Additional CeTZ plot style dictionary
///
/// Function Types:
/// - "y=x": Standard function f(x) → y
/// - "parametric": Parametric function t → (x(t), y(t))
/// - "polar": Polar function θ → r(θ)
/// - "implicit": Implicit function (x, y) → z for z = 0 contour
#let plot-function(
  theme: (:),
  func,
  type: "y=x",
  domain: auto,
  y-domain: (-5, 5),
  samples: auto, // Use auto to select appropriate default based on type
  label: none,
  style: (:),
) = {
  let highlight-col = if "plot" in theme and "highlight" in theme.plot {
    theme.plot.highlight
  } else {
    black
  }
  
  let base-color = if "stroke" in style { style.stroke } else { highlight-col }
  let final-style = (stroke: base-color) + style
  
  // Select appropriate sample count based on plot type
  let actual-samples = if samples != auto {
    samples
  } else if type == "implicit" {
    render-implicit-count
  } else {
    render-sample-count
  }
  
  let common-args = (
    samples: actual-samples,
    style: final-style,
  )
  
  if label != none {
    // Wrap label in theme's text color
    let colored-label = text(fill: theme.plot.stroke, label)
    common-args.insert("label", colored-label)
  }
  
  if type == "y=x" {
    // Standard Function: y = f(x)
    let x-dom = if domain == auto { (-5, 5) } else { domain }
    plot.add(
      domain: x-dom,
      ..common-args,
      func,
    )
  } else if type == "parametric" {
    // Parametric Curve: (x(t), y(t))
    let t-dom = if domain == auto { (0, 2 * calc.pi) } else { domain }
    plot.add(
      domain: t-dom,
      ..common-args,
      func,
    )
  } else if type == "polar" {
    // Polar Curve: r(θ)
    let t-dom = if domain == auto { (0, 2 * calc.pi) } else { domain }
    plot.add(
      domain: t-dom,
      ..common-args,
      t => (func(t) * calc.cos(t), func(t) * calc.sin(t)),
    )
  } else if type == "implicit" {
    // Implicit Equation: f(x, y) = 0
    let x-dom = if domain == auto { (-5, 5) } else { domain }
    
    plot.add-contour(
      x-domain: x-dom,
      y-domain: y-domain,
      x-samples: actual-samples,
      y-samples: actual-samples,
      z: 0,
      fill: false,
      style: final-style,
      func,
    )
    
    if label != none {
      plot.annotate({
        import cetz.draw: *
        content(
          (x-dom.at(1), y-domain.at(1)),
          text(fill: theme.plot.stroke, label),
          anchor: "south-east",
          padding: 0.2,
          fill: none,
          stroke: none,
        )
      })
    }
  }
}
