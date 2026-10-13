"""A scripted stand-in for a chat model, so tests never call an API."""

from langchain_core.runnables import RunnableLambda


class ScriptedModel:
    """Answers each call with the next scripted dict, and records the prompts."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.prompts = []

    def with_structured_output(self, schema):
        def answer(msgs):
            self.prompts.append(msgs)
            item = self.answers.pop(0)
            if isinstance(item, Exception):
                raise item
            return schema(**item)

        return RunnableLambda(answer)
