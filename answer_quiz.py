import json
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Optional, Dict, List

from selenium.webdriver import Edge
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement


class QuizTypes(StrEnum):
    PCNotSupport = "PC not supported"
    WatchVideo = "Watching video"
    Discussion = "Discussion"
    FillInBlanks = "FillInBlanks"
    SingleChoose = "Single choose"
    MultiChoose = "Multi choose"
    Unknown = "Unknown type"


class MultiType(StrEnum):
    NotTested = "not tested"
    WrongAnswer = "wrong answer"
    AcceptAnswer = "accepted"


@dataclass
class TestData:
    answer: int
    right: bool


@dataclass
class MultiData:
    option_cnt: int
    answers: List[MultiType]
    expected_num: Optional[int] = None
    find_cnt: int = 0


class AnswerQuiz:
    def __init__(self, driver: Edge, wrap: WebElement):
        self.driver = driver
        self.content = wrap
        self.type = self.check_type()
        print(f"Got type: {self.type}")

    def solve(self) -> Dict:
        check = self.if_cannot_deal()
        if check is not None:
            return check
        return self.answer_quiz()

    def check_support(self) -> bool:
        return "不支持" in self.content.text

    def check_single_choose(self):
        try:
            test = self.content.find_elements(By.CLASS_NAME, "question-common-abs-choice")
            if not test:
                return False
            return test[0].get_attribute("class") == "question-common-abs-choice"
        except:
            return False

    def check_multi_choose(self):
        try:
            test = self.content.find_elements(By.CLASS_NAME, "question-common-abs-choice")
            if not test:
                return False
            return test[0].get_attribute("class") == "question-common-abs-choice multipleChoice"
        except:
            return False

    def check_type(self) -> str:
        if self.check_support():
            return QuizTypes.PCNotSupport
        if self.check_single_choose():
            return QuizTypes.SingleChoose
        if self.check_multi_choose():
            return QuizTypes.MultiChoose
        # Todo: Finish other types
        return QuizTypes.Unknown

    def if_cannot_deal(self) -> Optional[Dict]:
        if self.type == QuizTypes.PCNotSupport:
            return {"status": -1, "record": self.content.screenshot_as_png,
                    "info": "This type of quiz is not supported on PC."}
        if self.type in [QuizTypes.Discussion, QuizTypes.FillInBlanks]:
            return {"status": -2, "record": self.content.screenshot_as_png,
                    "info": f"Known type: {self.type}, but not supported to automate yet."}
        return None

    def answer_quiz(self) -> Dict:
        if self.type == QuizTypes.SingleChoose:
            return self.deal_single_choose()
        if self.type == QuizTypes.MultiChoose:
            return self.deal_multi_choose()
        return {"status": -2, "info": "Unknown problem"}

    def deal_single_choose(self, test_data: Optional[List[TestData]] = None):
        ques = self.content.find_elements(By.CLASS_NAME, "question-common-abs-choice")
        if test_data is None:
            test_data = [TestData(-1, False) for _ in range(len(ques))]
        for i in test_data:
            if not i.right:
                i.answer += 1

        for i in range(len(ques)):
            ques[i].find_elements(By.CLASS_NAME, "option")[test_data[i].answer].find_element(By.CLASS_NAME,
                                                                                             "caption").click()

        # submit
        self.driver.find_element(By.TAG_NAME, "footer").find_element(By.CLASS_NAME, "btn").click()

        result = self.get_result()
        final = json.loads(result[-1]["body"])
        scores: List[int] = final["data"]["state"]["__EXTEND_DATA__"]["__SUBMIT_INFO__"]["state"]["score"]
        for i in range(len(scores)):
            if scores[i] == 0:
                test_data[i].right = False
            else:
                test_data[i].right = True
        if min(scores) != 0:
            return {"status": 0}

        button = self.driver.find_element(By.TAG_NAME, "footer").find_element(By.CLASS_NAME, "btn")
        if "返回" in button.text:
            button.click()  # get back
        else:
            self.driver.refresh()
            time.sleep(3)

        time.sleep(2)
        self.content = self.driver.find_element(By.CLASS_NAME, "question-wrap")
        return self.deal_single_choose(test_data)

    def deal_multi_choose(self, test_data: Optional[MultiData] = None):
        options = self.content.find_elements(By.CLASS_NAME, "option")
        if test_data is None:
            test_data = MultiData(len(options), [MultiType.NotTested] * len(options))

        if test_data.expected_num is None or test_data.find_cnt != test_data.expected_num:
            next_index = test_data.answers.index(MultiType.NotTested)
            binary = "0" * next_index + "1" + "0" * (test_data.option_cnt - next_index - 1)
        else:
            binary = ""
            for i in test_data.answers:
                binary += "1" if i == MultiType.AcceptAnswer else "0"

        for i in range(len(options)):
            if binary[i] != "0":
                options[i].find_element(By.CLASS_NAME, "caption").click()

        # submit
        self.driver.find_element(By.TAG_NAME, "footer").find_element(By.CLASS_NAME, "btn").click()

        result = self.get_result()
        final = json.loads(result[-1]["body"])
        score: float = final["data"]["state"]["__EXTEND_DATA__"]["__SUBMIT_INFO__"]["state"]["score"][0]

        if score == 1:
            return {"status": 0}

        if score == 0:
            test_data.answers[binary.find("1")] = MultiType.WrongAnswer
        else:
            test_data.answers[binary.find("1")] = MultiType.AcceptAnswer
            test_data.find_cnt += 1
            test_data.expected_num = round(1 / score)

        button = self.driver.find_element(By.TAG_NAME, "footer").find_element(By.CLASS_NAME, "btn")
        if "返回" in button.text:
            button.click()  # get back
            time.sleep(2)
            self.content = self.driver.find_element(By.CLASS_NAME, "question-wrap")
            options = self.content.find_elements(By.CLASS_NAME, "option")
            for i in range(len(options)):
                if binary[i] != "0":
                    options[i].find_element(By.CLASS_NAME, "caption").click()
        else:
            self.driver.refresh()
            time.sleep(3)
            time.sleep(1)
            self.content = self.driver.find_element(By.CLASS_NAME, "question-wrap")

        return self.deal_multi_choose(test_data)

    def get_result(self):
        time.sleep(1)
        responses = {}
        logs = self.driver.get_log("performance")

        for entry in logs:
            log_message = json.loads(entry["message"])
            message = log_message.get("message", {})
            method = message.get("method")

            if method == 'Network.responseReceived':
                params = message.get('params', {})
                request_id = params.get('requestId')
                response = params.get('response', {})
                if request_id:
                    responses[request_id] = {
                        'url': response.get('url'),
                        'status': response.get('status'),
                        'headers': response.get('headers'),
                        'body': None
                    }

            elif method == 'Network.loadingFinished':
                params = message.get('params', {})
                request_id = params.get('requestId')
                if request_id in responses:
                    try:
                        # 获取响应体
                        body = self.driver.execute_cdp_cmd(
                            'Network.getResponseBody',
                            {'requestId': request_id}
                        )
                        responses[request_id]['body'] = body.get('body', '')[:10000]
                    except Exception as e:
                        del responses[request_id]
        responses = list(
            filter(lambda x: x.get("status", 0) == 200 and x.get("headers", {}).get("Content-Encoding", "") == "gzip",
                   responses.values()))
        return responses

        # 假设延迟后继续处理，根据实际情况调整
