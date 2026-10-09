"""Laya Decision Maker"""

from laya.agent import Agent, load

from ...devices import ToolProvider
from ...home import Home
from .models import (
    DeviceNameDecision,
    DeviceType,
    DeviceTypeDecision,
)


class LayaClient:
    def initialise(self) -> Agent:
        # Load classifier agent from hf
        self.agent: Agent = load("convaiinnovations/laya")
        return self.agent

    def select_device(self, utterance: str, home: Home) -> tuple[ToolProvider, str]:
        """Select the registered device targeted by the user's utterance.

        Args:
            utterance (str): Text representation of the words the user has spoken.
            home (Home): Home object.

        Returns:
            ObjectSelection
        """

        # Classify device type
        device_type_decision = self._identify_device_type(utterance)

        # Grab available devices from the device type
        devices = getattr(home, device_type_decision.device_type)
        device_names = list(devices.keys())

        # Find the correct device name
        device_name_decision = self._identify_device_name(
            utterance, device_type_decision.device_type, device_names
        )

        # Return the device
        return devices[
            device_name_decision.device_name
        ], device_type_decision.device_type

    def _identify_device_type(self, utterance) -> DeviceTypeDecision:
        """Decide what device can handle this request

        Args:
            utterance (str): _description_
        """

        result = self.agent.decide(
            state=utterance, schema=DeviceType, return_details=True
        )

        print(result)

        # Unpack answer
        answer = result.values["device_type"]  # "speaker"
        answer_confidence = result.answer_confidence["device_type"]
        decision_confidence = result.confidence[
            "device_type"
        ]  # 0.79  1 - H(p)/log(k) on this 3-option `choice` field
        probabilities = result.probabilities[
            "device_type"
        ]  # {"speaker": 0.94, "tv": 0.06, "light": 0.0}

        """
        result = agent.decide(state, schema=Ticket, return_details=True)
        result.values["department"]            # "billing"
        result.answer_confidence["department"] # 0.94  max(p): the quantity min_confidence gates on
        result.confidence["department"]        # 0.79  1 - H(p)/log(k) on this 3-option `choice` field
        result.probabilities["department"]     # {"billing": 0.94, "support": 0.06, "sales": 0.0}
        result.usage                           # {"input_tokens": ..., "output_tokens": 0,
                                            #  "state_tokens": ..., "state_tokens_dropped": ...,
                                            #  "truncated": ..., "truncated_questions": [...]}
        result.routing                         # the Router decision, when a Router answered
        """
        # Build device decision
        device_decision = DeviceTypeDecision(
            device_type=answer,
            answer_confidence=answer_confidence,
            decision_confidence=decision_confidence,
            probabilities=probabilities,
        )

        return device_decision

    def _identify_device_name(
        self, utterance: str, device_type: str, device_names: list[str]
    ):
        """Decide what device can handle this request

        Args:
            utterance (str): _description_
        """
        criteria = {
            name: f"The user is referring to the {name} {device_type}."
            for name in device_names
        }

        result = self.agent.decide(
            state=utterance,
            questions={
                "device_name": {
                    "type": "choice",
                    "instructions": f"Which {device_type} is the user referring to?",
                    "criteria": criteria,
                }
            },
            return_details=True,
        )
        print()
        print(result)

        # Unpack answer
        answer = result.answers["device_name"]["choice"]  # "speaker"
        answer_confidence = result.answer_confidence["device_name"]
        decision_confidence = result.confidence[
            "device_name"
        ]  # 0.79  1 - H(p)/log(k) on this 3-option `choice` field
        probabilities = result.probabilities[
            "device_name"
        ]  # {"speaker": 0.94, "tv": 0.06, "light": 0.0}

        """
        result = agent.decide(state, schema=Ticket, return_details=True)
        result.values["department"]            # "billing"
        result.answer_confidence["department"] # 0.94  max(p): the quantity min_confidence gates on
        result.confidence["department"]        # 0.79  1 - H(p)/log(k) on this 3-option `choice` field
        result.probabilities["department"]     # {"billing": 0.94, "support": 0.06, "sales": 0.0}
        result.usage                           # {"input_tokens": ..., "output_tokens": 0,
                                            #  "state_tokens": ..., "state_tokens_dropped": ...,
                                            #  "truncated": ..., "truncated_questions": [...]}
        result.routing                         # the Router decision, when a Router answered
        """
        # Build device decision
        device_name_decision = DeviceNameDecision(
            device_name=answer,
            answer_confidence=answer_confidence,
            decision_confidence=decision_confidence,
            probabilities=probabilities,
        )

        return device_name_decision
