"""Laya Decision Maker"""

from laya.agent import Agent, load

from ...devices import Device
from ...home import Home
from .models import (
    DeviceKeyDecision,
    DeviceType,
    DeviceTypeDecision,
)


class LayaClient:
    def initialise(self) -> Agent:
        # Load classifier agent from hf
        self.agent: Agent = load("convaiinnovations/laya")
        return self.agent

    def select_device(self, utterance: str, home: Home) -> tuple[Device, str]:
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
        device_keys = list(devices.keys())

        # Find the correct device key
        device_key_decision = self._identify_device_key(
            utterance, device_type_decision.device_type, device_keys
        )

        # Return the device
        return devices[
            device_key_decision.device_key
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

    def _identify_device_key(
        self, utterance: str, device_type: str, device_keys: list[str]
    ):
        """Decide what device can handle this request

        Args:
            utterance (str): _description_
        """
        criteria = {
            device_key: f"The user is referring to the {device_key} {device_type}."
            for device_key in device_keys
        }

        result = self.agent.decide(
            state=utterance,
            questions={
                "device_key": {
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
        answer = result.answers["device_key"]["choice"]  # "speaker"
        answer_confidence = result.answer_confidence["device_key"]
        decision_confidence = result.confidence[
            "device_key"
        ]  # 0.79  1 - H(p)/log(k) on this 3-option `choice` field
        probabilities = result.probabilities[
            "device_key"
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
        device_key_decision = DeviceKeyDecision(
            device_key=answer,
            answer_confidence=answer_confidence,
            decision_confidence=decision_confidence,
            probabilities=probabilities,
        )

        return device_key_decision
