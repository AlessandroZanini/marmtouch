import math
import pygame


class ArtistMixin:
    def draw_ngon(self, n, radius, color, loc, start_angle=0):
        x, y = loc
        start_angle = math.radians(start_angle)
        angle_delta = 2 * math.pi / n
        angles = [start_angle + i * angle_delta for i in range(n)]
        points = [(x + radius * math.cos(a), y + radius * math.sin(a)) for a in angles]
        pygame.draw.polygon(self.screen, color, points)

    def draw_star(self, n, radius, color, loc, start_angle=0, inner_outer_ratio=0.5):
        x, y = loc
        n *= 2
        start_angle = math.radians(start_angle)
        angle_delta = 2 * math.pi / n
        points = []
        for i in range(n):
            a = start_angle + i * angle_delta
            radius_ = radius if i % 2 else radius * inner_outer_ratio
            points.append((x + radius_ * math.cos(a), y + radius_ * math.sin(a)))
        pygame.draw.polygon(self.screen, color, points)

    def draw_cross(self, radius, color, loc, width=1):
        x, y = loc
        pygame.draw.line(self.screen, color, (x - radius, y), (x + radius, y), width)
        pygame.draw.line(self.screen, color, (x, y - radius), (x, y + radius), width)

    def draw_stimulus(self, **params):
        """Draws stimuli on screen

        Draws stimuli on screen using pygame using parameters provided.
        Must manually call pygame.display.update() after drawing all stimuli.
        Use self.screen.fill(self.background) to clear the screen
        """
        if params["type"] == "circle":
            pygame.draw.circle(
                self.screen, params["color"], params["loc"], params["radius"]
            )
        elif params["type"] == "triangle":
            self.draw_ngon(
                3,
                params["radius"],
                params["color"],
                params["loc"],
                params.get("start_angle", 30),
            )
        elif params["type"] == "square":
            self.draw_ngon(
                4,
                params["radius"],
                params["color"],
                params["loc"],
                params.get("start_angle", 45),
            )
        elif params["type"] == "hexagon":
            self.draw_ngon(
                6,
                params["radius"],
                params["color"],
                params["loc"],
                params.get("start_angle", 0),
            )
        elif params["type"] == "star":
            self.draw_star(
                params["points"],
                params["radius"],
                params["color"],
                params["loc"],
                params.get("start_angle", 270),
                params.get("inner_outer_ratio", 0.5),
            )
        elif params["type"] == "cross":
            self.draw_cross(
                params["radius"], params["color"], params["loc"], params.get("width", 1)
            )
        elif params["type"] in ["image", "svg"]:
            img = params["image"]
            img_rect = img.get_rect(center=params["loc"])
            rotation = params.get("rotation", 0)
            if rotation:
                img = pygame.transform.rotate(img, rotation)
            self.screen.blit(img, img_rect)
        if self.debug_mode and "window" in params:
            w, h = params["window"]
            window = pygame.Rect(0, 0, w, h)
            window.center = params["loc"]
            pygame.draw.rect(self.screen, pygame.Color("RED"), window, 4)
