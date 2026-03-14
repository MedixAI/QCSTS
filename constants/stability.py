# constants/stability.py


class StudyType:
    """
    The three ICH-defined stability study types.
    When a batch is created, one of these is selected.
    ScheduleEngine uses this to determine which timepoints to generate.
    """
    LONG_TERM       = "long_term"
    ACCELERATED     = "accelerated"
    INTERMEDIATE    = "intermediate"

    CHOICES = [
        (LONG_TERM,     "Long Term"),
        (ACCELERATED,   "Accelerated"),
        (INTERMEDIATE,  "Intermediate"),
    ]


class ICHTimepoints:
    """
    Test months for each study type as defined by ICH Q1A(R2).
    Month 0 = the day the batch enters the stability chamber.
    """
    LONG_TERM       = [0, 3, 6, 9, 12, 18, 24, 36]
    ACCELERATED     = [0, 1, 3, 6]
    # INTERMEDIATE    = [0, 3, 6, 9, 12]

# TO Revision
class StorageCondition:
    """
    ICH-defined storage conditions for each study type.
    Format: temperature / relative humidity
    """
    LONG_TERM       = "25°C / 60% RH"
    ACCELERATED     = "40°C / 75% RH"
    # INTERMEDIATE    = "30°C / 65% RH"

    MAP = {
        StudyType.LONG_TERM:     LONG_TERM,
        StudyType.ACCELERATED:   ACCELERATED,
        # StudyType.INTERMEDIATE:  INTERMEDIATE,
    }