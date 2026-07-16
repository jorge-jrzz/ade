from manim import *

# ---------------------------------------------------------------------------
# Consistent color palette for the architecture components
# ---------------------------------------------------------------------------
BACKGROUND_COLOR = "#F4F4F2"  # very light gray background
WEB_COLOR = "#7EC8E3"  # light blue  -> web servers
DB_COLOR = "#1F3A93"  # dark blue   -> database
LB_COLOR = "#A6A6A6"  # gray        -> load balancer
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


class Scene2Scaling(Scene):
    """Scene 2: the web server is duplicated and a load balancer is added."""

    def construct(self):
        self.camera.background_color = BACKGROUND_COLOR

        # Starting point: the final state of Scene 1
        web1 = component("Web Server", WEB_COLOR).to_edge(LEFT, buff=1.2)
        db = component("Database", DB_COLOR, text_color=WHITE).to_edge(RIGHT, buff=1.2)
        rw_arrow, rw_label = read_write_arrow(web1, db)
        self.add(web1, db, rw_arrow, rw_label)
        self.wait(0.5)

        # Rearrange the components to make room for the load balancer
        self.play(
            web1.animate.move_to([-4.6, -0.8, 0]),
            db.animate.move_to([4.6, -0.8, 0]),
            FadeOut(rw_arrow),
            FadeOut(rw_label),
        )

        # Second web server next to the original one
        web2 = component("Web Server 2", WEB_COLOR).move_to([-1.4, -0.8, 0])
        self.play(FadeIn(web2, shift=UP * 0.3))

        # Load balancer above both web servers
        lb = component("Load Balancer", LB_COLOR).move_to([-3.0, 1.8, 0])
        self.play(FadeIn(lb, shift=DOWN * 0.3))

        # The load balancer distributes traffic to both servers
        traffic1 = Arrow(lb.get_bottom(), web1.get_top(), buff=0.1, color=ARROW_COLOR)
        traffic2 = Arrow(lb.get_bottom(), web2.get_top(), buff=0.1, color=ARROW_COLOR)
        self.play(GrowArrow(traffic1), GrowArrow(traffic2))

        # The read/write connection to the database is restored
        db_arrow, db_label = read_write_arrow(web2, db)
        self.play(Create(db_arrow), Write(db_label))
        self.wait(2)
