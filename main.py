import sys
import time
from os import path, remove

from PyQt5 import QtWidgets
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from pandas import DataFrame
from bokeh.models import CustomJS, ColumnDataSource, OpenURL, TapTool, WheelZoomTool
from bokeh.plotting import figure, output_file, show
from bokeh.layouts import column
from bokeh.models.widgets import CheckboxButtonGroup

import form

IMPLICITLY_WAIT = 10
SLEEP_ON_PAGE = 0.3
PLAYERS = "https://fastcup.net/players.html"
FIGHT = 'https://fastcup.net/fight.html?id=%s'

# form.ui -> form.py: pyuic5 form.ui -o form.py
# build: pyinstaller -F -w --clean main.py
class ExampleApp(QtWidgets.QMainWindow, form.Ui_form_fcstats):
    def __init__(self):
        # access to variables and methods form.py
        super().__init__()

        # init design
        self.setupUi(self)

        # start function by button
        self.button_create_stats.clicked.connect(self.main_process)
        # press the button by enter
        self.button_create_stats.setAutoDefault(True)
        self.line_edit.returnPressed.connect(self.button_create_stats.click)

        self.button_load_file.clicked.connect(self.load_data)

        # selenium settings
        self.capabilities = {
            "browserName": "chrome",
            "version": "latest",
            "javascriptEnabled": True
        }
        self.driver = None

    def main_process(self):
        save_in_file = self.checkbox_save_in_file.isChecked()
        self.save_stats = self.checkbox_save_stats.isChecked()
        player_name = self.line_edit.text()
        self.init_web_driver()
        # open the page
        self.driver.get(PLAYERS)
        self.search_player(player_name)
        try:
            player = self.driver.find_element(By.XPATH, "//div[@class='right_col_textbox']/div[@class='msg']/a[contains(text(), '%s')]" % player_name)
            player.click()
        except NoSuchElementException:
            self.driver.close()
            QtWidgets.QMessageBox.about(self, "Warning!", "Player not found!")
        else:
            try:
                number_of_pages = int(self._get_element_list("//div[@id='mtabs-battles']")[0].split()[-1])
                data = self.data_collection(number_of_pages)
                self.driver.close()
                data = ["\n".join(page) for page in data]
                data = "\n".join(data)
                if save_in_file:
                    self.save_data(data)
            except ValueError:
                self.driver.close()
                QtWidgets.QMessageBox.about(self, "Warning!", "Have no data!")
            else:
                self.visualization(data, player_name)

                # self.common_table(dt)

    def load_data(self):
        self.save_stats = self.checkbox_save_stats.isChecked()
        directory = QtWidgets.QFileDialog.getOpenFileName(self, "Load file", filter="*.txt")
        path_to_file = directory[0]
        if path_to_file:
            with open(path_to_file, 'r', encoding='utf-8') as f:
                data = f.read()
            file_name = path_to_file.split('/')[-1][:-4]
            self.visualization(data, file_name)

    def visualization(self, data, player_name):
        prepared_data = self.data_preparation(data)
        df = self.create_dataframe(prepared_data)
        df_wins_defeats = df[(df.Результат == "Победа") | (df.Результат == "Поражение")]
        self.build_graph_skill_fights(df_wins_defeats, player_name)


    def _get_element_list(self, xpath: str):
        return self.driver.find_element(By.XPATH, xpath).text.split('\n')

    def data_collection(self, number_of_pages: int) -> list:
        data = []
        for i in range(2, number_of_pages + 1):
            data.append(self._get_element_list("//div[@id='mtabs-battles']")[2:])
            # click next page
            self.driver.find_element(By.XPATH, "//div[@id='mtabs-battles']/a[contains(text(), '%d')]" % i).click()
            # for page load
            time.sleep(SLEEP_ON_PAGE)
        data.append(self._get_element_list("//div[@id='mtabs-battles']")[2:])
        return data

    def create_dataframe(self, dt: [list]) -> DataFrame:
        labels = ["Игра", "Дата", "Время", "Канал", "Размер", "Карта",
                  "Сторона", "Результат", "KD", "Скилл", "Деление", "Опыт"]
        return DataFrame.from_records(dt, columns=labels).iloc[::-1]

    def init_web_driver(self):
        self.driver = webdriver.Chrome(executable_path='chromedriver.exe',
                                       desired_capabilities=self.capabilities)
        self.driver.implicitly_wait(IMPLICITLY_WAIT)
        # driver.manage().timeouts().implicitlyWait(10, TimeUnit.SECONDS)
        # driver.manage().timeouts().setScriptTimeout(10, TimeUnit.SECONDS)

    def data_preparation(self, data: str) -> [list]:
        """
        Don't try to understand it, just believe"""
        dt = []
        for line in data.split("\n"):
            if not line:
                continue
            ln = line.split()
            fight = ln[0]
            date = " ".join(ln[1:4])
            time = ln[4]
            type_game = " ".join(ln[5:8])
            xvsx = "".join(ln[9:12])
            mp = ln[12]
            side, result, kd, sep = "", "", "", ""
            points = 0.0
            exp = 0
            side = "T" if ln[13] == "A" else "CT"
            if ln[14] == "Не":
                result = " ".join(ln[14:16])
            elif ln[14] == "Ошибка":
                result = ln[14]
            else:
                result = ln[14]
                kd = ln[15]
                points = float(ln[16])
                try:
                    if ln[17][0] == "(":
                        sep = ln[17]
                        exp = ln[18]
                    else:
                        sep = ""
                        try:
                            exp = ln[17]
                        except IndexError:
                            pass
                except IndexError:
                    pass
            dt.append([fight, date, time, type_game,
                      xvsx, mp, side, result, kd, points, sep, exp])
        return dt

    def search_player(self, player_name: str):
        element = self.driver.find_element(By.XPATH, "//input[@placeholder='Ник или STEAM_0:X:XXXXXX']")
        element.send_keys(player_name)
        element.send_keys(Keys.ENTER)

    def save_data(self, data):
        """"Save data in text file"""
        directory = QtWidgets.QFileDialog.getSaveFileName(self, "Save file", filter="*.txt")
        if directory[0]:
            with open(directory[0], "w", encoding='utf-8') as f:
                f.write(data)

    def build_graph_skill_fights(self, df: DataFrame, player_name: str):
        player_name = self.replace_unsupported_chars(player_name)
        output_file(f"Fights_{player_name}.html")

        y = df.Скилл
        x = range(1, len(y) + 1)
        fights = list(map(lambda x_: x_[1:], df.Игра))

        source = ColumnDataSource(data=dict(
            x=x,
            y=y,
            fights=fights,
            kd=df.KD,
            map=df.Карта,
            size=df.Размер
        ))

        TOOLTIPS = [
            ('KD', "@kd"),
            ('Skill', '@y'),
            ('Map', '@map'),
            ('xVSx', '@size')
        ]

        # TODO: fix fights in tooltips
        # create a new plot
        p = figure(title="Щелкай на битвы!", x_axis_label='Номер битвы', y_axis_label='Скилл',
                   tools="pan,tap,wheel_zoom", active_drag="pan", tooltips=TOOLTIPS, sizing_mode='stretch_both')

        p.line('x', 'y', source=source, line_width=2)
        p.circle('x', 'y', size=8, source=source, legend="Битвы")
        p.toolbar.active_scroll = p.select_one(WheelZoomTool)

        url = 'https://fastcup.net/fight.html?id=@fights'
        taptool = p.select(type=TapTool)
        taptool.callback = OpenURL(url=url)


        def callback(source=source, window=None):
            data = source.data

            f = cb_obj.attributes.active
            console.log(data['map'])

            source.change.emit()

        maps = list(set(df.Карта))
        checkbox_button_group = CheckboxButtonGroup(labels=maps, active=list(range(len(maps))),
                                                    callback=CustomJS.from_py_func(callback))
        layout = column(checkbox_button_group, p)

        # show the results
        show(layout)

        if not self.save_stats:
            time.sleep(3)  # for load file
            remove(f"Fights_{player_name}.html")

    @staticmethod
    def replace_unsupported_chars(string: str) -> str:
        for i in r'/\:*?«<>|"':
            string = string.replace(i, '_')
        return string


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = ExampleApp()
    window.show()
    app.exec_()


if __name__ == '__main__':
    main()
