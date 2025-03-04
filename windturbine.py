import pandas as pd
import math
import matplotlib.pyplot as plt
import numpy as np
from scipy import interpolate

bn = 3              #Blades number [-]
hubr = 0.01         #Hub radius [m]
blade_min_radius = 0.05        #Blade min working radius [m]
blade_max_radius = 0.20        #Blade max working radius [m] (Rotor radius)
blade_sections_number = 9              #Blade sections [-]
uinf = 6           #Rated wind speed [m/s]
lamb =  6           #Rated lamda [-] (Omega*bmaxr/uinf)
rho=1.225           #Air density [kg/m3]
cilsec = True       #If true output sections are on a cilindrical surface
pivotx = 0          #Pivot point x for airfoil rotation
pivoty = 0          #Pivot point y for airfoil rotation

# Instatntiate plot figure
fig = plt.figure()

# Read airfoil data from CSV
dataS822= pd.read_csv("dataS822.csv",header=0,names=['Re','alpha','cl','cd','eta'],sep=',')

# Data interpolation for calculation
# fcd = interpolate.interp2d(dataS822.Re, dataS822.alpha, dataS822.cd, kind='quintic')
# fcl = interpolate.interp2d(dataS822.Re, dataS822.alpha, dataS822.cl, kind='quintic')
# feta= interpolate.interp2d(dataS822.Re, dataS822.alpha, dataS822.eta, kind='quintic')

# Prepare data for interpolation
points = np.column_stack((dataS822.Re, dataS822.alpha)) # column_stack is used to stack 1-D arrays as columns into a 2-D array for example (a,b,c) and (d,e,f) will be (a,d),(b,e),(c,f)
fcd = interpolate.LinearNDInterpolator(points, dataS822.cd)
fcl = interpolate.LinearNDInterpolator(points, dataS822.cl)
feta = interpolate.LinearNDInterpolator(points, dataS822.eta)

# Create grid for plotting
Regrid = np.arange(50000, 525000, 25000) # Reynolds number grid for interpolation
alphagrid = np.arange(-10, 15, 1) # Angle of attack grid for interpolation

# Create meshgrid
Regrid, alphagrid = np.meshgrid(Regrid, alphagrid) # Create meshgrid for interpolation points

# Interpolate values
cdplot = fcd(Regrid, alphagrid)
clplot = fcl(Regrid, alphagrid)
etaplot = feta(Regrid, alphagrid)

# Plot of airfoil "cd"
ax221 = fig.add_subplot(221, projection='3d')
ax221.scatter(dataS822.Re, dataS822.alpha, dataS822.cd)
ax221.plot_surface(Regrid, alphagrid, cdplot)

# Plot of airfoil "cl"
ax222 = fig.add_subplot(222, projection='3d')
ax222.scatter(dataS822.Re, dataS822.alpha, dataS822.cl)
ax222.plot_surface(Regrid, alphagrid, clplot)

# Plot of airfoil "eta"
ax223 = fig.add_subplot(223, projection='3d')
ax223.scatter(dataS822.Re, dataS822.alpha, dataS822.eta)
ax223.plot_surface(Regrid, alphagrid, etaplot)

# If needed show airfoil plot
#plt.show()

# Rated angular speed calculation
omegar = lamb*uinf/blade_max_radius
print('Turbine rated speed: ' + str(omegar*60/(2*math.pi)))

