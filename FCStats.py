# form.ui -> form.py: pyuic5 form.ui -o form.py
# build one file: pyinstaller -F -w --clean --icon=fcstats.ico FCStats.py
# build one dir: pyinstaller -D -w  --clean --icon=fcstats.ico --add-data "chromedriver.exe";"." --add-data "geckodriver.exe";"." --add-data "fcstats.qss";"." --add-data "fcstats.ico";"." FCStats.py
# https://stackoverflow.com/questions/33983860/hide-chromedriver-console-in-python - to hide console
import sys
from time import strftime, localtime, sleep
from os import path, remove, makedirs, getcwd
from datetime import datetime, timedelta
import logging
import sqlite3

from PyQt5 import QtWidgets, QtGui
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, NoSuchWindowException, SessionNotCreatedException, WebDriverException
from pandas import DataFrame
from bokeh.models import ColumnDataSource, OpenURL, TapTool, WheelZoomTool, LinearColorMapper, \
    BasicTicker, PrintfTickFormatter, ColorBar, HoverTool, FactorRange
from bokeh.plotting import figure, output_file, show
from bokeh.models.widgets import Panel, Tabs, DataTable, TableColumn, NumberFormatter
from bokeh.transform import dodge

import form


def make_dir(path_):
    if not path.exists(path_):
        makedirs(path_)


def read_file(filename: str) -> str:
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()


def replace_unsupported_chars(string: str) -> str:
    for i in r'/\:*?«<>|"':
        string = string.replace(i, '_')
    return string


# --------------------- CONFIG ---------------------
# selenium settings
CAPABILITIES = {'Chrome': {'browserName': 'chrome', 'version': 'latest', 'javascriptEnabled': True},
                'Firefox': {"alwaysMatch": {'browserName': 'Firefox', 'browserVersion': 'latest'}, 'javascriptEnabled': True}}
IMPLICITLY_WAIT = 10
PATH_TO_WEBDRIVER = {'Chrome': 'chromedriver.exe',
                     'Firefox': 'geckodriver.exe'}
# because fastcup raise "HTTP 429 Too Many Requests" :\
SLEEP_ON_PAGE = {'Chrome': 0.4,
                 'Firefox': 0}
PLAYERS = 'https://old.fastcup.net/players.html'
FIGHT = 'https://old.fastcup.net/fight.html?id=%s'
DAY_TO_STR = {1: 'Monday', 2: 'Tuesday', 3: 'Wednesday', 4: 'Thursday', 5: 'Friday', 6: 'Saturday', 7: 'Sunday'}
STYLES_FILE = 'fcstats.qss'
ICON = 'fcstats.ico'
FONT = 'Segoe UI'
LOG_DIRECTORY = 'logs'
DB_NAME = 'fcstats.db'

# --------------------------------------------------

# --------------------- FOR LOGS -------------------
log_file_name = "log_%s.txt" % strftime("%Y-%m-%d", localtime())
make_dir(LOG_DIRECTORY)
logger = logging.getLogger("log")
logger.setLevel(logging.DEBUG)
# create the logging file handler
fh = logging.FileHandler(path.join(LOG_DIRECTORY, log_file_name))
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
fh.setFormatter(formatter)
# add handler to logger object
logger.addHandler(fh)

# --------------------------------------------------


