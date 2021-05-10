# %%

import time
from datetime import datetime
from dateutil import parser

import fetcher
import telebot
from chrome_custom import ChromeCustom
from customLogging import get_logger
from db import dbUtil
from params import config

logger = get_logger('booker', log_level=5)


# %%

def login(driver, user_id):
    user_info = dbUtil.get_user_info(user_id)
    if user_info is None:
        return 1

    phone_number = user_info.get('phoneNumber', None)
    if phone_number is None:
        return 2

    driver.get('https://selfregistration.cowin.gov.in/')
    time.sleep(1)

    login_input = driver.find_element_by_css_selector('#mat-input-0')
    login_input.send_keys(phone_number)
    time.sleep(1)

    login_button = driver.find_element_by_css_selector('ion-button.login-btn')
    login_button.click()

    dbUtil.set_meta(user_id, 'otpMeta', None)

    start_time = time.time()

    telebot.send_message(
        user_id=user_id,
        message=f"Please send OTP to login on CoWin website. "
                f"We're trying to book your appointments for phone number {phone_number} "
                "\n\nSend OTP in format 'otp <verification-code>'"
    )

    # keep checking if otp was added by user
    timeout_time = 170

    otp = None
    while True:
        # check if login request timed out
        is_timed_out = (time.time() - start_time) > timeout_time
        if is_timed_out:
            break

        user_info = dbUtil.get_user_info(user_id)
        if user_info is not None:
            otp_meta = user_info.get('otpMeta', None)
            if otp_meta is not None:
                otp = otp_meta.get('otp', None)
                if otp is not None:
                    break

        time.sleep(1)

    is_timed_out = (time.time() - start_time) > timeout_time
    if is_timed_out:
        response = "Login attempt failed. Request timed out."
        ret = 3
    elif otp is None:
        response = "Login attempt failed. Couldn't get OTP."
        ret = 4
    else:
        otp = int(otp)
        otp_input = driver.find_element_by_xpath('//*[@id="mat-input-1"]')
        otp_input.send_keys(otp)

        otp_verify_button = driver.find_element_by_css_selector('ion-button.vac-btn')
        otp_verify_button.click()

        logout_btn = None
        try:
            logout_btn = driver.find_element_by_css_selector('ul.logout-text')
        except:
            pass

        if logout_btn is not None:
            response = 'Logged in successfully to CoWin website.'
            ret = 0
        else:
            response = 'Failed to login.'
            ret = 5

    telebot.send_message(user_id=user_id, message=response)
    return ret


# %%

def book(driver, user_id, book_btn):
    driver.execute_script("arguments[0].scrollIntoView();", book_btn)
    book_btn.click()
    time.sleep(1)

    time_slot_btns = driver.find_elements_by_css_selector('ion-button.time-slot')
    time_slot_btns[1].click()

    captcha = driver.find_element_by_css_selector('#captchaImage')
    telebot.send_photo_file(user_id, 'Enter captcha.', captcha.screenshot_as_png)

    dbUtil.set_meta(user_id, 'captchaMeta', None)

    start_time = time.time()

    # keep checking if otp was added by user
    timeout_time = 300

    captcha = None
    while True:
        is_timed_out = (time.time() - start_time) > timeout_time
        if is_timed_out:
            break

        user_info = dbUtil.get_user_info(user_id)
        if user_info is not None:
            captcha_meta = user_info.get('captchaMeta', None)
            if captcha_meta is not None:
                captcha = captcha_meta.get('captcha', None)
                if captcha is not None:
                    break

        time.sleep(1)

    if captcha is None:
        return 1


# %%

def process(driver):
    response = ''
    ret = 0

    beneficiary_cards = driver.find_elements_by_css_selector('ion-grid.cardblockcls', True)
    if len(beneficiary_cards) == 0:
        response = 'No beneficiaries registered for user.'
        ret = 1
    else:
        start = 2
        for idx, _ in enumerate(beneficiary_cards[start:], start):
            beneficiary_cards = driver.find_elements_by_css_selector('ion-grid.cardblockcls', True)

            card = beneficiary_cards[idx]
            driver.execute_script("arguments[0].scrollIntoView();", card)

            birth_year = card.find_element_by_xpath(
                './/span[contains(., "Year of Birth:")]/following-sibling::span').text
            birth_year = int(birth_year)

            pincode = 263139
            age = datetime.now().year - birth_year

            fetcher.fetch_for_pincode(pincode)
            latest_timestamp, slots = fetcher.check_slots_available(pincode, age)
            if slots is None or len(slots) == 0:
                response = 'No slots available.'
                ret = 2
            else:
                schedule_btn = card.find_element_by_xpath('.//a[contains(., "Schedule")]')
                schedule_btn.click()
                time.sleep(1)

                schedule_now_btn = driver.find_element_by_css_selector('ion-button.schedule-appointment')
                schedule_now_btn.click()
                time.sleep(1)

                pincode_input = driver.find_element_by_xpath('//input[@formcontrolname="pincode"]')
                pincode_input.send_keys(pincode)

                search_btn = driver.find_element_by_css_selector('ion-button.pin-search-btn')
                search_btn.click()
                time.sleep(1)

                mapping = dict()

                dates = driver.find_elements_by_css_selector('ul.availability-date-ul li.availability-date')
                dates = [i.text for i in dates[:7]]

                centers = driver.find_elements_by_css_selector(
                    'mat-selection-list[formcontrolname=center_id] > div.ng-star-inserted')

                for center in centers:
                    center_name = center.find_element_by_css_selector('h5.center-name-title').text
                    center_name = center_name.lower()

                    mapping[center_name] = {}

                    btns_by_date = center.find_elements_by_css_selector(
                        'ion-col.slot-available-main ul li div.vaccine-box a')

                    for i, btn in enumerate(btns_by_date, 0):
                        date = dates[i]
                        date = parser.parse(date)
                        date = date.strftime('%d-%m-%Y')

                        mapping[center_name][date] = btn

                # based on slots and mapping, try to book

                is_booked = False

                for center_name in slots:
                    center = slots[center_name]
                    center_name = center_name.lower()

                    for slot in center['sessions']:
                        date = slot['date']

                        book_btn = mapping.get(center_name, dict()).get(date, None)
                        if book_btn is None:
                            continue

                        ret = book(driver, user_id, book_btn)
                        if ret == 0:
                            is_booked = True
                            break

                    if is_booked:
                        break

    telebot.send_message(user_id=user_id, message=response)
    return ret


# %%

if __name__ == '__main__':
    driver = ChromeCustom(headless=False)

    user_id = config['admin_user_id']
    user_id = int(user_id)

    ret = login(driver, user_id)
    print(ret)
