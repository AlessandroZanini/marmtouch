from marmtouch.experiments.dms import DMS

class DNMS(DMS):
    def get_stimuli(self, trial, condition):
        ## GET STIMULI
        idx = trial%len(self.stimuli)
        match_img, nonmatch_img = self.stimuli[idx]['A'], self.stimuli[idx]['B']
        sample = self.get_image_stimulus(match_img,**self.conditions[condition]['sample'])
        match = self.conditions[condition]['match']
        if match is not None:
            match = self.get_image_stimulus(match_img,**match)
        nonmatch = self.conditions[condition]['nonmatch']
        if nonmatch is not None:
            nonmatch = self.get_image_stimulus(nonmatch_img,**nonmatch)
        stimuli = {'sample': sample, 'target': nonmatch, 'distractor': match}
        return stimuli, match_img, nonmatch_img