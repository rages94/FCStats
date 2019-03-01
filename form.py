# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'form.ui'
#
# Created by: PyQt5 UI code generator 5.11.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_StatisticFastcup(object):
    def setupUi(self, FCstats):
        FCstats.setObjectName("FCstats")
        FCstats.setEnabled(True)
        FCstats.resize(300, 100)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(FCstats.sizePolicy().hasHeightForWidth())
        FCstats.setSizePolicy(sizePolicy)
        FCstats.setMinimumSize(QtCore.QSize(300, 100))
        FCstats.setMaximumSize(QtCore.QSize(300, 100))
        self.centralwidget = QtWidgets.QWidget(FCstats)
        self.centralwidget.setObjectName("centralwidget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.lineEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.lineEdit.setObjectName("lineEdit")
        self.horizontalLayout.addWidget(self.lineEdit)
        self.btn_id = QtWidgets.QPushButton(self.centralwidget)
        self.btn_id.setObjectName("btn_id")
        self.horizontalLayout.addWidget(self.btn_id)
        FCstats.setCentralWidget(self.centralwidget)
        self.statusbar = QtWidgets.QStatusBar(FCstats)
        self.statusbar.setObjectName("statusbar")
        FCstats.setStatusBar(self.statusbar)

        self.retranslateUi(FCstats)
        QtCore.QMetaObject.connectSlotsByName(FCstats)

    def retranslateUi(self, FCstats):
        _translate = QtCore.QCoreApplication.translate
        FCstats.setWindowTitle(_translate("FCstats", "FCstats"))
        self.lineEdit.setPlaceholderText(_translate("FCstats", "Ник или STEAM_0:X:XXXXXX"))
        self.btn_id.setText(_translate("FCstats", "Собрать данные"))

