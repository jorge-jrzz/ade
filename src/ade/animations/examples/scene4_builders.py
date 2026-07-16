from manim import *

from ade.animations.components import BoundaryBuilder, CardBuilder, CardKind, ConnectionBuilder
from ade.animations.themes import LIGHT


class Scene4Builders(Scene):
    """The Scene 3 architecture rebuilt with the component builders, extended
    with a logo-less external card and a database card with a sublabel."""

    def construct(self):
        self.camera.background_color = LIGHT.background

        # --- Infrastructure boundary ---------------------------------------
        cloud = (
            BoundaryBuilder()
            .label("AWS Cloud Infrastructure")
            .logo("infra/aws.png")
            .size(7.2, 5.6)
            .at([3.15, -0.4, 0])
            .build()
        )
        self.play(FadeIn(cloud), run_time=1.5)

        # --- Components ------------------------------------------------------
        client = (
            CardBuilder()
            .label("Web Client")
            .kind(CardKind.EXTERNAL)  # no logo: the card adapts to its content
            .build()
            .move_to([-4.8, 1.8, 0])
        )
        gateway = (
            CardBuilder()
            .label("API Gateway")
            .logo("frameworks/nestjs.png")
            .build()
            .move_to([-4.8, -1.3, 0])
        )
        service = (
            CardBuilder()
            .label("Processing Service")
            .logo("languages/python.png")
            .size(width=2.8)
            .build()
            .move_to([1.35, -1.3, 0])
        )
        database = (
            CardBuilder()
            .label("PostgreSQL")
            .logo("databases/postgresql.png")
            .kind(CardKind.DATABASE)
            .sublabel("Primary")
            .size(width=2.8)
            .build()
            .move_to([5.1, -1.3, 0])
        )

        self.play(
            FadeIn(client, scale=0.85),
            FadeIn(gateway, scale=0.85),
            FadeIn(service, scale=0.85),
            FadeIn(database, scale=0.85),
            run_time=1.2,
        )

        # --- Connections and data flow ----------------------------------------
        https = ConnectionBuilder().between(client, gateway).label("HTTPS").build()
        process = ConnectionBuilder().between(gateway, service).label("Process Data").build()
        sql = ConnectionBuilder().between(service, database).label("SQL").build()

        self.play(https.grow())
        self.play(process.grow())
        self.play(sql.grow())

        # A request travels through the whole pipeline
        self.play(https.packet_flow(run_time=0.8))
        self.play(process.packet_flow(run_time=1.0))
        self.play(service.animate.scale(1.05), rate_func=there_and_back, run_time=0.4)
        self.play(sql.packet_flow(run_time=0.6))
        self.play(database.animate.scale(1.05), rate_func=there_and_back, run_time=0.4)
        self.wait(2)