# This function calculate for every section of the blade some parameters. This function must be called iteratively starting from the result
# of previus call of the same function. The process may converge.
def bladesection(a_arr,a1_arr,c_arr):
    print('{:<10} {:<10} {:<10} {:<10} {:<10} {:<10} {:<10} {:<10} {:<10} {:<10} {:<10} {:<10} {:<10} {:<10}'.format('r', 'w', 'phi', 'Re', 'alpha', 'cd', 'cl', 'chord', 'cx', 'cy', 'newa', 'newa1', 'DeltaCp', 'Twist'))
    print('---------------------------------------------------------------------------------------------------------------------------------------------------------------')
    out_a_arr = np.empty(blade_sections_number)
    out_a1_arr = np.empty(blade_sections_number)
    out_c_arr = np.empty(blade_sections_number)
    out_cp_arr = np.empty(blade_sections_number)
    out_twist_arr = np.empty(blade_sections_number)

    for i in range(blade_sections_number):
        r = sector_radius[i]
        a = a_arr[i] #axial induction factor
        a1 = a1_arr[i] #angular induction factor
        c = c_arr[i] #chord
        w = math.sqrt((uinf*(1-a))**2 + (omegar*r*(1+a1))**2) #relative wind speed
        phi = math.atan((uinf*(1-a))/(omegar*r*(1+a1))) #angle of attack
        re = w*c/1.45e-5 #Reynolds number
        if re < 50000:
            re = 50000
        alphas = np.linspace(-10,14,100) #angle of attack range
        etas = feta(re,alphas) #efficiency
        #plt.plot(alphas,etas)
        #plt.show()
        bestalpha = alphas.item(np.argmax(etas)) #best angle of attack for efficiency 
        cdrags = fcd(re,alphas) #drag coefficient for every angle of attack
        clifts = fcl(re,alphas) #lift coefficient for every angle of attack
        bestcd = cdrags.item(np.argmax(etas)) #drag coefficient for best angle of attack
        bestcl = clifts.item(np.argmax(etas)) #lift coefficient for best angle of attack

        newc = ((8*(2*math.pi*blade_max_radius))/(9*lamb**bestcl*bn))/(math.sqrt((4/9)+((lamb**2)*((r/blade_max_radius)**2)*(1+2/(9*(lamb**2)*((r/blade_max_radius)**2)))**2))) #new chord
        out_c_arr[i]=newc   #save chord value obtained from airfoil series theoric calculation

        cy=bestcl*math.cos(phi)+bestcd*math.sin(phi)    #cy and cx are the lift and drag components of the force
        cx=bestcl*math.sin(phi)-bestcd*math.cos(phi)

        #B=((bn*c)/(2*math.pi*r)*((cy**2)-(((bn*newc)/(2*math.pi*r)*cx**2)/(4*(math.sin(phi))**2))/(4*(math.sin(phi))**2)))
        sigmar = bn*newc/(2*math.pi*r)
        B=(sigmar/(4*(math.sin(phi)**2)))*((cy**2)-((sigmar*(cx**2))/(4*math.sin(phi)**2)))
        newa=B/(B+1)
        out_a_arr[i]=newa
        F=((bn*newc)/(2*math.pi*r)*cx/(4*math.sin(phi)*math.cos(phi)))
        newa1=F/(1-F)
        out_a1_arr[i]=newa1

        deltacp=((4*math.pi*rho*uinf*(omegar**2)*r*newa1*(1-newa)*(r**2)*((blade_max_radius-blade_min_radius)/blade_sections_number))-(0.5*rho*(w**2)*bestcd*math.cos(phi)*newc*bn*omegar*r*((blade_max_radius-blade_min_radius)/blade_sections_number)))/(0.5*rho*math.pi*(blade_max_radius**2)*(uinf**3))
        out_cp_arr[i]=deltacp

        twist_ang = phi-(bestalpha*0.017453)
        out_twist_arr[i] = twist_ang

        print('{:<10.2f} {:<10.2f} {:<10.2f} {:<10.0f} {:<10.2f} {:<10.2f} {:<10.2f} {:<10.3f} {:<10.2f} {:<10.2f} {:<10.2f} {:<10.2f} {:<10.3f} {:<10.3f}'.format(r, w, phi/0.01745, re, bestalpha, bestcd, bestcl, newc, cx, cy, newa, newa1, deltacp, twist_ang/0.017453))
    print()
    results = [out_a_arr,out_a1_arr,out_c_arr,out_cp_arr,out_twist_arr]
    return results

# First attempt values:
cp_0 = 0.44         #First attempt power coefficient
a_0 = 0.333         #First attempt axial induction factor
a1_0 = 0            #First attempt angular induction factor
ci_0 = 0.02         #First attempt airfoil chord

