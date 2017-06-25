import numpy as np
import matplotlib.pyplot as plt
import time
import os


def get_cpg_values(mu, offset, omega, d, num_samples=1000):
    r = np.sqrt(mu)
    phi = np.pi * d
    o = offset
    gamma = 0.1
    dt = 0.001

    samples = []

    # startup_samples = 5000

    for sample in range(num_samples):
        for iteration in range(int(0.001 / dt)):
            d_r = gamma * (mu - r * r) * r
            d_phi = omega
            d_o = 0

            r += dt * d_r
            phi += dt * d_phi
            o += dt * d_o

        two_pi = 2 * 3.141592654

        phi_L = 0
        phi_2pi = phi % two_pi
        if phi_2pi < (two_pi * d):
            phi_L = phi_2pi / (2 * d)
        else:
            phi_L = (phi_2pi + two_pi * (1 - 2 * d)) / (2 * (1 - d))

        action = r * np.cos(phi_L) + o
        # if sample >= startup_samples:
        samples.append(action)

    return samples


def main():
    times = np.arange(0, 1, 0.001)
    amplitude = 30**2
    freq = 1
    cpg_values_1 = np.array(get_cpg_values(amplitude, 0, freq * 2 * np.pi, 0.1))
    cpg_values_2 = np.array(get_cpg_values(amplitude, 0, freq * 2 * np.pi, 0.3))
    cpg_values_3 = np.array(get_cpg_values(amplitude, 0, freq * 2 * np.pi, 0.5))
    cpg_values_4 = np.array(get_cpg_values(amplitude, 0, freq * 2 * np.pi, 0.7))
    cpg_values_5 = np.array(get_cpg_values(amplitude, 0, freq * 2 * np.pi, 0.9))

    # row and column sharing
    # f, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, sharex='col', sharey='row')
    # ax1.plot(times, cpg_values_1, color='red', linewidth='1.5')
    #
    # ax1.set_ylim(cpg_values_1.min()*1.1, cpg_values_1.max()*1.1)
    #
    # ax1.set_title('Influence of duty factor on CPG shape')
    # ax2.plot(times, cpg_values_2, color='green', linewidth='1.5')
    # ax3.plot(times, cpg_values_3, color='blue', linewidth='1.5')
    # ax4.plot(times, cpg_values_4, color='orange', linewidth='1.5')

    plt.figure(figsize=(6.5,5))

    ax = plt.gca()

    ax.yaxis.set_ticks_position('left') # this one is optional but I still recommend it...
    ax.xaxis.set_ticks_position('bottom')

    # plt.plot(times, cpg_values_1, color='purple', linewidth='1.5', label='d=0.1')
    # plt.plot(times, cpg_values_2, color='red', linewidth='1.5', label='d=0.3')
    # plt.plot(times, cpg_values_3, color='green', linewidth='1.5', label='d=0.5')
    # plt.plot(times, cpg_values_4, color='blue', linewidth='1.5', label='d=0.7')
    # plt.plot(times, cpg_values_5, color='orange', linewidth='1.5', label='d=0.9')

    plt.plot(times, cpg_values_1, label='d=0.1')
    plt.plot(times, cpg_values_2, label='d=0.3')
    plt.plot(times, cpg_values_3, label='d=0.5')
    plt.plot(times, cpg_values_4, label='d=0.7')
    plt.plot(times, cpg_values_5, label='d=0.9')

    plt.ylim(cpg_values_1.min()*1.1, cpg_values_1.max()*1.1)

    plt.xlabel('Time (s)')
    plt.ylabel('Motor position (degrees)')

    plt.legend(loc='upper left', frameon=False)

    plt.savefig('/Users/Siebe/Dropbox/Thesis/writing/figures/cpg_duty_factor.pgf')
    # plt.show()


if __name__ == '__main__':
    main()
