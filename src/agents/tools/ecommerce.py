from agno.agent import Agent
from agno.tools import Toolkit
from selenium import webdriver
from selenium.webdriver.common.by import By
import time, json

class EcommerceToolkit(Toolkit):
    def __init__(self, **kwargs):
        tools=[self.retrieve_items_list, self.order_items, self.checkout]
        super().__init__(name="shell_tools", tools=tools, **kwargs)
        self.driver = None
        self.items = [] # the html items to avoid retrieving them twice
        self.item_simple = {'items':{}}
        self.cart_items = []

    def _ensure_driver(self):
        if self.driver is None:
            self.driver = webdriver.Chrome()
            self.driver.get("https://www.saucedemo.com/")  # ecommerce demo website
            # self.driver.maximize_window()
            # Log in (demo)
            self.driver.find_element(By.ID, "user-name").send_keys("standard_user")
            self.driver.find_element(By.ID, "password").send_keys("secret_sauce")
            self.driver.find_element(By.ID, "login-button").click()
            time.sleep(2)

    def retrieve_items_list(self, agent: Agent):
        """Retrieve the list of items from saucedemo.com with title, price, and description."""
        
        self._ensure_driver()
        items = self.driver.find_elements(By.CLASS_NAME, "inventory_item")
        self.cart_items = []
        
        for item in items:
            title = item.find_element(By.CLASS_NAME, "inventory_item_name").text
            price = item.find_element(By.CLASS_NAME, "inventory_item_price").text
            description = item.find_element(By.CLASS_NAME, "inventory_item_desc").text
            ipd = {"title": title, "price": price, "description": description}
            self.item_simple['items'][title] = {"price": price, "description": description}
            self.items.append(item)
        return json.dumps(self.item_simple['items'])

    def order_items(self, titles, agent: Agent):
        """
        Add items to the cart by their titles.
        titles is a list of product titles to add to cart.
        """
        self._ensure_driver()
        added = []
        for item in self.items:
            title = item.find_element(By.CLASS_NAME, "inventory_item_name").text
            if title in titles:
                btn = item.find_element(By.CLASS_NAME, "btn_inventory")
                btn.click()
                self.cart_items.append(title)
                added.append(title)
        return json.dumps({"added": added, "cart": self.cart_items})

    def checkout(self, agent: Agent, first_name="John", last_name="Doe", postal_code="12345"):
        """Tool to to checkout the items in the cart current cart
            first_name = the first name of the user if it is known
            last_name = the last name of the user if it is known
            postal_code = postal code of the user if it is known
        """
        self._ensure_driver()
        self.driver.find_element(By.CLASS_NAME, "shopping_cart_link").click()
        time.sleep(1)
        self.driver.find_element(By.ID, "checkout").click()
        time.sleep(1)
        self.driver.find_element(By.ID, "first-name").send_keys(first_name)
        self.driver.find_element(By.ID, "last-name").send_keys(last_name)
        self.driver.find_element(By.ID, "postal-code").send_keys(postal_code)
        self.driver.find_element(By.ID, "continue").click()
        time.sleep(1)
        self.driver.find_element(By.ID, "finish").click()
        time.sleep(1)
        confirmation = self.driver.find_element(By.CLASS_NAME, "complete-header").text
        time.sleep(2)
        self.driver.find_element(By.ID, "back-to-products").click()
        time.sleep(1)
        return json.dumps({"confirmation": confirmation, "cart": self.cart_items}) 

    def __del__(self):
        if self.driver is not None:
            self.driver.quit()

ecommerce = EcommerceToolkit() # to be used as 'Tool' in agent definition
