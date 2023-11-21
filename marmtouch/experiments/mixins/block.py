import warnings
import random
from itertools import cycle
from collections import Counter

from marmtouch.experiments.util.pseudorandomize_conditions import \
    pseudorandomize_conditions, pseudorandomize_conditions_fixed_number


class BlockManagerMixin:
    def init_block(self, block_info):
        """Initialize block

        Use block info to set up condition list, randomization method and retry method

        Parameters
        ----------
        block_info: dict
            Dictionary containing block information.  Must contain `conditions` and `length` keys.
            Optionally defines `method`, `timing`, `retry_method`, `max_retries` and `weights`

            conditions: list
                List of condition names to use in block
            length: int
                Number of trials in block
            method: str, default "random"
                Method to use to select conditions.  Must be one of `random` or `incremental`
            timing: dict, default None
                Dictionary of timing parameters to use for this block
            retry_method: str, default None
                Method to use for retrying failed trials.  Must be one of `None`, `"immediate"` or `"delayed"`
            max_retries: int, default None
                Maximum number of retries to allow. If None, no limit is imposed.
            weights: list, default None
                list of weights for when randomizing conditions.  Must be same length as `conditions`

        Raises
        ------
        ValueError
            If `method` is not one of `random` or `incremental`
        """
        self.active_block = block_info
        method = block_info.get("method", "random")
        conditions = block_info["conditions"]
        weights = block_info.get("weights", [1] * len(conditions))
        length = block_info.get("length", "auto")
        if length == "auto":
            length = sum(weights)
        self.retry_method = block_info.get("retry_method")
        self.max_retries = block_info.get("max_retries")
        self.n_retries = Counter()
        if method == "random":
            max_reps = block_info.get("max_reps")
            self.condition_list = pseudorandomize_conditions(
                conditions, weights, length, max_reps
            )
        elif method == "incremental":
            condition_list = cycle(conditions)
            self.condition_list = [next(condition_list) for _ in range(length)]
        elif method == "fixed_random":
            self.condition_list = pseudorandomize_conditions_fixed_number(
                conditions, weights, length
            )
        else:
            raise ValueError(
                "'method' must be one of ['random', 'fixed_random', 'incremental']"
            )

    def get_condition(self):
        """Get the condition for the next trial

        If the condition list is empty, get the next block and initialize it.

        Returns
        -------
        condition:
            Condition name
        """
        if not self.condition_list:
            # check if we've reached the max number of blocks
            if self.max_blocks is not None and self.block_number >= self.max_blocks:
                self.graceful_exit()
                self.condition = None
                return
            # otherwise increment and get next block
            self.block_number += 1
            self.init_block(next(self.blocks))
        self.condition = self.condition_list.pop(0)
        return self.condition

    def update_condition_list(self, outcome, trialunique=False):
        """Update condition list

        If the trial was completed correctly, do nothing

        If the trial was completed incorrectly, determine how to update
        condition list based on the retry_method.

        If retry_method is None or max_retries has been reached
        for this condition, do nothing.

        If retry_method is "immediate", insert the current condition
        back into the list at the first position.

        If retry_method is "delayed", insert the current condition
        back into the list at a random position.

        Parameters
        ----------
        correct: bool, default True
            Whether the trial was completed correctly
        trialunique: bool, default False
            Whether the experiment is set up to run in a trial unique manner

        Raises
        ------
        ValueError
            If `retry_method` is not one of `None`, `"immediate"` or `"delayed"`

        Warns
        -----
        UserWarning
            If using delayed retry method and `trialunique` is True
        """
        # always ignore correct trials
        if outcome == 1:
            return
        # if retry no response only, and no response, ignore
        if self.active_block.get("retry_noresponse_only", False) and outcome != 0:
            return

        retry_method = self.active_block.get("retry_method")
        max_retries = self.active_block.get("max_retries")
        if max_retries is not None:
            if self.n_retries[self.condition] >= max_retries:
                return
            self.n_retries[self.condition] += 1

        if retry_method is None:
            return
        elif retry_method == "delayed":
            idx = random.randint(0, len(self.condition_list))
            self.condition_list.insert(idx, self.condition)
            if trialunique:
                warnings.warn(
                    "Delayed retry does not repeat items in trial unique experiments"
                )
        elif retry_method == "immediate":
            self.condition_list.insert(0, self.condition)
            if trialunique:
                self.itemid -= 1
        else:
            raise ValueError(
                "'retry_method' must be one of [None,'delayed','immediate']"
            )
