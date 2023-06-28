import pyqtgraph as pg
import collections
from pyqtgraph.Qt import QtGui, QtCore
from threading import Thread
import sys
import serial
import numpy as np
import struct
import keyboard

Number = input()

class Graph:
    def __init__(self, parent):
        self.numberofTags = 6
        self.count = 0
        self.maxLen = 3000
        self.db = {}
        self.tagCounter = 0
        self.ch = 11
        self.set_num = 10
        self.running = True
        self.app = parent
        self.win = pg.GraphicsWindow(title="EMG and Angle Data")
        self.privdat = None
        self.dat = []
        for i in range(self.ch):
            self.dat.append(collections.deque([0] * self.maxLen, maxlen=self.maxLen))
        self.plotHandler = None
        self.curveHandler = [None for i in range(self.ch)]
        self.colorList = ["#803723", "#1ff2ed", "#00fa5c", "#aff0ed", "#f1af00", "#803723", "#803723", "#1ff2ed", "#00fa5c", "#aff0ed", "#f1af00"]
        self.title = ["새끼폄근", "집게폄근", "엄지폄근", "손가락 폄근", "엄지 굽힘근", "손가락 굽힘근", "엄지각도", "검지각도", "중지각도", "약지각도", "새끼각도"]

        self.port = 'COM7'
        self.baud = 2000000
        self.start = 0x0b
        self.end = 0x0c

        self.ser = serial.Serial(self.port, self.baud)
        self.ser.set_buffer_size(rx_size=16384, tx_size=16384)
        self.ser.flush()

        self.indexStep = 5000
        self.indexLimit = self.indexStep
        self.i = 0
        self.w = np.zeros((10))
        self.p = 0
        self.readingIndex = self.i
        self.showingLength = 3000

        self.samplingTime = 5000000
        self.emgData = np.zeros((self.indexStep, self.ch), dtype=float)
        self.targetPacketBytes = self.ch * 2 * 50
        self.inWaitingBuffer = []

        self.initPlotHandler()

        self.graphUpdateSpeedMs = 50
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(self.graphUpdateSpeedMs)

    def initPlotHandler(self):
        for i in range(self.ch):
            if i <= 5:
                self.plotHandler = self.win.addPlot(title=self.title[i], row=i, col=0)
                self.plotHandler.setYRange(-5, 5)
            else:
                self.plotHandler = self.win.addPlot(title=self.title[i], row=i - 6, col=1)
                self.plotHandler.setYRange(1, 4)

            color = self.colorList[i]

            if i >= 6:
                self.curveHandler[i] = self.plotHandler.plot(pen=pg.mkPen(color))
            else:
                self.curveHandler[i] = self.plotHandler.plot(pen=pg.mkPen(color))

    def update(self):
        if self.readingIndex > 0:
            for i in range(self.ch):
                self.curveHandler[i].setData(self.emgData[self.readingIndex - self.showingLength:self.readingIndex, i])

    def backgroundThread(self):
        while self.running:
            if keyboard.is_pressed('2'):
                for i in range(10):
                    print('%d번 째 데이터를 띄우는 중' % int(i + 1))
                    self.readingIndex = int(self.w[i]) + 8000
                    self.showingLength = 8000
                    if i == 9:
                        print('끝내시려면 2를 누르세요')
                    keyboard.wait('2')
                    if i == 9:
                        self.timer.stop()
                        self.sendData(self.end)
                        self.ser.close()
                        self.running = False
                        break
                break

            if self.i >= self.indexLimit:
                self.indexLimit += self.indexStep
                self.emgData = np.vstack((self.emgData, np.zeros((self.indexStep, self.ch))))

            if self.ser.in_waiting >= self.targetPacketBytes:
                readData = self.ser.read(self.targetPacketBytes)
                for _t in range(50):
                    for _Ch in range(self.ch):
                        self.emgData[self.i + _t, _Ch] = (struct.unpack(">h", readData[int(_t * self.ch + _Ch) * 2:int(_t * self.ch + _Ch) * 2 + 2])[0]) / 32768 * 5
                self.i = self.i + 50
                self.readingIndex = self.i

    def sendData(self, x):
        self.ser.write(struct.pack("<h", x))

    def main(self):
        print("main start")
        self.sendData(self.start)
        self.backgroundThread()
        self.emgData = self.emgData[:self.i, :]
        for _i in range(self.set_num):
            np.save('%s_%d' % (Number, _i + 1), self.emgData[int(self.w[_i]):int(self.w[_i]) + 8000, :])
        print("main out")

    def timing(self):
        for _i in range(self.set_num):
            keyboard.wait('1')
            print("No.%d Flag on" % int(_i + 1))
            self.w[self.p] = self.i
            self.p = self.p + 1
        print("Final Flag")


if __name__ == '__main__':
    try:
        a = QtGui.QApplication(sys.argv)
        wObj = Graph(a)
        wObj.win.activateWindow()

        T1 = Thread(target=wObj.main)
        T2 = Thread(target=wObj.timing)

        print('Start')
        T2.start()
        T1.start()
    except Exception as e:
        print(e)
