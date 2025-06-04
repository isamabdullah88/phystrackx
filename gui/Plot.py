
import matplotlib.pyplot as plt
import numpy as np

class Plot:
    def __init__(self, data:list[float], fps=24, theme='ggplot'):
        # data: list of numpy arrays. Each array should have shape N,2
        self._data = data
        self._datanum = len(data)
        self._fps = 24
        
        samplecount = self._data[0].shape[0]
        self._t = np.linspace(0, samplecount/fps, samplecount)
        plt.style.use(theme)
        
    def plotx(self):
        self.plot(self._data, title="Data")
        
    def plotdrv(self):        
        datadrv = []
        
        for i in range(self._datanum):
            dx = np.gradient(np.squeeze(self._data[i][:,0])).reshape(-1, 1)
            dy = np.gradient(np.squeeze(self._data[i][:,1])).reshape(-1, 1)
            datadrv.append(np.hstack((dx,dy)))
        
        self.plot(datadrv, title="Derivative")
        
    def plot(self, trackpts, title="Data"):
        numt = len(trackpts)
        _, axes = plt.subplots(numt, 3, figsize=(12, 8))

        for i in range(numt):
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