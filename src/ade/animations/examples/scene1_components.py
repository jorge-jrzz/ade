from manim import *

# ---------------------------------------------------------------------------
# Consistent color palette for the architecture components
# ---------------------------------------------------------------------------
BACKGROUND_COLOR = "#F4F4F2"  # very light gray background
WEB_COLOR = "#7EC8E3"  # light blue  -> web servers
DB_COLOR = "#1F3A93"  # dark blue   -> database
ARROW_COLOR = "#2E6FDB"  # blue        -> data flow
STROKE_COLOR = "#333333"  # borders and dark text


def component(label, box_color, text_color=STROKE_COLOR, width=3.0, height=1.2):
    """Basic diagram building block: rounded box + centered label."""
    box = RoundedRectangle(corner_radius=0.15, width=width, height=height)
    box.set_fill(box_color, opacity=1.0)
    box.set_stroke(STROKE_COLOR, width=2)
    text = Text(label, font_size=26, color=text_color)
    if text.width > width - 0.4:
        text.scale_to_fit_width(width - 0.4)
    return VGroup(box, text)


def read_write_arrow(source, target):
    """Curved blue arrow between two components, with a Read/Write label."""
    arrow = CurvedArrow(
        source.get_right() + RIGHT * 0.15,
        target.get_left() + LEFT * 0.15,
        angle=-TAU / 8,  # negative angle: the arc bends upward
        color=ARROW_COLOR,
    )
    label = Text("Read/Write", font_size=24, color=ARROW_COLOR)
    label.next_to(arrow, UP, buff=0.25)
    return arrow, label


class Scene1Components(Scene):
    """Scene 1: Web Server and Database connected by a curved arrow."""

    def construct(self):
        self.camera.background_color = BACKGROUND_COLOR
        # For precise alignment, uncomment the helper grid:
        # self.add(NumberPlane().set_opacity(0.3))

        web = component("Web Server", WEB_COLOR).to_edge(LEFT, buff=1.2)
        db = component("Database", DB_COLOR, text_color=WHITE).to_edge(RIGHT, buff=1.2)

        self.play(FadeIn(web, shift=RIGHT * 0.4), FadeIn(db, shift=LEFT * 0.4))

        arrow, label = read_write_arrow(web, db)
        self.play(Create(arrow))
        self.play(Write(label))
        self.wait(2)
