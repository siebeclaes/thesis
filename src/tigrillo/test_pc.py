import time
OFFSETTIME = time.time()

def generateCPG(cpg, delay = 0):
    T = time.time() - OFFSETTIME
    actions = cpg.get_action(T)
    print actions

def loadCpgParamsFromFile(filename):
    import pickle
    with open(filename, 'rb') as f:
        params = pickle.load(f)
        print params
        return loadCpgParams(params)


def loadCpgParams(x):
    from CpgControl import CPGControl

    mu = [x[0], x[1], x[2], x[3]]
    o = [x[4], x[4], x[5], x[5]]
    omega = [x[6], x[6], x[7], x[7]]
    d = [x[8], x[8], x[9], x[9]]
    coupling = [[0, x[10], x[11], x[13]], [x[10], 0, x[12], x[14]], [x[11], x[12], 0, x[15]], [x[13], x[14], x[15], 0]]
    phase_offset = x[16]

    cpg = CPGControl(mu, o, omega, d, coupling, phase_offset)
    return cpg


cpg = loadCpgParamsFromFile('cpg_params.pickle')

while(1):
    generateCPG(cpg)