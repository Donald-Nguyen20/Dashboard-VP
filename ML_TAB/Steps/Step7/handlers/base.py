from abc import ABC, abstractmethod
import pandas as pd

class BaseHandler(ABC):
    bundle_type: str

    @abstractmethod
    def predict(self, bundle: dict, data: pd.DataFrame) -> pd.DataFrame:
        """Return a result dataframe with prediction columns added."""
        ...