
import matplotlib.pyplot as plt
import numpy as np
from gui.components import Axes
from core import PlotTypes

class Plot:
    def __init__(self, data:list[float], axes:Axes , vwidth, vheight, fwidth, fheight, fps=24,
                scale=1, theme='ggplot'):
        """
        data: list of numpy arrays. Each array should have shape N,2.
        ox, oy: origin of user specified coordinate axes.
        fwidth: Width of video frame.
        fheight: Height of video frame.
        vwidth: Width of videoview frame.
        vheight: Height of videoview frame.
        """
        self._data = data
        self.datanum = len(data)
        self.fps = fps
        self._fwidth = fwidth
        self._fheight = fheight
        self._vwidth = vwidth
        self._vheight = vheight
        self._scale = scale
        self.axes = axes
        
        self.samplecount = 0
        if self.datanum > 0:
            self.samplecount = self._data[0].shape[0]
        self._t = np.linspace(0, self.samplecount/fps, self.samplecount)
        plt.style.use(theme)
        
        # Transform
        self._datatr = []
        for i in range(self.datanum):
            data = self._data[i]
            
            datax, datay = self.transform(data[:,0], data[:,1], axes)
            datatr = np.hstack((datax.reshape(-1,1), datay.reshape(-1,1)))
            
            self._datatr.append(datatr)
            
    def data(self):
        """Returns processed data after transformation"""
        return self._datatr
        
    def transform(self, x, y, axes: Axes):
        """Applies transformation according to videoview, image frame and user specified frame"""
        fvx = self._vwidth/2 - self._fwidth/2
        fvy = self._vheight/2 - self._fheight/2
        ox = self.axes.ox
        oy = self.axes.oy
        
        # In canvas coordinates
        x = x + fvx
        y = y + fvy
        
        x, y = axes.canvas2reg(x, y, ox, oy)
        
        # Inverse rotate points
        theta = -np.deg2rad(self.axes.theta.get())
        x, y = axes.rotatez(x, y, theta)
        
        if self._scale is not None:
            x = x * self._scale
            y = y * self._scale
        
        return x, y
    
    def showplots(self, splots):
        """Displays plot of selected plots stored in splots"""
        for ptype in splots:
            if ptype == PlotTypes.X.name:
                self.plotx()
            elif ptype == PlotTypes.Y.name:
                self.ploty()
            elif ptype == PlotTypes.XY.name:    
                self.plotxy()
            elif ptype == PlotTypes.DX.name:
                self.plotdx()
            elif ptype == PlotTypes.DY.name:
                self.plotdy()
            elif ptype == PlotTypes.D2X.name:
                self.plotd2x()
            elif ptype == PlotTypes.D2Y.name:
                self.plotd2y()
                
        plt.show()
        
    def plotx(self):
        for d in self._datatr:
            plt.figure()
            plt.title(r"$\mathbf{x}$")
            plt.xlabel(r"$\mathbf{t}$")
            plt.ylabel(r"$\mathbf{x}$")
            plt.plot(self._t, d[:, 0], '-m')
            
    def ploty(self):
        for d in self._datatr:
            plt.figure()
            plt.title(r"$\mathbf{y}$")
            plt.xlabel(r"$\mathbf{t}$")
            plt.ylabel(r"$\mathbf{y}$")
            plt.plot(self._t, d[:, 1], '-m')
            
    def plotxy(self):
        for d in self._datatr:
            plt.figure()
            plt.title(r"$\mathbf{x,y}$")
            plt.xlabel(r"$\mathbf{x}$")
            plt.ylabel(r"$\mathbf{y}$")
            plt.plot(d[:,0], d[:, 1], '-c')
            
    def plotdx(self):
        for d in self._datatr:
            dx_dt = np.gradient(d[:,0], self._t).reshape(-1, 1)
            plt.figure()
            plt.title(r"$\mathbf{dx}$")
            plt.xlabel(r"$\mathbf{t}$")
            plt.ylabel(r"$\mathbf{dx}$")
            plt.plot(self._t, dx_dt, '-g')
            
    
    def plotdy(self):
        for d in self._datatr:
            dy_dt = np.gradient(d[:,1], self._t).reshape(-1, 1)
            plt.figure()
            plt.title(r"$\mathbf{dy}$")
            plt.xlabel(r"$\mathbf{t}$")
            plt.ylabel(r"$\mathbf{dy}$")
            plt.plot(self._t, dy_dt, '-g')
            
    def plotd2x(self):
        for d in self._datatr:
            dx_dt = np.gradient(d[:,0], self._t)
            dx2_dt = np.gradient(dx_dt, self._t)
            plt.figure()
            plt.title(r"$\mathbf{d^2x}$")
            plt.xlabel(r"$\mathbf{t}$")
            plt.ylabel(r"$\mathbf{d^2x}$")
            plt.plot(self._t, dx2_dt, '-b')            
    
    def plotd2y(self):
        for d in self._datatr:
            dy_dt = np.gradient(d[:,1], self._t)
            dy2_dt = np.gradient(dy_dt, self._t)
            plt.figure()
            plt.title(r"$\mathbf{d^2y}$")
            plt.xlabel(r"$\mathbf{t}$")
            plt.ylabel(r"$\mathbf{d^2y}$")
            plt.plot(self._t, dy2_dt, '-b')
        
        
    # def intgr(self):
    #     dataintr = []
        
    #     for i in range(self.datanum):
            
    #         x_intg = np.cumsum(self._datatr[i][:,0]).reshape(-1,1) * (self._t[1] - self._t[0])
    #         y_intg = np.cumsum(self._datatr[i][:,1]).reshape(-1,1) * (self._t[1] - self._t[0])
            
    #         dataintr.append(np.hstack((x_intg,y_intg)).reshape(-1, 2))
        
    #     self.plot(dataintr, title="Integral")
    
    # def plotdrv(self):
    #     datadrv = []
        
    #     for i in range(self.datanum):
    #         dx_dt = np.gradient(self._datatr[i][:,0], self._t).reshape(-1, 1)
    #         dy_dt = np.gradient(self._datatr[i][:,1], self._t).reshape(-1, 1)
    #         datadrv.append(np.hstack((dx_dt,dy_dt)).reshape(-1, 2))
        
    #     self.plot(datadrv, title="1st Derivative")
        
    # def plotdrv2(self):
    #     datadrv = []
        
    #     for i in range(self.datanum):
    #         dx_dt = np.gradient(self._datatr[i][:,0], self._t)
    #         dx2_dt = np.gradient(dx_dt, self._t)
            
    #         dy_dt = np.gradient(self._datatr[i][:,1], self._t)
    #         dy2_dt = np.gradient(dy_dt, self._t)
            
    #         datadrv.append(np.vstack((dx2_dt,dy2_dt)).reshape(-1, 2))
        
    #     self.plot(datadrv, title="2nd Derivative")
        
    # def plot(self, trackpts, title="Data"):

    #     _, axes = plt.subplots(self.datanum, 3, figsize=(10, 5), squeeze=False)

    #     for i in range(self.datanum):
    #         trackpt = trackpts[i]
            
    #         xcoords = trackpt[:, 0]
    #         ycoords = trackpt[:, 1]

    #         axes[i][0].plot(self._t, xcoords, '-m')
    #         axes[i][0].set_xlabel(r"$\mathbf{t}$")
    #         axes[i][0].set_ylabel(r"$\mathbf{x}$")
    #         axes[i][0].set_title(title + r" - $\mathbf{x}$")
    #         axes[i][0].set_aspect('equal')
            
    #         axes[i][1].plot(self._t, ycoords, '-g')
    #         axes[i][1].set_xlabel(r"$\mathbf{t}$")
    #         axes[i][1].set_ylabel(r"$\mathbf{y}$")
    #         axes[i][1].set_title(title + r" - $\mathbf{y}$")
    #         axes[i][1].set_aspect('equal')
            
    #         axes[i][2].plot(xcoords, ycoords, '-r')
    #         axes[i][2].set_xlabel(r"$\mathbf{x}$")
    #         axes[i][2].set_ylabel(r"$\mathbf{y}$")
    #         axes[i][2].set_title(title + r" - $\mathbf{x}$ vs $\mathbf{y}$")
    #         axes[i][2].set_aspect('equal')
            
    #     plt.tight_layout()
    #     # plt.show()
        
    # def show(self):
    #     plt.show()
        
        
if __name__ == "__main__":
    data = [np.random.rand(100, 2) * 100]
    plot = Plot(data, 640, 480, 640, 480)
    plot.plotx()
    # plot.plotdrv()
    # plot.plotdrv2()
    plot.intgr()
    plot.show()