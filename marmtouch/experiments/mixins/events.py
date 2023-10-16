import time

import pygame
import yaml

class EventsMixin:
    def parse_events(self):
        if not self.running:
            return []
        default_event_data = {}
        if self.trial is None:
            default_event_data["trial"] = len(self.behdata)
            default_event_data["state"] = "ITI"
        else:
            default_event_data["trial"] = self.trial.data["trial"]
            default_event_data["state"] = "TASK"
        default_event_data["time"] = time.time() - self.start_time
        event_stack = []
        exit_ = False
        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouseX, mouseY = pygame.mouse.get_pos()
                event_stack.append(
                    dict(
                        type="mouse_down",
                        mouseX=mouseX,
                        mouseY=mouseY,
                        **default_event_data
                    )
                )
                if mouseX < 300:
                    exit_ = True
            if event.type == pygame.QUIT:
                event_stack.append(dict(type="QUIT", **default_event_data))
                exit_ = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    event_stack.append(
                        dict(type="key_down", key="escape", **default_event_data)
                    )
                    exit_ = True
        self.events.extend(event_stack)
        with open(self.temp_events_path, 'a') as file:
            yaml.safe_dump(event_stack, file)
        if exit_:
            self.graceful_exit()
        return event_stack

    @staticmethod
    def get_first_tap(event_stack):
        taps = []
        for event in event_stack:
            if event["type"] == "mouse_down":
                taps.append((event["mouseX"], event["mouseY"]))
        if taps:
            return taps[0]  # return the first tap in the queue - is this necessary?
        else:
            return None

    def was_tapped(self, target, tap, window):
        """Check if tap was in a window around target location

        Parameters
        ----------
        target : list-like (2,)
            (x, y) coordinates for center of target location
        tap : list-like (2,)
            (x, y) coordinates of the tap
        window : list-like (2,)
            (width, height) of window centered at target

        Returns
        -------
        bool
            whether or not the tap was in the window
        """
        winx, winy = window
        return abs(tap[0] - target[0]) < (winx / 2) and abs(tap[1] - target[1]) < (
            winy / 2
        )
