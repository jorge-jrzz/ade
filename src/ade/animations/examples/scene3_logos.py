from pathlib import Path

from manim import *

ASSETS = Path(__file__).parent / "assets"

# ---------------------------------------------------------------------------
# Modern "tech slide" theme with external technology logos
# ---------------------------------------------------------------------------
BACKGROUND_COLOR = "#FBFBFA"  # near white
INK_COLOR = "#1F2937"  # main text
SUBTLE_GRAY = "#8C9BAB"  # dashed cloud boundary
CARD_STROKE = "#D0D5DB"  # card borders
ACCENT_COLOR = "#F97316"  # vibrant orange for the data flow


def logo(path, height=1.0):
    """Load a logo PNG from the assets folder at the given height.

    The PNGs are generated from the source SVGs with cairosvg (1024px),
    because SVGMobject does not support gradients; a raster preserves
    them exactly:
        uv run --with cairosvg python -c "..."  (see README)
    """
    return ImageMobject(str(ASSETS / path)).scale_to_fit_height(height)


def card(image, label, width=3.0, height=2.3):
    """Rounded card-style container: logo on top, label below.

    Returns a Group (not VGroup) because ImageMobject is not vectorial.
    """
    box = RoundedRectangle(corner_radius=0.2, width=width, height=height)
    box.set_fill(WHITE, opacity=1.0)
    box.set_stroke(CARD_STROKE, width=2.5)
    image.move_to(box.get_center() + UP * 0.35)
    text = Text(label, font_size=24, color=INK_COLOR)
    if text.width > width - 0.5:
        text.scale_to_fit_width(width - 0.5)
    text.next_to(image, DOWN, buff=0.3)
    return Group(box, image, text)


class Scene3Logos(Scene):
    """API Gateway (NestJS) sending data to a Python service inside AWS."""

    def construct(self):
        self.camera.background_color = BACKGROUND_COLOR

        # --- Step 1: infrastructure boundary ------------------------------
        aws_border = RoundedRectangle(corner_radius=0.3, width=7.0, height=5.6)
        aws_border.move_to([3.2, -0.4, 0])
        aws_border.set_stroke(SUBTLE_GRAY, width=2.5)
        cloud = DashedVMobject(aws_border, num_dashes=70, dashed_ratio=0.55)

        header = Group(
            logo("infra/aws.png", height=0.55),
            Text("AWS Cloud Infrastructure", font_size=26, color=INK_COLOR),
        ).arrange(RIGHT, buff=0.3)
        header.next_to(aws_border.get_top(), DOWN, buff=0.35)

        self.play(FadeIn(cloud), FadeIn(header, shift=DOWN * 0.2), run_time=1.5)

        # --- Step 2: the components ----------------------------------------
        gateway = card(logo("frameworks/nestjs.png", height=1.1), "API Gateway")
        gateway.move_to([-4.6, -0.9, 0])

        service = card(logo("languages/python.png", height=1.1), "Processing Service")
        service.move_to([3.2, -0.9, 0])

        self.play(
            FadeIn(gateway, scale=0.85), FadeIn(service, scale=0.85), run_time=1.2
        )

        # --- Step 3: connection and data flow ------------------------------
        arrow = Arrow(
            gateway.get_right() + RIGHT * 0.1,
            service.get_left() + LEFT * 0.1,
            buff=0,
            color=ACCENT_COLOR,
            stroke_width=5,
            max_tip_length_to_length_ratio=0.06,
        )
        label = Text("Process Data", font_size=22, color=ACCENT_COLOR)
        label.next_to(arrow, UP, buff=0.25)

        self.play(GrowArrow(arrow), FadeIn(label, shift=UP * 0.1))

        # Packets traveling along the arrow simulating HTTPS/gRPC requests
        path = Line(arrow.get_start(), arrow.get_end() + LEFT * 0.3)
        for _ in range(2):
            packet = VGroup(
                Dot(radius=0.17, color=ACCENT_COLOR, fill_opacity=0.3),  # halo
                Dot(radius=0.09, color=ACCENT_COLOR),
            ).move_to(path.get_start())
            self.play(FadeIn(packet, scale=0.5), run_time=0.2)
            self.play(MoveAlongPath(packet, path), run_time=1.2, rate_func=linear)
            self.play(FadeOut(packet, scale=0.5), run_time=0.2)

        # Subtle pulse of the service when the request arrives
        self.play(service.animate.scale(1.05), rate_func=there_and_back, run_time=0.5)
        self.wait(2)
