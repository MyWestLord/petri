"""The 8 brain regions. Each one reads the stimulus and fires spikes on the bus."""
from .amygdala import Amygdala
from .auditory import Auditory
from .cerebellum import Cerebellum
from .dopamine import Dopamine
from .hippocampus import Hippocampus
from .motor import Motor
from .prefrontal import Prefrontal
from .visual import Visual

__all__ = ["Amygdala", "Auditory", "Cerebellum", "Dopamine", "Hippocampus", "Motor", "Prefrontal", "Visual"]
