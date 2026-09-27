from etienne.integrations.home_assistant import HomeAssistantClient


class Speaker:
    def __init__(
        self,
        entity_id: str,
        ha: HomeAssistantClient,
    ):
        self.entity_id = entity_id
        self.ha = ha

    def play(
        self,
    ) -> None:
        pass

    def pause(self) -> None:
        pass