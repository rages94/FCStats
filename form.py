# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'form.ui'
#
# Created by: PyQt5 UI code generator 5.12
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_form_fcstats(object):
    def setupUi(self, form_fcstats):
        form_fcstats.setObjectName("form_fcstats")
        form_fcstats.setEnabled(True)
        form_fcstats.resize(350, 130)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(form_fcstats.sizePolicy().hasHeightForWidth())
        form_fcstats.setSizePolicy(sizePolicy)
        form_fcstats.setMinimumSize(QtCore.QSize(350, 130))
        form_fcstats.setMaximumSize(QtCore.QSize(350, 130))
        self.centralwidget = QtWidgets.QWidget(form_fcstats)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayoutWidget = QtWidgets.QWidget(self.centralwidget)
        self.gridLayoutWidget.setGeometry(QtCore.QRect(6, 10, 331, 101))
        self.gridLayoutWidget.setObjectName("gridLayoutWidget")
        self.gridLayout = QtWidgets.QGridLayout(self.gridLayoutWidget)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.button_create_stats = QtWidgets.QPushButton(self.gridLayoutWidget)
        self.button_create_stats.setObjectName("button_create_stats")
        self.gridLayout.addWidget(self.button_create_stats, 3, 1, 1, 1)
        self.line_edit = QtWidgets.QLineEdit(self.gridLayoutWidget)
        self.line_edit.setMaximumSize(QtCore.QSize(200, 20))
        self.line_edit.setObjectName("line_edit")
        self.gridLayout.addWidget(self.line_edit, 3, 0, 1, 1)
        self.checkbox_save_in_file = QtWidgets.QCheckBox(self.gridLayoutWidget)
        self.checkbox_save_in_file.setChecked(False)
        self.checkbox_save_in_file.setObjectName("checkbox_save_in_file")
        self.gridLayout.addWidget(self.checkbox_save_in_file, 2, 0, 1, 1)
        self.button_load_file = QtWidgets.QPushButton(self.gridLayoutWidget)
        self.button_load_file.setObjectName("button_load_file")
        self.gridLayout.addWidget(self.button_load_file, 4, 1, 1, 1)
        self.checkbox_save_stats = QtWidgets.QCheckBox(self.gridLayoutWidget)
        self.checkbox_save_stats.setChecked(True)
        self.checkbox_save_stats.setObjectName("checkbox_save_stats")
        self.gridLayout.addWidget(self.checkbox_save_stats, 2, 1, 1, 1)
        form_fcstats.setCentralWidget(self.centralwidget)
        self.statusbar = QtWidgets.QStatusBar(form_fcstats)
        self.statusbar.setObjectName("statusbar")
        form_fcstats.setStatusBar(self.statusbar)

        self.retranslateUi(form_fcstats)
        QtCore.QMetaObject.connectSlotsByName(form_fcstats)

    def retranslateUi(self, form_fcstats):
        _translate = QtCore.QCoreApplication.translate
        form_fcstats.setWindowTitle(_translate("form_fcstats", "FCStats"))
        self.button_create_stats.setText(_translate("form_fcstats", "Создать"))
        self.line_edit.setPlaceholderText(_translate("form_fcstats", "Ник или STEAM_0:X:XXXXXX"))
        self.checkbox_save_in_file.setText(_translate("form_fcstats", "Сохранить данные"))
        self.button_load_file.setText(_translate("form_fcstats", "Загрузить из файла"))
        self.checkbox_save_stats.setText(_translate("form_fcstats", "Сохранить статистику"))


