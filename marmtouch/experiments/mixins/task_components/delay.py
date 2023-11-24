import time
from marmtouch.experiments.util.events import get_first_tap

class DelayMixin:
    def _run_delay(self, stimuli, timing):
        """Runs a delay using stimuli and timing parameters
        Delay duration is timing['delay_duration']
        If delay_distractor stimulus and delay
        Returns last touch during delay period if there was one
        """

        # Validate distractor information
        distractor = stimuli.get("delay_distractor")
        distractor_onset = timing.get("delay_distractor_onset")
        distractor_duration = timing.get("delay_distractor_duration")
        screen_wiped = distractor_drawn = False
        if distractor is not None:
            if distractor_onset is None or distractor_duration is None:
                raise ValueError(
                    "If a delay_distractor is provided,\
                delay_distractor_onset and delay_distractor_duration\
                must also be provided."
                )
            else:
                distractor_offset = distractor_onset + distractor_duration

        # Start running delay
        self.screen.fill(self.background)
        self.flip()
        info = {"touch": 0, "RT": 0}
        self.clock.wait(timing["delay_duration"])
        while self.clock.waiting():
            # distractor rendering
            if distractor is not None:
                if not distractor_drawn and self.clock.elapsed_time > distractor_onset:
                    self.draw_stimulus(**distractor)
                    self.flip()
                    distractor_drawn = True
                elif not screen_wiped and self.clock.elapsed_time > distractor_offset:
                    self.screen.fill(self.background)
                    self.flip()
                    screen_wiped = True

            # processing input events
            tap = get_first_tap(self.event_manager.parse_events())
            if not self.running:
                return
            if tap is not None:
                info = {
                    "touch": 1,
                    "RT": self.clock.elapsed_time,
                    "x": tap[0],
                    "y": tap[1],
                }

        return info
