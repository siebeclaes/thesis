import pickle
import numpy as np
import matplotlib.pyplot as plt
from generate_cpg_control import loadCpgParamsFromFile

cpg_files = ['baseline', 'spring_noise_10', 'spring_noise_20', 'mass_noise_10', 'mass_noise_20', 'friction_noise_10', 'friction_noise_20', 'final_transfer']
gait_names = ['the baseline', '10\% noise on spring stiffness', '20\% noise on spring stiffness', '10\% noise on mass', '20\% noise on mass', '10\% noise on friction', '20\% noise on friction', 'combined noise']

f = open('/Users/Siebe/Dropbox/Thesis/writing/cpg_appendix.tex', 'w')


def write_section(name):
	f.write("\\clearpage\\section{{{}}}\n\n".format(name))

def write_table(params, name):
	amplitude_f = np.sqrt(params[0])
	amplitude_b = np.sqrt(params[2])

	offset_f = params[4]
	offset_b = params[5]

	frequency = params[6] / 2 / np.pi

	duty_f = params[7]
	duty_b = params[8]

	phase_offset = params[10]

	f.write("""
\\begin{{table}}[h]
	\\centering
	\\caption{{CPG parameters for {}}}
	\\label{{my-label}}
	\\begin{{tabular}}{{l|cc}}
		& \\textbf{{Front legs}} & \\textbf{{Hind legs}} \\\\ \\hline
		\\textbf{{Amplitude (degrees)}}    & {:.5f}                  & {:.5f}                 \\\\
		\\textbf{{Offset (degrees)}}       & {:.5f}                   & {:.5f}                 \\\\
		\\textbf{{Frequency (Hz)}}    & {:.5f}                   & {:.5f}                  \\\\
		\\textbf{{Duty factor}}  & {:.5f}                 & {:.5f}                \\\\ \\hline
		\\textbf{{Phase offset (radians)}} & \\multicolumn{{2}}{{c}}{{{:.5f}}}                 
	\\end{{tabular}}
\\end{{table}}\n
		""".format(
			name, amplitude_f, amplitude_b, offset_f, offset_b, frequency, frequency, duty_f, duty_b, phase_offset
			)
		)

def create_plot(cpg_file):
	cpg = loadCpgParamsFromFile('final_cpgs/' + cpg_file + '.pickle')
	front, hind = [], []

	timestep = 0.01 # 10 ms
	duration = 5 # seconds

	# Get actions for 15 seconds
	for time in range(int(duration/timestep)):
		action = cpg.get_action(time*timestep)
		front.append(action[0])
		hind.append(action[2])

	X = np.arange(0, duration, timestep)
	plt.figure(figsize=(6.5,3.5))
	plt.plot(X, front, label='Front')
	plt.plot(X, hind, label='Hind')
	plt.legend()
	plt.xlabel('Time (s)')
	plt.ylabel('CPG output (degrees)')
	plt.tight_layout()

	plt.savefig('/Users/Siebe/Dropbox/Thesis/writing/figures/' + cpg_file + '.pgf')

def write_include_plot(cpg_file, name):
	f.write("""
\\begin{{figure}}[h]
	\\centering
	\\input{{figures/{}.pgf}}
	\\caption{{The output of the front and hind CPGs for {}. Positive values rotate the leg forward.}}
	\\label{{fig:{}}}
\\end{{figure}}
	""".format(cpg_file, name, cpg_file)
	)

for cpg_file, gait_name in zip(cpg_files, gait_names):
	write_section(gait_name)

	with open('final_cpgs/' + cpg_file + '.pickle', 'rb') as f2:
		params = pickle.load(f2)
		write_table(params, gait_name)
		create_plot(cpg_file)
		write_include_plot(cpg_file, gait_name)

f.close()