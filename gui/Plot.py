
import matplotlib.pyplot as plt
import numpy as np

class Plot:
    def __init__(self, data:list[float], vwidth, vheight, fwidth, fheight, ox=0, oy=0, fps=24,
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
        self._datanum = len(data)
        self._fps = 24
        self._fwidth = fwidth
        self._fheight = fheight
        self._ox = ox
        self._oy = oy
        self._vwidth = vwidth
        self._vheight = vheight
        self._scale = scale
        
        samplecount = self._data[0].shape[0]
        self._t = np.linspace(0, samplecount/fps, samplecount)
        plt.style.use(theme)
        
        # Transform
        self._datatr = []
        for i in range(self._datanum):
            data = self._data[i]
            
            datax, datay = self.transform(data[:,0], data[:,1])
            datatr = np.hstack((datax.reshape(-1,1), datay.reshape(-1,1)))
            self._datatr.append(datatr)
        
    def transform(self, x, y):
        """Applies transformation according to videoview, image frame and user specified frame"""
        fvx = self._vwidth/2 - self._fwidth/2
        fvy = self._vheight/2 - self._fheight/2
        
        # Invert y coordinates
        y = self._fheight - y
        self._oy = self._vheight - self._oy
        
        # Transform
        x = x - (self._ox - fvx)
        y = y - (self._oy - fvy)
        
        if self._scale is not None:
            x = x * self._scale
            y = y * self._scale
        
        return x, y
        
    def plotx(self):
        self.plot(self._datatr, title="Data")
        
    def plotdrv(self):
        datadrv = []
        
        for i in range(self._datanum):
            dx_dt = np.gradient(self._datatr[i][:,0], self._t)
            dy_dt = np.gradient(self._datatr[i][:,1], self._t)
            datadrv.append(np.vstack((dx_dt,dy_dt)).reshape(-1, 2))
        
        self.plot(datadrv, title="1st Derivative")
        
    def plotdrv2(self):
        datadrv = []
        
        for i in range(self._datanum):
            dx_dt = np.gradient(self._datatr[i][:,0], self._t)
            dx2_dt = np.gradient(dx_dt, self._t)
            
            dy_dt = np.gradient(self._datatr[i][:,1], self._t)
            dy2_dt = np.gradient(dy_dt, self._t)
            
            datadrv.append(np.vstack((dx2_dt,dy2_dt)).reshape(-1, 2))
        
        self.plot(datadrv, title="2nd Derivative")
        
    def plot(self, trackpts, title="Data"):

        _, axes = plt.subplots(self._datanum, 3, figsize=(10, 5), squeeze=False)

        for i in range(self._datanum):
            trackpt = trackpts[i]
            
            xcoords = trackpt[:, 0]
            ycoords = trackpt[:, 1]

            # title = r"$\mathbf{T_" + str(i+1) + r"}$"
            axes[i][0].plot(self._t, xcoords, '-m')
            axes[i][0].set_xlabel(r"$\mathbf{t}$")
            axes[i][0].set_ylabel(r"$\mathbf{x}$")
            axes[i][0].set_title(title + r" - $\mathbf{x}$")
            # axes[i][0].set_aspect('equal')
            
            axes[i][1].plot(self._t, ycoords, '-g')
            axes[i][1].set_xlabel(r"$\mathbf{t}$")
            axes[i][1].set_ylabel(r"$\mathbf{y}$")
            axes[i][1].set_title(title + r" - $\mathbf{y}$")
            # axes[i][1].set_aspect('equal')
            
            axes[i][2].plot(xcoords, ycoords, '-r')
            axes[i][2].set_xlabel(r"$\mathbf{x}$")
            axes[i][2].set_ylabel(r"$\mathbf{y}$")
            axes[i][2].set_title(title + r" - $\mathbf{x}$ vs $\mathbf{y}$")
            # axes[i][2].set_aspect('equal')
            
        plt.tight_layout()
        # plt.show()
        
    def show(self):
        plt.show()
        
        
if __name__ == "__main__":
    plot = Plot([np.random.rand(100, 2) * 100], 640, 480, 640, 480)
    plot.plotx()
    plot.plotdrv()
    plot.plotdrv2()
    plot.show()