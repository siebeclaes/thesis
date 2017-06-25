import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl

def isodistance():
    plt.figure(figsize=(8, 5), dpi=100)
    ax = plt.subplot(111)

    E_ref = 60

    E = np.linspace(0, 100, num=100, endpoint=True)
    isodistance = [0,0.1, 1,2,3,4,5]

    max_y = 0
    for distance in isodistance:
        R = distance * np.tanh(E_ref / E)
        if R.max() > max_y:
            max_y = R.max()

        plt.plot(E, R, label="isodistance " + str(distance))

    ax.yaxis.set_ticks_position('left') # this one is optional but I still recommend it...
    ax.xaxis.set_ticks_position('bottom')

    plt.ylim(0, max_y * 1.1)
    plt.legend()

    plt.show()


def isoreward(presentation=False):
    if presentation:
        plt.figure(figsize=(4,3))
        mpl.rcParams['axes.color_cycle'] = ['#78B833', '#DD7611', '#16A6C9']
        mpl.rcParams['axes.grid'] = False
    else:
        plt.figure(figsize=(6.5, 5))
    # plt.switch_backend('tkagg')
    ax = plt.subplot(111)

    E_ref = 30

    E = np.linspace(0.1, 5, num=100, endpoint=True)
    if presentation:
        isoreward = [1, 3, 5]
    else:
        isoreward = [0.1, 1, 2, 3, 4, 5]

    max_y = 0
    for reward in isoreward:
        R = reward / np.tanh((E_ref/10) / (E)) / 10

        if R.max() > max_y:
            max_y = R.max()

        plt.plot(E, R, label="Score = " + str(reward))

    ax.yaxis.set_ticks_position('left') # this one is optional but I still recommend it...
    ax.xaxis.set_ticks_position('bottom')

    plt.ylim(0, max_y * 1.1)
    plt.xlabel('Power (W)')
    plt.ylabel('Speed (m/s)')
    plt.legend()

    if presentation:
        plt.title("Score function (higher is better)")
        plt.tight_layout()
        plt.savefig('/Users/Siebe/Dropbox/Thesis/presentation_plots/score_function.png', dpi=300)
    else:
        plt.savefig("/Users/Siebe/Dropbox/Thesis/writing/figures/isoreward_eref_30.pgf")
    # plt.show()


isoreward(presentation=True)