# Fill of first attemp arrays
sector_radius = np.linspace(blade_min_radius,blade_max_radius,blade_sections_number)
a_i=np.empty(blade_sections_number)
a_i.fill(a_0)
a1_i=np.empty(blade_sections_number)
a1_i.fill(a1_0)
ci_i=np.empty(blade_sections_number)
ci_i.fill(ci_0)

#Instead of having a while cycle to convergence there is a for cycle (usually 10 iteration are enought)
for i in range(10):
    results = bladesection(a_i,a1_i,ci_i)
    a_i = results[0]
    a1_i = results[1]
    ci_i = results[2]

# Iteration turbine Cp (sum of section Cp)
print('Turbine Cp: ' + str(sum(results[3])))

# Read of airfoil shape from CSV
shapeS822= pd.read_csv("shapeS822.csv",header=0,names=['x','y'],sep=',')

ax224 = fig.add_subplot(224,projection='3d')

# If needed plot the loaded shape
#ax224.plot(shapeS822.x,shapeS822.y)

# Function that scale, rotate, and project airfoil shape based on a pivot point
# It save 3 series of CSV files, the first series without suffix contains the full shape for every blade section,
# the one with suffix "_A" contains the first half shape of the airfoil for every blade section,
# the one with suffix "_B" contains the other half shape of the airfoil for every blade section
def bladeddraw(c_arr,twist_arr,pivot_x,pivot_y): 
    fig2 = plt.figure()
    fig2.tight_layout()
    ax111 = fig2.add_subplot(111,projection='3d')
    for j in range(blade_sections_number):
        x = (shapeS822.x-pivot_x)*c_arr[j]
        y = (shapeS822.y-pivot_y)*c_arr[j]
        x1 = x*math.cos(twist_arr[j])-y*math.sin(twist_arr[j])
        y1 = y*math.cos(twist_arr[j])+x*math.sin(twist_arr[j])
        #ax224.plot(x1,y1)
        #sigma = (x/secr[j])*2*math.pi
        sigma = np.empty(len(x1))
        x2 = np.empty(len(x1))
        y2 = np.empty(len(x1))
        z2 = np.empty(len(x1))
        for k in range(len(x1)):
            sigma[k] = x1[k]/sector_radius[j]
            if cilsec:
                x2[k] = 100*sector_radius[j]*math.sin(sigma[k])      #100 convert the coordinate in [cm] but importing it in Fusion360
                y2[k] = 100*y1[k]                           #leads to [mm] dimensions!!!!!
                z2[k] = 100*sector_radius[j]*math.cos(sigma[k])
            else:
                x2[k] = 100*x1[k]
                y2[k] = 100*y1[k]
                z2[k] = 100*sector_radius[j]
        ax224.scatter(x2,y2,z2)
        coord =  {  'x': x2,
                    'y': y2,
                    'z': z2
        }
        df = pd.DataFrame(coord, columns= ['x', 'y','z'])
        fn = 'output/coord_{:.2f}'.format(sector_radius[j]) + '.csv'
        df.to_csv (fn, index = False, header=True, float_format='%.3f')
        print (df)

        coord_a =  {'x': x2[0:31],
                    'y': y2[0:31],
                    'z': z2[0:31]
        }
        df = pd.DataFrame(coord_a, columns= ['x', 'y','z'])
        fn = 'output/coord_{:.2f}'.format(sector_radius[j]) + '_A.csv'
        df.to_csv (fn, index = False, header=True, float_format='%.3f')
        print (df)

        coord_b =  {    'x': x2[30:61],
                        'y': y2[30:61],
                        'z': z2[30:61]
        }
        df = pd.DataFrame(coord_b, columns= ['x', 'y','z'])
        fn = 'output/coord_{:.2f}'.format(sector_radius[j]) + '_B.csv'
        df.to_csv (fn, index = False, header=True, float_format='%.3f')
        print (df)
        ax111.scatter(x2,y2,z2)
        ax111.set_xlim3d([-50,50])
        ax111.set_ylim3d([-50,50])
        ax111.set_zlim3d([0,100])

# Call of bladedraw with calculated chords length, angles with a specific pivot point
bladeddraw(ci_i,results[4],pivotx,pivoty)
plt.tight_layout()
# Show the plot with cd, cl, eta and blade subplots
plt.show()