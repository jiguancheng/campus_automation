import time
from tomllib import loads
from typing import Optional, Dict

from selenium.webdriver import Edge
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.remote.webelement import WebElement

from answer_quiz import AnswerQuiz

login_configs = loads(open(r"key.toml", encoding="utf-8").read())
configs = loads(open(r"config.toml", encoding="utf-8").read())
account, pwd = login_configs.values()
book_keyword, units = configs.values()


def get_parent(element: WebElement, times: int = 1):
    if times == 1:
        return element.find_element(By.XPATH, "./..")
    return get_parent(element.find_element(By.XPATH, "./.."), times - 1)


def login(driver: Edge):
    """Create a drive and return it after login to UCampus"""
    driver.get("https://ucloud.unipus.cn/home")
    while "login" not in driver.current_url:  # Waiting for redirection
        time.sleep(.25)
    time.sleep(3)  # Waiting for the page to load
    account_input = driver.find_element(By.XPATH,
                                        r"""/html/body/div[2]/div/div/div[2]/div[1]/div[1]/div[1]/form/div[1]/input""")
    pwd_input = driver.find_element(By.XPATH,
                                    r"""/html/body/div[2]/div/div/div[2]/div[1]/div[1]/div[1]/form/div[2]/input""")
    accept_check_box = driver.find_element(By.XPATH,
                                           r"""/html/body/div[2]/div/div/div[2]/div[1]/div[2]/div/label/input""")
    login_button = driver.find_element(By.XPATH, r"""/html/body/div[2]/div/div/div[2]/div[1]/div[2]/button""")
    account_input.send_keys(account)
    pwd_input.send_keys(pwd)
    accept_check_box.click()
    login_button.click()
    return driver


def get_records(driver: Edge, full: bool = False, search_key: Optional[str] = None):
    for i in range(1, units):
        key = f"{i}-{i + 1}"
        arrow = driver.find_element(By.XPATH, f"""//tr[@data-row-key = "{key}"]""").find_element(By.TAG_NAME, "svg")
        arrow.click()  # expand the unit details

    if search_key is not None:
        items = [driver.find_element(By.XPATH, f"""//tr[@data-row-key = "{search_key}"]""")]
    else:
        items = driver.find_elements(By.CLASS_NAME, "courses-studyrecord_scaleLable__Fn9nw")
        items = list(map(lambda x: get_parent(x, 4), items))

    undone = []
    for i in items:
        try:
            i.find_element(By.TAG_NAME, "svg")
        except:
            undone.append(i)
    print(f"Left: {len(undone)} / {len(items)}")
    return items if full else undone


def goto_home(driver: Edge):
    driver.get(r"https://ucloud.unipus.cn/app/cmgt/course-management")  # Jump to classes page
    time.sleep(5)  # Waiting for load
    books = driver.find_elements(By.CLASS_NAME, r"course-name")  # Get the classes
    print(f"Books: {", ".join(map(lambda x: x.text, books))}")
    for i in books:
        if book_keyword in i.text:
            print(f"Choose class: {i.text}")
            i.click()
            break
    else:
        raise ValueError(f"Failed to find the book with keyword: {book_keyword}")
    time.sleep(5)
    record_tab = driver.find_element(By.XPATH, r"""//div[@data-node-key = "record"]""")
    record_tab.click()


def process_record(driver: Edge, record: str) -> Optional[Dict]:
    """

    status:
         0: Finished
        -1: PC not support
        -2: Known type but can't finish
        -3: Unknown type

    :param driver:
    :param record:
    :return: A dict {status: int, info: str, Optional[record]: bytes}
    """
    record = get_records(driver, search_key=record)[0]
    record.find_element(By.CLASS_NAME, "courses-studyrecord_operationItem__8GU5t").click()  # goto page
    time.sleep(5)
    try:  # deal with the popup
        i_know = driver.find_element(By.CLASS_NAME, "iKnow")
        i_know.click()
    except:
        pass
    time.sleep(1)
    try:  # deal with the dialog
        driver.find_element(By.CLASS_NAME, "ant-modal-wrap").find_element(By.TAG_NAME, "button").click()
    except Exception as e:
        print("Failed to close the popup via click :< fuck U campus")

    question_wrap = driver.find_element(By.CLASS_NAME, "question-wrap")

    result = AnswerQuiz(driver, question_wrap).answer_quiz()
    return result


options = Options()
options.set_capability("ms:loggingPrefs", {'performance': 'ALL'})
driver = Edge(options=options)
driver.execute_cdp_cmd("Network.enable", {})

login(driver)  # Login
print("Login success")
time.sleep(3)  # Waiting for the login to complete

goto_home(driver)
time.sleep(2)  # Wait for load
records = list(map(lambda x: x.get_attribute("data-row-key"), get_records(driver)))

for i, j in enumerate(records):
    time.sleep(2)
    goto_home(driver)
    time.sleep(2)
    print(f"start processing: {i} / {len(records)}  [{j}]")
    result = process_record(driver, j)
    print(result)

time.sleep(10000)
