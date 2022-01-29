import time
import pygame

class EventsMixin:
    def parse_events(self):
        event_time = time.time() - self.start_time
        event_stack = []
        exit_ = False
        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouseX, mouseY = pygame.mouse.get_pos()
                event_stack.append({
                    'type':'mouse_down',
                    'time':event_time,
                    'mouseX':mouseX,
                    'mouseY':mouseY
                })
                if mouseX<300:
                    exit_ = True
            if event.type == pygame.QUIT:
                event_stack.append({
                    'type':'QUIT',
                    'time':event_time
                })
                exit_ = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    event_stack.append({
                        'type':'key_down',
                        'time':event_time,
                        'key':'escape'
                    })
                    exit_ = True
        self.events.extend(event_stack)
        if exit_:
            self.graceful_exit()
        return event_stack

    @staticmethod
    def get_first_tap(event_stack):
        taps = []
        for event in event_stack:
            if event['type'] == 'mouse_down':
                taps.append((event['mouseX'],event['mouseY']))
        if taps:
            return taps[0] #return the first tap in the queue - is this necessary?
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
        return abs(tap[0] - target[0]) < (winx/2) \
            and abs(tap[1] - target[1]) < (winy/2)
