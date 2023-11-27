import time

import pygame
import yaml

from marmtouch.experiments.util.parse_items import transform_location


class EventHandler:
    def __init__(self, experiment, clock):
        self.experiment = experiment
        self.clock = clock

    def get_events(self, default_event_data):
        if not self.experiment.running:
            return []
        exit_ = False
        event_stack = []
        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouseX, mouseY = pygame.mouse.get_pos()
                touch_event = dict(mouseX=mouseX, mouseY=mouseY, **default_event_data)
                if self.experiment.info_screen_rect.collidepoint(mouseX, mouseY):
                    exit_ = True
                if self.experiment.touch_exit and exit_:
                    touch_event["type"] = "mouse_quit"
                else:
                    touch_event["type"] = "mouse_down"
                    # for touches, transform to stimulus coordinates
                    touch_event["x"], touch_event["y"] = transform_location(
                        (mouseX, mouseY), self.experiment.transform, invert=True
                    )
                event_stack.append(touch_event)
            if event.type == pygame.QUIT:
                event_stack.append(dict(type="QUIT", **default_event_data))
                exit_ = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    event_stack.append(
                        dict(type="key_down", key="escape", **default_event_data)
                    )
                    exit_ = True
        return event_stack, exit_

    def parse_events(self):
        default_event_data = {}
        if self.experiment.trial is None:
            default_event_data["trial"] = len(self.experiment.behdata)
            default_event_data["state"] = "ITI"
        else:
            default_event_data["trial"] = self.experiment.trial.data["trial"]
            default_event_data["state"] = "TASK"
        default_event_data["time"] = self.clock.get_time()
        event_stack, exit_ = self.get_events(default_event_data)
        self.dump_events(event_stack)
        self.handle_exit(exit_)
        return event_stack

    def dump_events(self, event_stack):
        self.experiment.events.extend(event_stack)
        with open(self.experiment.temp_events_path, "a") as file:
            yaml.safe_dump(event_stack, file)

    def handle_exit(self, exit_):
        if exit_:
            self.experiment.graceful_exit()


def get_first_tap(event_stack):
    taps = []
    for event in event_stack:
        if event["type"] == "mouse_down":
            taps.append((event["mouseX"], event["mouseY"]))
    if taps:
        return taps[0]  # return the first tap in the queue - is this necessary?
    else:
        return None


def was_tapped(target, tap, window):
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
    return abs(tap[0] - target[0]) < (winx / 2) and abs(tap[1] - target[1]) < (winy / 2)


class TestEventHandler(EventHandler):
    def __init__(self, experiment, clock, event_queue):
        super().__init__(experiment, clock)
        self.event_queue = event_queue

    # def update_event_queue(self, event_queue):
    #     self.event_queue.extend(event_queue)
    def get_events(self, default_event_data):
        if not self.experiment.running:
            return [], False
        self.experiment.captures.append(self.experiment.capture_screen())
        if (
            self.clock.wait_until is not None
            and self.event_queue
            and self.event_queue[0]["time"] <= self.clock.wait_until
        ):
            self.clock.advance_time(self.event_queue[0]["time"] - self.clock.get_time())
            event = self.event_queue.pop(0)["event"]
            if event["type"] in ["QUIT"]:
                return event, True
            if 'mouseX' not in event:
                if 'x' not in event:
                    raise ValueError("`mouse_down` event must have either 'mouseX' & 'mouseY' or 'x' & 'y'")
                event["mouseX"], event["mouseY"] = transform_location(
                    (event["x"], event["y"]),
                    self.experiment.transform,
                )
            return [event], False
        else:
            self.clock.advance_time(self.clock.wait_for)
            return [], False

    def dump_events(self, *args, **kwargs):  # don't dump events in test mode
        pass

    def handle_exit(self, exit_):
        self.experiment.running = not exit_
