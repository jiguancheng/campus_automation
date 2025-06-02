import time
from tomllib import loads

from selenium.webdriver import Edge, EdgeService
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

login_configs = loads(open(r".\..\key.toml", encoding="utf-8").read())
configs = loads(open(r"config.toml", encoding="utf-8").read())
account, pwd = login_configs.values()
book_keyword, units, stop_time, loop_time = configs["get_time"].values()


def get_parent(element: WebElement, times: int = 1):
    if times == 1:
        return element.find_element(By.XPATH, "./..")
    return get_parent(element.find_element(By.XPATH, "./.."), times - 1)


def text_to_time(text: str) -> int:
    if text == "-":
        return 0
    temp = text.split(":")
    return int(temp[0]) * 3600 + int(temp[1]) * 60 + int(temp[2])


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


def get_records(driver: Edge, full: bool = False):
    for i in range(1, units):
        key = f"{i}-{i + 1}"
        arrow = driver.find_element(By.XPATH, f"""//tr[@data-row-key = "{key}"]""").find_element(By.TAG_NAME, "svg")
        arrow.click()  # expand the unit details
    items = driver.find_elements(By.CLASS_NAME, "courses-studyrecord_scaleLable__Fn9nw")
    items = list(map(lambda x: get_parent(x, 4), items))

    print(f"Found {len(items)} items.")

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

service = EdgeService(executable_path=r".\..\msedgedriver.exe")
driver = Edge(service=service)
driver.execute_cdp_cmd("Network.enable", {})
login(driver)  # Login
print("Login success")
time.sleep(3)  # Waiting for the login to complete

for _ in range(loop_time):
    goto_home(driver)
    time.sleep(10)  # Wait for load
    records = get_records(driver, True)
    durations = []
    for i in records:
        text = i.find_elements(By.CLASS_NAME, "ant-table-cell")[2].text
        durations.append(text_to_time(text))
    min_index = durations.index(min(durations))
    print(durations)
    print(f"choose index: {min_index}, value: {durations[min_index]}")
    records[min_index].find_elements(By.CLASS_NAME, "ant-table-cell")[-1].find_element(By.TAG_NAME, "a").click()
    time.sleep(5)
    try:  # deal with the popup
        IKnow = driver.find_element(By.CLASS_NAME, "iKnow")
        IKnow.click()
    except:
        pass
    time.sleep(1)
    try:  # deal with the dialog
        driver.find_element(By.CLASS_NAME, "ant-modal-wrap").find_element(By.TAG_NAME, "button").click()
    except Exception as e:
        print("Failed to close the popup via click :< fuck U campus")
    time.sleep(stop_time)
