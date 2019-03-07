import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

def limit_thrust(thrust_cmd, min_thrust, max_thrust):
    thrust = np.clip(thrust_cmd,-max_thrust,max_thrust)
    return thrust

def kill_engine(thrust_cmd,  kill_component):
    eps = 1e-8
    thrust_cmd[kill_component] /= 2
    thrust_mag  = np.linalg.norm(thrust_cmd)
    thrust_dvec = thrust_cmd / (thrust_mag + eps)
    thrust = thrust_mag * thrust_dvec
    return thrust

def kill_engine2(thrust_cmd,  kill_component):
    eps = 1e-8
    thrust_cmd[kill_component] /= 2
    thrust_cmd[2] /= 1.5
    thrust_mag  = np.linalg.norm(thrust_cmd)
    thrust_dvec = thrust_cmd / (thrust_mag + eps)
    thrust = thrust_mag * thrust_dvec
    return thrust


def get_glideslope(pos,vel):

    """
        Only impose constraint if: 
            above the ground
            magnitude of velocity > 1m/s

        2nd condition is to avoid noise violating the constraint when lander is
        close to making a landing

    """


    if len(vel.shape) == 1:
        dz = vel[2]
        dy = vel[1]
        dx = vel[0]
    else:
        dz = vel[:,2]
        dy = vel[:,1]
        dx = vel[:,0]

    gs = np.abs(dz) / np.sqrt(dx**2+dy**2)

    if pos[2] > 0.1 :#and np.linalg.norm(vel) > 1.0: 
        return gs
    else:
        return 100.0


def check_model_accuracy(agent, episodes, steps, print_skip=5):
    agent.model.logged_pred_errors = {}
    agent.model.logged_vpred_errors = {}
    agent.model.count = 0
    agent.model.print_skip = print_skip

    trajectories = []
    for i in range(episodes):
        traj = agent.run_episode()
        trajectories.append(traj)
    keys = trajectories[0].keys()
    agent.add_disc_sum_rew(trajectories, agent.gamma1, agent.gamma2)
    rollouts = {}
    for k in keys:
        rollouts[k] = np.concatenate([t[k] for t in trajectories])

    key = "padded_"
    unscaled_obs = rollouts[key + 'observes']
    unscaled_act = rollouts[key + 'actions']
    unscaled_nobs = rollouts[key + 'nobserves']

    states =        rollouts[key + 'model_states']
    errors =        rollouts[key + 'model_errors']
    masks =         rollouts[key + 'masks']
    flags =         rollouts[key + 'flags']
    sdr =           rollouts[key + 'disc_sum_rew']

    targets = agent.model.nobs_scaler.apply(unscaled_nobs)

    agent.model.test_lt(unscaled_obs, unscaled_act,  unscaled_nobs, states, errors, masks, flags, targets, sdr,  steps)


def calc_sdr(agent, traj):
    if agent.gamma1 < 0.999:  # don't scale for gamma ~= 1
        rewards1 = traj['rewards1'] * (1 - agent.gamma1)
    else:
        rewards1 = traj['rewards1'] * (1-0.999)

    if agent.gamma2 < 0.999:  # don't scale for gamma ~= 1
        rewards2 = traj['rewards2'] * (1 - agent.gamma2)
    else:
        rewards2 = traj['rewards2'] * (1-0.999)

    sdr1 = agent.discount(rewards1, agent.gamma1)
    sdr2 = agent.discount(rewards2, agent.gamma2)
    sdr = sdr1 + sdr2
    return sdr, sdr1, sdr2
 
