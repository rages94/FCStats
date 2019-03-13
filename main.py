import sys
import time
from os import path, remove

from PyQt5 import QtWidgets
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from pandas import DataFrame
from bokeh.models import ColumnDataSource, OpenURL, TapTool, WheelZoomTool
from bokeh.plotting import figure, output_file, show
from bokeh.models.widgets import Panel, Tabs
from bokeh.io import curdoc

import form

PATH_TO_WEBDRIVER = 'chromedriver.exe'
IMPLICITLY_WAIT = 10
# because fastcup raise "HTTP 429 Too Many Requests" :\
SLEEP_ON_PAGE = 0.4
PLAYERS = "https://fastcup.net/players.html"
FIGHT = 'https://fastcup.net/fight.html?id=%s'


# form.ui -> form.py: pyuic5 form.ui -o form.py
# build one file: pyinstaller -F -w --clean main.py
# build one dir: pyinstaller -D -w  --clean --add-data "C:/Users/dprokazin/Desktop/Python/FC/chromedriver.exe";"." main.py
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
        # init messagebox
        msg = QtWidgets.QMessageBox
        msg.setStyleSheet(self, "QLabel{min-width: 200px;}")

        save_in_file = self.checkbox_save_in_file.isChecked()
        self.save_stats = self.checkbox_save_stats.isChecked()
        player_name = self.line_edit.text()
        if not path.exists(PATH_TO_WEBDRIVER):
            msg.about(self, "Error!", "WebDriver not found!")
            return
        if not player_name:
            msg.about(self, "Warning!", "<p align='left'>Enter nickname!</p>")
            return
        self.init_web_driver()
        # open the page
        self.driver.get(PLAYERS)
        self.search_player(player_name)
        try:
            player = self.driver.find_element(By.XPATH, "//div[@class='right_col_textbox']/div[@class='msg']/a[contains(text(), '%s')]" % player_name)
            player.click()
        except NoSuchElementException:
            self.driver.close()
            msg.about(self, "Warning!", "Player not found!")
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
                msg.about(self, "Warning!", "Have no data!")
            else:
                self.visualization(data, player_name)

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

        player_name = self.replace_unsupported_chars(player_name)
        output_file(f"Fights_{player_name}.html", title='FCstats')

        tab_skill_fights = self.build_graph_skill_fights(df_wins_defeats)
        tab_maps = self.build_graph_maps(df_wins_defeats)
        tabs = Tabs(tabs=[tab_skill_fights, tab_maps])
        show(tabs)

        if not self.save_stats:
            time.sleep(6)  # for load file
            remove(f"Fights_{player_name}.html")

    def _get_element_list(self, xpath: str):
        return self.driver.find_element(By.XPATH, xpath).text.split('\n')

    def data_collection(self, number_of_pages: int) -> list:
        data = []
        for i in range(2, number_of_pages + 1):
            data.append(self._get_element_list("//div[@id='mtabs-battles']")[2:])
            # click next page
            self.driver.find_element(By.XPATH, "//div[@id='mtabs-battles']/a[contains(text(), '%d')]" % i).click()
            # because fastcup raise "HTTP 429 Too Many Requests" :\
            time.sleep(SLEEP_ON_PAGE)
        data.append(self._get_element_list("//div[@id='mtabs-battles']")[2:])
        return data

    def create_dataframe(self, dt: [list]) -> DataFrame:
        labels = ["Игра", "Дата", "Время", "Канал", "Размер", "Карта",
                  "Сторона", "Результат", "Фраги", "Смерти", "Скилл", "Деление", "Опыт"]
        return DataFrame.from_records(dt, columns=labels).iloc[::-1]

    def init_web_driver(self):
        self.driver = webdriver.Chrome(executable_path=PATH_TO_WEBDRIVER,
                                       desired_capabilities=self.capabilities)
        self.driver.implicitly_wait(IMPLICITLY_WAIT)

    def data_preparation(self, data: str) -> [list]:
        """
        Don't try to understand it, just believe"""
        dt = []
        for line in data.split("\n"):
            if not line:
                continue
            ln = line.split()
            x = ln.index("CS")
            fight = ln[0]
            # TODO: correct date/time someday
            if x == 5:
                date = " ".join(ln[1:4])
            else:
                date = ln[1]
            time = ln[x-1] if not ln.count("назад") else ''
            type_game = " ".join(ln[x:x+3])
            xvsx = "".join(ln[x+4:x+7])
            mp = ln[x+7]
            side, result, k, d, sep = "", "", "", "", ""
            points = 0.0
            exp = 0
            side = "T" if ln[x+8] == "A" else "CT"
            if ln[x+9] == "Не":
                result = " ".join(ln[x+9:x+11])
            elif ln[x+9] == "Ошибка":
                result = ln[x+9]
            else:
                result = ln[x+9]
                k, d = map(int, ln[x+10].split('/'))
                points = float(ln[x+11])
                try:
                    if ln[x+12][0] == "(":
                        sep = ln[x+12]
                        exp = ln[x+13]
                    else:
                        sep = ""
                        try:
                            exp = ln[x+12]
                        except IndexError:
                            pass
                except IndexError:
                    pass
            dt.append([fight, date, time, type_game,
                      xvsx, mp, side, result, k, d, points, sep, exp])
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

    def build_graph_skill_fights(self, df: DataFrame) -> Panel:
        y = df.Скилл
        x = range(1, len(y) + 1)
        fights = list(map(lambda x_: x_[1:], df.Игра))

        source = ColumnDataSource(data=dict(
            x=x,
            y=y,
            fights=fights,
            kills=df.Фраги,
            deaths=df.Смерти,
            map=df.Карта,
            size=df.Размер
        ))

        TOOLTIPS = [
            ('K/D', "@kills/@deaths"),
            ('Skill', '@y{0.0}'),
            ('Map', '@map'),
            ('xVSx', '@size')
        ]

        # TODO: fix fights in tooltips
        # sizing_mode='stretch_both' don't work in tabs :(
        p = figure(title="Щелкай на битвы!", x_axis_label='Номер битвы', y_axis_label='Скилл',
                   tools="pan,tap,wheel_zoom,reset", active_drag="pan", tooltips=TOOLTIPS, width=1000, height=600)

        p.line('x', 'y', source=source, line_width=2, color="cornflowerblue")
        p.circle('x', 'y', size=8, source=source, legend="Битвы")
        p.toolbar.active_scroll = p.select_one(WheelZoomTool)

        url = 'https://fastcup.net/fight.html?id=@fights'
        taptool = p.select(type=TapTool)
        taptool.callback = OpenURL(url=url)
        return Panel(child=p, title='Skill-Fights')

    def build_graph_maps(self, df: DataFrame) -> Panel:
        # prepare data
        df_group = df.Скилл.groupby(df.Карта)
        wins_defeats_count = df.Результат.groupby(df.Карта).value_counts()

        maps = list(df_group.sum().index)
        number_of_fights = df_group.count().values
        skill_sum = df_group.sum().values
        kills_sum = df.Фраги.groupby(df.Карта).sum()
        deaths_sum = df.Смерти.groupby(df.Карта).sum()
        wins_count = [wins_defeats_count[i].get('Победа', 0) for i in maps]
        defeats_count = [wins_defeats_count[i].get('Поражение', 0) for i in maps]

        # maps_sorted = sorted(maps, key=lambda x: skill_sum[maps.index(x)], reverse=True)
        # number_of_fights_sorted = sorted(number_of_fights, key=lambda x: skill_sum[number_of_fights.index(x)], reverse=True)
        # skill_sum_sorted = sorted(skill_sum, reverse=True)

        source = ColumnDataSource(data=dict(
            x=maps,
            y=skill_sum,
            number_of_fights=number_of_fights,
            avg_skill=list(map(lambda x, y: x/y, skill_sum, number_of_fights)),
            kills=kills_sum,
            deaths=deaths_sum,
            wins=wins_count,
            defeats=defeats_count
        ))

        TOOLTIPS = [
            ('Skill', '@y{0.0}'),
            ('Map', '@x'),
            ('Number of fights', '@number_of_fights'),
            ('Average skill', '@avg_skill{0.000}'),
            ('K/D', '@kills/@deaths'),
            ('Wins', '@wins'),
            ('Defeats', '@defeats')
        ]

        # sizing_mode='stretch_both' don't work in tabs :(
        p = figure(x_range=maps, title="unts", tooltips=TOOLTIPS, tools="pan,wheel_zoom,reset", width=1000, height=600)
        p.vbar(x='x', top='y', width=0.9, source=source, color="cornflowerblue")
        p.toolbar.active_scroll = p.select_one(WheelZoomTool)

        # p.xgrid.grid_line_color = None
        p.y_range.start = min(skill_sum)
        return Panel(child=p, title='Skill-Maps')

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