class ExampleApp(QtWidgets.QMainWindow, form.Ui_form_fcstats):
class MainWindow(QtWidgets.QMainWindow, form.Ui_form_fcstats):
    def __init__(self):
        # access to variables and methods form.py
        super().__init__()

        # init design
        self.setupUi(self)
        self.setFont(QtGui.QFont(FONT, 8))
        self.setStyleSheet(read_file(STYLES_FILE))
        self.setWindowIcon(QtGui.QIcon(ICON))

        # start function by button
        self.button_create_stats.clicked.connect(self.main_process)
        # press the button by enter
        self.button_create_stats.setAutoDefault(True)
        self.line_edit.returnPressed.connect(self.button_create_stats.click)

        self.button_load.clicked.connect(self.load_data)

        self.driver = None
        self.browser = None
        screen_size = QtWidgets.QDesktopWidget().availableGeometry()
        self.height = int(screen_size.height() * 0.85)
        self.width = int(screen_size.width() * 0.95)

    @staticmethod
    def create_db():
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute("""CREATE TABLE fights
                          (id text, 
                          date text, 
                          time text,
                          year text, 
                          month text, 
                          day text,
                          hour text, 
                          minutes text, 
                          type_game text, 
                          xvsx text, 
                          map text, 
                          side text, 
                          result text, 
                          kills int, 
                          deaths int, 
                          points real, 
                          sep_skill text, 
                          experience int, 
                          player text)
                       """)
        conn.close()

    @staticmethod
    def db_insert_data(player_name: str, data: [list]):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM fights WHERE player = '{player_name}'")
        cursor.executemany(f"INSERT INTO fights VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'{player_name}')", data)
        conn.commit()
        conn.close()

    @staticmethod
    def db_select_data(player_name: str) -> [tuple]:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        data = cursor.execute(f"Select * from fights where player = '{player_name}'").fetchall()
        conn.close()
        return data

    def main_process(self):
        """Searching player, collect data and visualization
        """
        logger.debug('Start collecting data')
        # init messagebox
        msg = QtWidgets.QMessageBox
        # check existing db
        if not path.exists(DB_NAME):
            self.create_db()
        self.browser = self.combox_browsers.currentText()
        player_name = self.line_edit.text()
        if not path.exists(PATH_TO_WEBDRIVER[self.browser]):
            mess = f"WebDriver не найден! Для {self.browser} он должен называться {PATH_TO_WEBDRIVER[self.browser]} и лежать в корне вместе с исполняемым файлом!"
            logger.error(mess)
            msg.about(self, "Ошибка!", mess)
            return
        if not player_name:
            msg.about(self, "Внимание!", "<p align='left'>Введите ник игрока!</p>")
            return
        if not self.init_web_driver():
            return
        # open the page
        self.driver.get(PLAYERS)
        try:
            self.search_player(player_name)
            player = self.driver.find_element(By.XPATH, "//div[@class='right_col_textbox']/div[@class='msg']/a[contains(text(), '%s')]" % player_name)
            player.click()
        except NoSuchElementException:
            self.driver.close()
            mess2 = f"Пользователь с ником {player_name} не найден!"
            logger.info(mess2)
            msg.about(self, "Внимание!", mess2)
        except NoSuchWindowException:
            logger.warning(f'NoSuchWindowException in search player, {self.browser}')
        except WebDriverException:
            logger.warning(f'WebDriverException in search player, {self.browser}')
        except AttributeError as e:
            self.driver.close()
            logger.warning(f'%s in search player, {self.browser}' % e)
        except Exception as e:
            logger.error(str(e))
            msg.about(self, "Ошибка!", 'Что-то пошло не так...')
        else:
            try:
                number_of_pages = int(self._get_element_list("//div[@id='mtabs-battles']")[0].split()[-1])
                logger.info(f'Player: {player_name}, number of pages: {number_of_pages}, browser: {self.browser}')
                data = self.data_collection(number_of_pages)
                self.driver.close()
                data = ["\n".join(page) for page in data]
                data = "\n".join(data)
                prepared_data = self.data_preparation(data)
                self.db_insert_data(player_name, prepared_data)
            except ValueError:
                self.driver.close()
                logger.info("Нет данных")
                msg.about(self, "Внимание!", "Нет данных!")
            except AttributeError as e:
                self.driver.close()
                logger.warning(f'%s in collection, {self.browser}' % e)
            except NoSuchWindowException:
                logger.warning(f'NoSuchWindowException in collection, {self.browser}')
            except WebDriverException:
                logger.warning(f'WebDriverException in collection, {self.browser}')
            except Exception as e:
                logger.error(str(e))
                msg.about(self, "Ошибка!", 'Что-то пошло не так...')
            else:
                try:
                    self.visualization(prepared_data, player_name)
                except Exception as e:
                    logger.error(str(e))
                    msg.about(self, "Ошибка!", 'Что-то пошло не так...')

    def init_web_driver(self, wait=IMPLICITLY_WAIT) -> bool:
        try:
            logger.debug('Init web driver')
            options = webdriver.ChromeOptions()
            options.add_argument('--no-sandbox')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--headless')
            self.driver = webdriver.Chrome(executable_path=PATH_TO_WEBDRIVER[self.browser],
                                           desired_capabilities=CAPABILITIES[self.browser],
                                           chrome_options=options)
            self.driver.implicitly_wait(wait)
            return True
        except SessionNotCreatedException:
            logging.warning('SessionNotCreatedException in init_web_driver()')
            return False

    def _get_element_list(self, xpath: str):
        return self.driver.find_element(By.XPATH, xpath).text.split('\n')

    def search_player(self, player_name: str):
        logger.debug('Search player')
        element = self.driver.find_element(By.XPATH, "//input[@placeholder='Ник или STEAM_0:X:XXXXXX']")
        element.send_keys(player_name)
        element.send_keys(Keys.ENTER)

    def data_collection(self, number_of_pages: int) -> list:
        logger.debug('Data collection')
        data = []
        for i in range(2, number_of_pages + 1):
            data.append(self._get_element_list("//div[@id='mtabs-battles']")[2:])
            # click next page
            self.driver.find_element(By.XPATH, "//div[@id='mtabs-battles']/a[contains(text(), '%d')]" % i).click()
            # because fastcup raise "HTTP 429 Too Many Requests" :\
            sleep(SLEEP_ON_PAGE[self.browser])
        data.append(self._get_element_list("//div[@id='mtabs-battles']")[2:])
        return data

    def data_preparation(self, data: str) -> [list]:
        """Don't try to understand it, just believe
        """
        logger.debug('Data preparation')
        dt = []
        for line in data.split("\n"):
            if not line:
                continue
            ln = line.split()
            x = ln.index("CS")
            fight = ln[0]
            date, time = self.__get_date_time(ln[1:x])
            year, month, day = date.split('-')
            hour, minutes = time.split(':')
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
                try:
                    k, d = map(int, ln[x+10].split('/'))
                except ValueError:
                    k, d = 0, 0
                try:
                    points = float(ln[x+11])
                except IndexError:
                    points = 0.0
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
            dt.append([fight, date, time, year, month, day, hour, minutes, type_game,
                      xvsx, mp, side, result, k, d, points, sep, exp])
        return dt

    def load_data(self):
        """Load data and visualization
        """
        try:
            logger.debug('Load from database')
            # check existing db
            if not path.exists(DB_NAME):
                self.create_db()
            # init messagebox
            msg = QtWidgets.QMessageBox
            player_name = self.line_edit.text()
            if not player_name:
                msg.about(self, "Внимание!", "<p align='left'>Введите ник игрока!</p>")
                return
            data = self.db_select_data(player_name)
            prepared_data = list(map(lambda x: x[:-1], data))
            if not len(prepared_data):
                msg.about(self, "Внимание!", "<p align='left'>Нет данных!</p>")
                return
            self.visualization(prepared_data, player_name)
        except Exception as e:
            logger.error(str(e))
            msg = QtWidgets.QMessageBox
            msg.about(self, "Ошибка!", 'Что-то пошло не так...')

    def visualization(self, prepared_data, player_name):
        logger.debug('Start visualuzation')
        df = self.create_dataframe(prepared_data)
        df_wins_defeats = df[(df.Результат == "Победа") | (df.Результат == "Поражение")]
        dates = [str(date).split()[0] for date in df_wins_defeats.Дата.sort_values()]
        tabs = []

        player_name = replace_unsupported_chars(player_name)
        file_name = f"Fights_{player_name}.html"
        output_file(file_name, title='FCStats')

        tabs.append(Panel(child=self.build_graph_skill_fights(df_wins_defeats), title='Skill-Fights'))

        p = self.build_hist(df_wins_defeats, 'Карта', 'Map', label_orientation=True)
        if p:
            tabs.append(Panel(child=p, title='Skill-Maps'))

        p = self.build_hist(df_wins_defeats, 'Размер', 'Size')
        if p:
            tabs.append(Panel(child=p, title='Skill-Sizes'))

        p = self.build_hist(df_wins_defeats, 'Сторона', 'Side')
        if p:
            tabs.append(Panel(child=p, title='Skill-Sides'))

        p = self.build_hist(df_wins_defeats, dates, 'Date', visible_xaxis=False, visible_grid=False)
        if p:
            tabs.append(Panel(child=p, title='Skill-Dates'))

        p = self.build_hist(df_wins_defeats, 'Год', 'Year')
        if p:
            tabs.append(Panel(child=p, title='Skill-Years'))

        p = self.build_hist(df_wins_defeats, 'Месяц', 'Month')
        if p:
            tabs.append(Panel(child=p, title='Skill-Months'))

        p = self.build_hist(df_wins_defeats, 'ДеньНедели', 'DayOfWeek')
        if p:
            tabs.append(Panel(child=p, title='Skill-DaysOfWeek'))

        p = self.build_hist(df_wins_defeats, 'Час', 'Hour', visible_grid=False)
        if p:
            tabs.append(Panel(child=p, title='Skill-Hours'))

        p = self.build_categorical_hist(df_wins_defeats, ['Карта', 'Сторона'], 'Map-Side', label_orientation=True)
        if p:
            tabs.append(Panel(child=p, title='Skill-Maps'))

        p = self.heat_map(df_wins_defeats, ['Год', 'Месяц'])
        if p:
            tabs.append(Panel(child=p, title='Years-Month'))

        tabs.append(Panel(child=self.common_table(df), title='Common table'))

        tabs = Tabs(tabs=tabs)
        show(tabs)
        logger.debug('End visualuzation')

    def build_graph_skill_fights(self, df: DataFrame):
        logger.debug('Graph skill-fights')
        y = df.Скилл
        x = range(1, len(y) + 1)
        fights = list(map(lambda x_: x_[1:], df.Игра))
        difference_kd = [k-d for k, d in zip(df.Фраги, df.Смерти)]

        source = ColumnDataSource(data=dict(
            x=x,
            y=y,
            fights=fights,
            kills=df.Фраги,
            deaths=df.Смерти,
            map=df.Карта,
            size=df.Размер,
            difference_kd=difference_kd
        ))

        colors = ['#E60C00', '#E67E00', '#FFCC0F', '#B5EB00', '#78EB00', '#2BEB00']
        color_mapper = LinearColorMapper(palette=colors,
                                         low=min(difference_kd), high=max(difference_kd))

        TOOLTIPS = [
            ('K/D', "@kills/@deaths"),
            ('Skill', '@y{0.0}'),
            ('Map', '@map'),
            ('xVSx', '@size')
        ]
        hover_tools = HoverTool(tooltips=TOOLTIPS, line_policy='nearest', point_policy='snap_to_data')

        # sizing_mode='stretch_both' don't work in tabs :(
        p = figure(title="Click on fights!", x_axis_label='Fight number', y_axis_label='Skill',
                   tools="pan,tap,wheel_zoom,reset", active_drag="pan", width=self.width, height=self.height)

        p.circle('x', 'y', size=8, nonselection_fill_alpha=0.7, fill_alpha=0.7, source=source,
                 legend="Fights", color={'field': 'difference_kd', 'transform': color_mapper},
                 nonselection_color={'field': 'difference_kd', 'transform': color_mapper})
        p.toolbar.active_scroll = p.select_one(WheelZoomTool)
        p.tools.append(hover_tools)

        color_bar = ColorBar(color_mapper=color_mapper, major_label_text_font_size="8pt",
                             ticker=BasicTicker(desired_num_ticks=len(colors)),
                             formatter=PrintfTickFormatter(format='%d k/d difference'),
                             label_standoff=21, border_line_color=None, location=(0, 0))
        p.add_layout(color_bar, 'right')

        url = 'https://old.fastcup.net/fight.html?id=@fights'
        taptool = p.select(type=TapTool)
        taptool.callback = OpenURL(url=url)
        return p

    def build_hist(self, df: DataFrame, group_by_col, name: str, visible_xaxis=True, visible_grid=True, label_orientation=False):
        logger.debug(f'Build hist {name}')
        # prepare data
        df_group = df.groupby(group_by_col).Скилл
        if len(df_group.sum()) <= 1:
            return False
        wins_defeats_count = df.groupby(group_by_col).Результат.value_counts()

        x = list(df_group.sum().index)
        number_of_fights = df_group.count().values
        skill_sum = df_group.sum().values
        kills_sum = df.groupby(group_by_col).Фраги.sum()
        deaths_sum = df.groupby(group_by_col).Смерти.sum()
        wins_count = [wins_defeats_count[i].get('Победа', 0) for i in x]
        defeats_count = [wins_defeats_count[i].get('Поражение', 0) for i in x]

        source = ColumnDataSource(data=dict(
            x=x,
            y=skill_sum,
            number_of_fights=number_of_fights,
            avg_skill=list(map(lambda x, y: x/y, skill_sum, number_of_fights)),
            kills=kills_sum,
            deaths=deaths_sum,
            wins=wins_count,
            defeats=defeats_count
        ))

        colors = ['#deebf7', '#c6dbef', '#9ecae1', '#6baed6', '#4292c6', '#2171b5', '#084594']
        color_mapper = LinearColorMapper(palette=colors,
                                         low=min(number_of_fights), high=max(number_of_fights))

        TOOLTIPS = [
            ('Skill', '@y{0.0}'),
            ('Average skill', '@avg_skill{0.000}'),
            ('Number of fights', '@number_of_fights'),
            (name, '@x'),
            ('K/D', '@kills/@deaths'),
            ('Wins', '@wins'),
            ('Defeats', '@defeats')
        ]

        # sizing_mode='stretch_both' don't work in tabs :(
        p = figure(x_range=x, title="", tooltips=TOOLTIPS, tools="pan,wheel_zoom,reset", width=self.width, height=self.height,
                   y_axis_label='Skill')
        p.vbar(x='x', top='y', width=0.9, source=source, color={'field': 'number_of_fights', 'transform': color_mapper})
        p.toolbar.active_scroll = p.select_one(WheelZoomTool)

        min_skill_sum = min(skill_sum)
        p.y_range.start = min_skill_sum if min_skill_sum < 0 else 0
        if label_orientation:
            p.xaxis.major_label_orientation = 3.14 / 3

        color_bar = ColorBar(color_mapper=color_mapper, major_label_text_font_size="8pt",
                             ticker=BasicTicker(desired_num_ticks=len(colors)),
                             formatter=PrintfTickFormatter(format='%d fights'),
                             label_standoff=13, border_line_color=None, location=(0, 0))
        p.add_layout(color_bar, 'right')

        if not visible_xaxis:
            p.xaxis.major_label_text_font_size = '0pt'

        if not visible_grid:
            p.grid.grid_line_color = None
            p.axis.major_tick_line_color = None

        return p

    def build_categorical_hist(self, df: DataFrame, group_by_col, name: str, visible_xaxis=True,
                               visible_grid=True, label_orientation=False):
        logger.debug('Categorical hist')
        # prepare data
        df_group = df.groupby(group_by_col)
        if len(df_group.sum()) <= 1:
            return False
        wins_defeats_count = df.groupby(group_by_col).Результат.value_counts()
        # sides_count = df.groupby(group_by_col).Сторона.value_counts()

        x = list(df_group.sum().index)
        number_of_fights = df_group.count().reset_index().Скилл.values
        skill_sum = df_group.sum().reset_index().Скилл.values
        kills_sum = df_group.Фраги.sum().reset_index().Фраги.values
        deaths_sum = df_group.Смерти.sum().reset_index().Смерти.values
        wins_count = [wins_defeats_count[i].get('Победа', 0) for i in x]
        defeats_count = [wins_defeats_count[i].get('Поражение', 0) for i in x]

        res_indx_count = df_group.count().reset_index()
        x = [(mp, sd) for mp, sd in zip(res_indx_count.Карта, res_indx_count.Сторона)]

        source = ColumnDataSource(data=dict(
            x=x,
            y=skill_sum,
            avg_skill=list(map(lambda x, y: x/y, skill_sum, number_of_fights)),
            number_of_fights=number_of_fights,
            kills=kills_sum,
            deaths=deaths_sum,
            wins=wins_count,
            defeats=defeats_count
        ))

        colors = ['#deebf7', '#c6dbef', '#9ecae1', '#6baed6', '#4292c6', '#2171b5', '#084594']
        color_mapper = LinearColorMapper(palette=colors,
                                         low=min(number_of_fights), high=max(number_of_fights))

        TOOLTIPS = [
            ('Skill', '@y{0.0}'),
            ('Average skill', '@avg_skill{0.000}'),
            ('Number of fights', '@number_of_fights'),
            (name, '@x'),
            ('K/D', '@kills/@deaths'),
            ('Wins', '@wins'),
            ('Defeats', '@defeats')
        ]

        # sizing_mode='stretch_both' don't work in tabs :(
        p = figure(x_range=FactorRange(*x), title="", tooltips=TOOLTIPS, tools="pan,wheel_zoom,reset", width=self.width, height=self.height,
                   y_axis_label='Skill')
        p.vbar(x='x', top='y', width=0.9, source=source, color={'field': 'number_of_fights', 'transform': color_mapper})
        p.toolbar.active_scroll = p.select_one(WheelZoomTool)

        min_skill_sum = min(skill_sum)
        p.y_range.start = min_skill_sum if min_skill_sum < 0 else 0
        if label_orientation:
            p.xaxis.group_label_orientation = 3.14 / 3

        color_bar = ColorBar(color_mapper=color_mapper, major_label_text_font_size="8pt",
                             ticker=BasicTicker(desired_num_ticks=len(colors)),
                             formatter=PrintfTickFormatter(format='%d fights'),
                             label_standoff=13, border_line_color=None, location=(0, 0))
        p.add_layout(color_bar, 'right')

        if not visible_xaxis:
            p.xaxis.major_label_text_font_size = '0pt'

        if not visible_grid:
            p.grid.grid_line_color = None
            p.axis.major_tick_line_color = None

        return p

    def heat_map(self, df: DataFrame, group_by_col):
        logger.debug('Heat map')
        df_group = df.groupby(group_by_col)
        if len(df_group.sum()) <= 1:
            return False
        wins_defeats_count = df.groupby(group_by_col).Результат.value_counts()

        months = df_group.sum().reset_index().Месяц.values
        years = df_group.sum().reset_index().Год.values
        x = list(df_group.sum().index)
        number_of_fights = df_group.count().Игра.values
        skill_sum = [round(i, 1) for i in df_group.Скилл.sum().values]
        kills_sum = df.groupby(group_by_col).Фраги.sum().values
        deaths_sum = df.groupby(group_by_col).Смерти.sum().values
        wins_count = [wins_defeats_count[i].get('Победа', 0) for i in x]
        defeats_count = [wins_defeats_count[i].get('Поражение', 0) for i in x]

        source = ColumnDataSource(data=dict(
            x=months,
            y=years,
            number_of_fights=number_of_fights,
            avg_skill=list(map(lambda x, y: x/y, skill_sum, number_of_fights)),
            kills=kills_sum,
            deaths=deaths_sum,
            wins=wins_count,
            defeats=defeats_count,
            skill_sum=skill_sum
        ))

        colors = ['#deebf7', '#c6dbef', '#9ecae1', '#6baed6', '#4292c6', '#2171b5', '#084594']
        color_mapper = LinearColorMapper(palette=colors,
                                         low=min(number_of_fights), high=max(number_of_fights))
        colors_skill = ['#000000', '#FFFFFF']
        color_mapper_skill = LinearColorMapper(palette=colors_skill,
                                               low=min(number_of_fights), high=max(number_of_fights))
        colors_wins = ['#002d00', '#00ea00']
        color_mapper_wins = LinearColorMapper(palette=colors_wins,
                                              low=min(number_of_fights), high=max(number_of_fights))
        colors_defeats = ['#380000', '#e30000', '#ff2435']
        color_mapper_defeats = LinearColorMapper(palette=colors_defeats,
                                                 low=min(number_of_fights), high=max(number_of_fights))

        TOOLTIPS = [
            ('Skill', '@skill_sum{0.0}'),
            ('Average skill', '@avg_skill{0.000}'),
            ('Number of fights', '@number_of_fights'),
            ('Year', '@y'),
            ('Month', '@x'),
            ('K/D', '@kills/@deaths'),
            ('Wins', '@wins'),
            ('Defeats', '@defeats')
        ]
        hover_tools = HoverTool(tooltips=TOOLTIPS, line_policy='nearest', point_policy='snap_to_data', names=['rect'])

        p = figure(title="",
                   x_range=['01', '02', '03', '04', '05', '06',
                            '07', '08', '09', '10', '11', '12'],
                   y_range=sorted(set(df.Год)),
                   x_axis_location="above", plot_width=self.width, plot_height=self.height,
                   tools="pan,box_zoom,reset,wheel_zoom")

        p.rect(x="x", y="y", width=1, height=1,
               source=source,
               fill_color={'field': 'number_of_fights', 'transform': color_mapper},
               line_color='#deebf7',
               name='rect')
        p.tools.append(hover_tools)

        text_props = {"source": source, "text_font_size": '8pt', "x_offset": -0.8}

        x = dodge("x", -0.4, range=p.x_range)
        p.text(x=x, y=dodge("y", 0.2, range=p.y_range), text="skill_sum",
               text_color={'field': 'number_of_fights', 'transform': color_mapper_skill}, **text_props)
        p.text(x=x, y=dodge("y", -0.1, range=p.y_range), text="wins",
               text_color={'field': 'number_of_fights', 'transform': color_mapper_wins}, **text_props)
        p.text(x=x, y=dodge("y", -0.25, range=p.y_range), text="defeats",
               text_color={'field': 'number_of_fights', 'transform': color_mapper_defeats}, **text_props)

        p.grid.grid_line_color = None
        p.axis.axis_line_color = None
        p.axis.major_tick_line_color = None
        p.axis.major_label_text_font_size = "8pt"
        p.axis.major_label_standoff = 0
        # p.xaxis.major_label_orientation = pi / 3

        color_bar = ColorBar(color_mapper=color_mapper, major_label_text_font_size="8pt",
                             ticker=BasicTicker(desired_num_ticks=len(colors)),
                             formatter=PrintfTickFormatter(format='%d fights'),
                             label_standoff=13, border_line_color=None, location=(0, 0))
        p.add_layout(color_bar, 'right')

        return p

    @staticmethod
    def common_table(df: DataFrame):
        logger.debug('Common table')
        ddf = df.Игра.groupby(df.Результат).count().to_frame()
        div_skill = df.where(df.Деление != '').dropna()
        div_skill_m = div_skill.where(df.Скилл <= 0).dropna()
        div_skill_p = div_skill.where(df.Скилл > 0).dropna()
        div_skill_m_sum = sum(div_skill_m.Скилл.values) * 3
        div_skill_p_sum = sum(div_skill_p.Скилл.values) * 3

        y = list(ddf.index.values)
        fights_count = list(ddf.Игра.values)
        skill_sum = list(df.Скилл.groupby(df.Результат).sum().values)

        y.extend(['Разделенный скилл -', 'Разделенный скилл +'])
        fights_count.extend([len(div_skill_m), len(div_skill_p)])
        skill_sum.extend([div_skill_m_sum, div_skill_p_sum])

        source = ColumnDataSource(data=dict(
            y=y,
            fights_count=fights_count,
            skill_sum=skill_sum
        ))
        columns = [
            TableColumn(field="y", title="Результат"),
            TableColumn(field="fights_count", title="Количество"),
            TableColumn(field="skill_sum", title="Суммарный скилл", formatter=NumberFormatter(format="0.0"))
        ]

        data_table = DataTable(source=source, columns=columns, width=800)

        return data_table

    @staticmethod
    def create_dataframe(dt: [list]) -> DataFrame:
        labels = ["Игра", "Дата", "Время", "Год", "Месяц", "День", "Час", "Минуты", "Канал", "Размер", "Карта",
                  "Сторона", "Результат", "Фраги", "Смерти", "Скилл", "Деление", "Опыт"]
        df = DataFrame.from_records(dt, columns=labels).iloc[::-1]
        df['Дата'] = df.Дата.astype('datetime64[ns]')
        df['ДеньНедели'] = [str(date.isoweekday()) for date in df.Дата]
        df = df.sort_values('Дата')
        return df

    @staticmethod
    def __get_date_time(lst_dt: [str]) -> (str, str):
        """Processing values like 'Сегодня 17:39', '42 минуты назад' etc.
        """
        month_to_num = dict(января='01', февраля='02', марта='03', апреля='04', мая='05', июня='06',
                            июля='07', августа='08', сентября='09', октября='10', ноября='11', декабря='12')
        days_to_int = dict(Сегодня=0, Вчера=1, Позавчера=2)

        now = datetime.today()
        if len(lst_dt) == 4:
            if lst_dt[2] == 'назад':
                date = now.strftime("%Y-%m-%d")
                time = now.strftime("%H:%M")
                if 'мин' in lst_dt[1]:
                    time = (now - timedelta(minutes=int(lst_dt[0]))).strftime("%H:%M")
            else:
                time = lst_dt[3]
                lst_dt[0] = lst_dt[0].zfill(2)
                lst_dt[1] = month_to_num[lst_dt[1]]
                date = '-'.join(lst_dt[2::-1])
        else:
            time = lst_dt[1]
            date = (now - timedelta(days=days_to_int[lst_dt[0]])).strftime("%Y-%m-%d")
        return date, time


def main():
    try:
        logger.debug('Start program')
        app = QtWidgets.QApplication(sys.argv)
        window = MainWindow()
        window.show()
        app.exec_()
        logger.debug('End program')
    except Exception as e:
        logger.error(str(e))


if __name__ == '__main__':
    main()