def plot_episode_predictions(agent,  target_key, predict_key, size,  vpred_key='model_vpreds', labnum=0, linewidth=0.2, show_data=False, zero_model_errors=False, use_model=False, fontsize=8):
    fig1 = plt.figure(labnum,figsize=plt.figaspect(0.5))
    fig1.clear()
    plt.figure(fig1.number)
    fig1.set_size_inches(8, 2, forward=True)
    gridspec.GridSpec(1,3)
    agent.arch.zero_model_errors = zero_model_errors
    agent.arch.use_model = use_model
    print(agent.arch.zero_model_errors, agent.arch.use_model)
    traj = agent.run_episode()
    pred = traj[predict_key]
    targ = traj[target_key]

    sdr,sdr1,sdr2 = calc_sdr(agent,traj)
     
    t = np.linspace(0,pred.shape[0],pred.shape[0])

    plt.subplot2grid( (1,3) , (0,0) )
    plt.plot(t, targ[:,0:size//2], 'r',label='Actual',linewidth=linewidth)
    plt.plot(t, pred[:,0:size//2], 'b',label='Predict',linewidth=linewidth)
    plt.gca().set_xlabel("Step",fontsize=fontsize)
    plt.gca().set_ylabel("Position",fontsize=fontsize)
    plt.gca().tick_params(axis='x', labelsize=fontsize)
    plt.gca().tick_params(axis='y', labelsize=fontsize)
    plt.grid()
    plt.legend(bbox_to_anchor=(0., 1.00, 1., .102), loc=3,
            ncol=2,  borderaxespad=0., prop={'size': fontsize})

    plt.subplot2grid( (1,3) , (0,1) )

    plt.plot(t, targ[:,size//2:size], 'r',label='Actual',linewidth=linewidth)
    plt.plot(t, pred[:,size//2:size], 'b',label='Predict',linewidth=linewidth)
    plt.gca().set_xlabel("Step",fontsize=fontsize)
    plt.gca().set_ylabel("Velocity",fontsize=fontsize)
    plt.gca().tick_params(axis='x', labelsize=fontsize)
    plt.gca().tick_params(axis='y', labelsize=fontsize)
    plt.grid()
    plt.legend(bbox_to_anchor=(0., 1.00, 1., .102), loc=3,
            ncol=2,  borderaxespad=0., prop={'size': fontsize})

    plt.subplot2grid( (1,3) , (0,2) )

    plt.plot(t, sdr, 'r',label='Actual',linewidth=linewidth)
    plt.plot(t, traj[vpred_key], 'b',label='Predict',linewidth=linewidth)
    plt.gca().set_xlabel("Step",fontsize=fontsize)
    plt.gca().set_ylabel("Value",fontsize=fontsize)
    plt.gca().tick_params(axis='x', labelsize=fontsize)
    plt.gca().tick_params(axis='y', labelsize=fontsize)
    plt.grid()
    plt.legend(bbox_to_anchor=(0., 1.00, 1., .102), loc=3,
            ncol=2,  borderaxespad=0., prop={'size': fontsize})

    plt.tight_layout(h_pad=3.0)
    fig1.canvas.draw()


    if show_data:
        print('Step | Ground Truth | Predict\n')
        f = '{:6.0f}'
        targ = traj[target_key]
        pred = traj[predict_key]
        for i in range(targ.shape[0]):
            s = 'i=%4d' %(i)
            s +=  print_vector(' |',targ[i],f)
            s +=  print_vector(' |',pred[i],f)
            print(s)
        print('\nStep | Error\n')
        for i in range(targ.shape[0]):
            s = 'i=%4d' %(i)
            s +=  print_vector(' |',pred[i]-targ[i],f)
            print(s)
    return traj

def get_vc(r_tm, v_tm):
   vc = -r_tm.dot(v_tm)/np.linalg.norm(r_tm)
   return vc

def get_zem(r_tm, v_tm):
    vc = get_vc(r_tm, v_tm)
    range = np.linalg.norm(r_tm)
    if True: #vc > 0.1:
        t_go = get_tgo(r_tm, v_tm, 4.0)
        zem = t_go * v_tm + r_tm
        zem = r_tm - t_go * v_tm
        #print('zem: ',zem, r_tm, t_go, v_tm)
    else:
        zem = np.zeros(3)
    return zem
 
def get_dlos(r_tm, v_tm ):
    vc = get_vc(r_tm, v_tm) 
    #dlos       =  r_tm * vc / np.linalg.norm(r_tm) ** 2
    r = np.linalg.norm(r_tm)
    if vc > 0.01:
        dlos = v_tm / r + r_tm * vc / r**2
    else:  
        dlos = np.zeros(3)
    return dlos

def get_tgo( rg, vg, g):
        gamma = 0.0
        p = [gamma + np.linalg.norm(g)**2/2  ,  0., -2. * np.dot(vg,vg)  , -12. * np.dot(vg,rg) , -18. * np.dot(rg , rg)]
        #print(rg, vg, p)
        p_roots = np.roots(p)
        for i in range(len(p_roots)):
            if np.abs(np.imag(p_roots[i])) < 0.0001:
                if p_roots[i] > 0:
                    t_go = np.real(p_roots[i])
        #print(t_go)
        if t_go < 0.:
            t_go = 0.

        return t_go 
 
def print_vector(s,v,f):
    v = 1.0 * v
    if isinstance(v,float): 
         v = [v]
    s1 = ''.join(f.format(v) for k,v in enumerate(v))
    s1 = s + s1
    return s1


def rk4(t, x, xdot, h ):

    """
        t  :  time
        x  :  initial state
        xdot: a function xdot=f(t,x, ...)
        h  : step size

    """

    k1 = h * xdot(t,x)
    k2 = h * xdot(t+h/2 , x + k1/2)
    k3 = h * xdot(t+h/2,  x + k2/2)
    k4 = h * xdot(t+h   ,  x +  k3)

    x = x + (k1 + 2*k2 + 2*k3 + k4) / 6

    return x


def render_traj(traj, vf=None, scaler=None, fontsize=12):

    fig1 = plt.figure(1,figsize=plt.figaspect(0.5))
    fig1.clear()
    plt.figure(fig1.number)
    fig1.set_size_inches(8, 8, forward=True)
    gridspec.GridSpec(3,2)
    t = np.asarray(traj['t'])
    pos = np.asarray(traj['position'])
    vel = np.asarray(traj['velocity'])
    norm_pos = np.linalg.norm(pos,axis=1)
    norm_vel = np.linalg.norm(vel,axis=1)

    x = pos[:,0]
    y = pos[:,1]
    z = pos[:,2]
    plt.subplot2grid( (4,2) , (0,0) )
    plt.plot(t,x,'r',label='X')
    plt.plot(t,y,'b',label='Y')
    plt.plot(t,z,'g',label='Z')
    plt.plot(t,norm_pos,'k',label='N')
    plt.legend(bbox_to_anchor=(0., 0.92, 1., .102), loc=3,
            ncol=5, mode="expand", borderaxespad=0., prop={'size': fontsize})
    plt.gca().set_ylabel('Position (m)',fontsize=fontsize)
    plt.gca().set_xlabel("Time (s)",fontsize=fontsize)
    plt.gca().tick_params(axis='x', labelsize=fontsize)
    plt.gca().tick_params(axis='y', labelsize=fontsize)

    plt.grid(True)
    vc = np.asarray(traj['vc'])
    vc = np.asarray(traj['glideslope']) 
    t1 = t[0:-1]
    plt.subplot2grid( (4,2) , (3,1) )
    colors = ['r']
    #print('debug: ',attitude.shape[1],len(colors))
    plt.plot(t1,vc,colors[0],label='glideslope' )
    plt.legend(bbox_to_anchor=(0., 0.98, 1., .102), loc=3,
            ncol=5, mode="expand", borderaxespad=0., prop={'size': fontsize})
    plt.gca().set_ylabel('Glideslope',fontsize=fontsize)
    plt.gca().set_xlabel("Time (s),fontsize=fontsize")
    plt.gca().tick_params(axis='x', labelsize=fontsize)
    plt.gca().tick_params(axis='y', labelsize=fontsize)

    plt.grid(True)


    dist = np.asarray(traj['disturbance'])
    xd = dist[:,0]
    yd = dist[:,1]
    zd = dist[:,2]

    plt.subplot2grid( (4,2) , (1,1) )
    plt.plot(t,xd,'r',label='X')
    plt.plot(t,yd,'b',label='Y')
    plt.plot(t,zd,'g',label='Z')
    plt.legend(bbox_to_anchor=(0., 1.00, 1., .102), loc=3,
            ncol=5, mode="expand", borderaxespad=0., prop={'size': fontsize})
    plt.gca().set_ylabel("Disturbance  (N)",fontsize=fontsize)
    plt.gca().set_xlabel('Time (s)',fontsize=fontsize)
    plt.gca().tick_params(axis='x', labelsize=fontsize)
    plt.gca().tick_params(axis='y', labelsize=fontsize)

    #plt.xlim(1500,0)
    plt.ylim(-2,2)
    plt.grid(True)


    r = np.asarray(traj['reward'])
    cr = np.cumsum(r)
    plt.subplot2grid( (4,2) , (2,1) )
    #print(r.shape, t1.shape)
    t1 = t[0:r.shape[0]]
    plt.plot(t1,r,'b',label='Reward')
    plt.plot(t1,cr,'g',label='Cum Reward')
    plt.legend(bbox_to_anchor=(0., 1.00, 1., .102), loc=3,
            ncol=5, mode="expand", borderaxespad=0., prop={'size': fontsize})
    plt.gca().set_xlabel("Time (s)",fontsize=fontsize)
    plt.gca().set_ylabel('Reward')
    plt.gca().tick_params(axis='x', labelsize=fontsize)
    plt.gca().tick_params(axis='y', labelsize=fontsize)

    plt.grid(True)

    x = vel[:,0]
    y = vel[:,1]
    z = vel[:,2]

    plt.subplot2grid( (4,2) , (0,1))
    plt.plot(t,x,'r',label='X')
    plt.plot(t,y,'b',label='Y')
    plt.plot(t,z,'g',label='Z')
    plt.plot(t,norm_vel,'k',label='N')
    plt.legend(bbox_to_anchor=(0., 0.92, 1., .102), loc=3,
            ncol=5, mode="expand", borderaxespad=0., prop={'size': fontsize})
    plt.gca().set_ylabel('Velocity (m/s)',fontsize=fontsize)
    plt.gca().tick_params(axis='x', labelsize=fontsize)
    plt.gca().tick_params(axis='y', labelsize=fontsize)

    plt.gca().set_xlabel("Time (s)",fontsize=fontsize)
    plt.grid(True)


    thrust = np.asarray(traj['thrust'])
    x = thrust[:,0]
    y = thrust[:,1]
    z = thrust[:,2]

    plt.subplot2grid( (4,2) , (1,0) )
    plt.plot(t,x,'r',label='X')
    plt.plot(t,y,'b',label='Y')
    plt.plot(t,z,'g',label='Z')

    plt.legend(bbox_to_anchor=(0., 1.00, 1., .102), loc=3,
            ncol=5, mode="expand", borderaxespad=0., prop={'size': fontsize})
    plt.gca().set_ylabel('Thrust  (N)',fontsize=fontsize)
    plt.gca().tick_params(axis='x', labelsize=fontsize)
    plt.gca().tick_params(axis='y', labelsize=fontsize)

    plt.gca().set_xlabel("Time (s)",fontsize=fontsize)
    plt.grid(True)

    if len(traj['value']) > 1 :
        value = np.asarray(traj['value'])
    else:
        value = np.zeros_like(t)
   
    plt.subplot2grid( (4,2) , (3,0) )
    plt.plot(t,value,'r',label='vpred')

    plt.legend(bbox_to_anchor=(0., 1.00, 1., .102), loc=3,
            ncol=5, mode="expand", borderaxespad=0., prop={'size': fontsize})
    plt.gca().set_ylabel('vpred',fontsize=fontsize)
    plt.gca().set_xlabel("Time (s)",fontsize=fontsize)
    plt.gca().tick_params(axis='x', labelsize=fontsize)
    plt.gca().tick_params(axis='y', labelsize=fontsize)

    plt.grid(True)

    m = np.asarray(traj['fuel'])
    plt.subplot2grid( (4,2) , (2,0) )
    plt.plot(t,m,'r',label='Fuel')

    plt.legend(bbox_to_anchor=(0., 1.00, 1., .102), loc=3,
            ncol=5, mode="expand", borderaxespad=0., prop={'size': fontsize})
    plt.gca().set_ylabel('Fuel (kg)',fontsize=fontsize)
    plt.gca().set_xlabel("Time (s)",fontsize=fontsize)
    plt.gca().tick_params(axis='x', labelsize=fontsize)
    plt.gca().tick_params(axis='y', labelsize=fontsize)

    plt.grid(True)

    


    plt.tight_layout(h_pad=3.0)
    fig1.canvas.draw()

def ortho_proj(V,p,d):
    # vertices, position, dvec
    Q=V-p
    qdot = Q.dot(d)
    proj = (qdot * np.expand_dims(d, axis=1)).T
    oproj = Q-proj
    return oproj

def closest_vertex(V,p,d):
    op = ortho_proj(V,p,d)
    dist = np.linalg.norm(ortho_proj(V,p,d),axis=1)
    idx = np.argmin(dist)
    return V[idx]

def plot_rf_vf(history, fignum=0, fontsize=8):
    fig1 = plt.figure(fignum,figsize=plt.figaspect(0.5))
    fig1.clear()
    plt.figure(fig1.number)
    fig1.set_size_inches(8, 2, forward=True)
    gridspec.GridSpec(1,2)
    plt.subplot2grid( (1,2) , (0,0) )

    ep = history['Episode']

    plt.plot(ep,history['Norm_rf'],'r',label='Mean_rf (m)')
    plt.plot(ep,history['SD_rf'], 'b',linestyle=':',label='SD_rf (m)')
    plt.plot(ep,history['Max_rf'], 'g',linestyle=':',label='Max_rf (m)')
    plt.grid(True)

    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
       ncol=5, mode="expand", borderaxespad=0., prop={'size': fontsize})
    ax = plt.gca()
    ax.set_xlabel("Episode", fontsize=8)
    plt.gca().tick_params(axis='x', labelsize=fontsize)
    plt.gca().tick_params(axis='y', labelsize=fontsize)

    plt.subplot2grid( (1,2) , (0,1) )

    plt.plot(ep,history['Norm_vf'],'r',label='Mean_vf (m)')
    plt.plot(ep,history['SD_vf'], 'b',linestyle=':',label='SD_vf (m)')
    plt.plot(ep,history['Max_vf'], 'g',linestyle=':',label='Max_vf (m)')

    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=5, mode="expand", borderaxespad=0., prop={'size': fontsize})
    ax = plt.gca()
    ax.set_xlabel("Episode", fontsize=8)
    plt.gca().tick_params(axis='x', labelsize=fontsize)
    plt.gca().tick_params(axis='y', labelsize=fontsize)

    plt.grid(True)
    plt.tight_layout()
    plt.gcf().subplots_adjust(top=0.85)
    fig1.canvas.draw()


import matplotlib as mpl
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
from matplotlib import cm

def plot_trajectories(trajectory_list, linewidth=0.1, 
                      min_axislimit=(-1200.,-1200.,-600.), max_axislimit=(1200,1200,1200),
                      r_ast=250., target_loc=np.asarray([0.,0.,250.])):
    plt.clf()
    fig = plt.figure(11)
    ax = fig.gca(projection='3d')
    pi = np.pi
    phi, theta = np.mgrid[0.0:pi:100j, 0.0:2.0*pi:100j]

        
    x = r_ast*np.sin(phi)*np.cos(theta)
    y = r_ast*np.sin(phi)*np.sin(theta)
    z = r_ast*np.cos(phi)

            
    ax.plot_surface( x,y,z,  linewidth=0, antialiased=False, shade=True, color='gray')
    rf_list = []
    vf_list = []
    ff_list = []
    for i in range(len(trajectory_list)):
        plot_traj( ax, trajectory_list[i],target_loc, linewidth=linewidth)
        rf_list.append(trajectory_list[i]['norm_rf'][-1])
        vf_list.append(trajectory_list[i]['norm_vf'][-1] * 100.)
        #print('foo: ', trajectory_list[i]['norm_vf'][-1])
        ff_list.append(trajectory_list[i]['fuel'][-1])
    #print(np.asarray(vf_list))
    ax.legend
    fig.canvas.draw()
    plt.show()

    ax.set_xlim3d(min_axislimit[0], max_axislimit[0])
    ax.set_ylim3d(min_axislimit[1], max_axislimit[1])
    ax.set_zlim3d(min_axislimit[2], max_axislimit[2])

    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_zlabel('Z (m)')

    l0 = '                 mean     std' + '\n'
    l1 = '%-20s%6.2f%6.2f' % ('Norm r_f (m):', np.mean(rf_list), np.std(rf_list)) + '\n'
    l2 = '%-20s%6.2f%6.2f' % ('Norm v_f (cm/s):',np.mean(vf_list), np.std(vf_list)) + '\n'
    l3 = '%-20s%6.2f%6.2f' % ('fuel (kg):', np.mean(ff_list), np.std(ff_list))  
    s = l0 + l1 + l2 + l3
    print(s)
    #plt.figtext(0.3,0.3, s , style='normal')
    #bbox={'facecolor':'red', 'alpha':0.5, 'pad':10})

def plot_traj( ax, trajectory, target_loc, linewidth=0.1):
    pos = np.asarray(trajectory['position'])
    pos += target_loc
    ax.plot(pos[:,0],pos[:,1],pos[:,2],linewidth=linewidth)
    