"""Consumer-facing reasons an offer cannot issue a clip."""


class OfferNotClippable(Exception):
    user_message = "This offer isn't available right now."

    def __init__(self):
        super().__init__(self.user_message)


class OfferWindowNotStarted(OfferNotClippable):
    user_message = "This offer isn't live yet — check back soon."


class OfferWindowClosed(OfferNotClippable):
    user_message = "This offer has ended."


class OfferSoldOut(OfferNotClippable):
    user_message = "This offer has reached its clip limit."
