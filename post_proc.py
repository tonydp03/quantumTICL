###############################################################
###############################################################
### **** POST-PROCESSING FUNCTIONS FOR TRACKSTER MERGE **** ###
###############################################################
###############################################################


import numpy as np
import pandas as pd
import math

from plot_utils import *
import matplotlib.pyplot as plt
from grover_func import *
from copy import deepcopy
# from tqdm import tqdm
import warnings
import itertools
import argparse

#'x', 'y', 'z', 'layer', 'energy', 'LCID', 'TrkId'

def trkIsValid(lcInTrackster, energyThrs, energyThrsCumulative, pThrs):
    lcEnergy = [[lc_energy[4] for lc_energy in lc] for lc in lcInTrackster]
    energyIndices = [[i for i in range(len(energies))] for energies in lcEnergy]

    allPaths = list(itertools.product(*energyIndices))
    lcXYZ = [[lcInfo[:3] for lcInfo in lc] for lc in lcInTrackster]

    totEnDiff = []
    totPVal = []
    for path in allPaths:
        enDiff = 0
        points = [lcXYZ[i][k] for i,k in enumerate(path)]
        energies = [lcEnergy[i][k] for i,k in enumerate(path)]
        pval = pval_fit(points, energies)
        if(pval > pThrs):
            pval = float('inf')
            # pval = 1
        for i,k in enumerate(path):
            if(i>0):
                enContr = np.abs((lcEnergy[i][k] - curr)/(lcEnergy[i][k] + curr))
                if(enContr < energyThrs):
                    enDiff += enContr
                else:
                    enDiff += float('inf')
            curr = lcEnergy[i][k]
        if(enDiff > energyThrsCumulative*len(energies)): # we multiply the energyThrsCumulative by the number of LCs
            totEnDiff.append(float('inf'))
        else:
            totEnDiff.append(enDiff/len(path))
        totPVal.append(pval)
    
    totDiff = [np.sqrt(totEnDiff[i] * totPVal[i]) for i in range(len(allPaths))]
    minTotDiff = np.min(totDiff)
    argMinTotDiff = np.where(totDiff == minTotDiff)[0][0]
    minIndices = allPaths[argMinTotDiff] 

    if(np.isinf(minTotDiff)):
        return []
    else:
        return [lcInTrackster[i][minIndices[i]] for i in range(len(minIndices))]


def closestDistanceBetweenLines(line1, line2, clampAll=False,clampA0=False,clampA1=False,clampB0=False,clampB1=False):

    ''' Given two lines defined by numpy.array pairs (a0,a1,b0,b1)
        Return the closest points on each segment and their distances XY and Z
    '''

    a0 = line1[0]
    a1 = line1[1]
    b0 = line2[0]
    b1 = line2[1]

    # If clampAll=True, set all clamps to True
    if clampAll:
        clampA0=True
        clampA1=True
        clampB0=True
        clampB1=True


    # Calculate denominator
    A = a1 - a0
    B = b1 - b0
    magA = np.linalg.norm(A)
    magB = np.linalg.norm(B)

    _A = A / magA
    _B = B / magB
    
    cross = np.cross(_A, _B)
    denom = np.linalg.norm(cross)**2
    
    
    # If lines are parallel (denom=0) test if lines overlap.
    # If they don't overlap then there is a closest point solution.
    # If they do overlap, there are infinite closest positions, but there is a closest distance
    if not denom:
        d0 = np.dot(_A,(b0-a0))
        
        # Overlap only possible with clamping
        if clampA0 or clampA1 or clampB0 or clampB1:
            d1 = np.dot(_A,(b1-a0))
            
            # Is segment B before A?
            if d0 <= 0 >= d1:
                if clampA0 and clampB1:
                    if np.absolute(d0) < np.absolute(d1):
                    #     return a0,b0,np.linalg.norm(a0-b0), 0.0
                        distXY = np.sqrt((a0[0]-b0[0])**2 + (a0[1]-b0[1])**2)
                        distZ = np.abs(a0[2]-b0[2])
                        return a0,b0,distXY,distZ                
                    # return a0,b1,np.linalg.norm(a0-b1)
                    distXY = np.sqrt((a0[0]-b1[0])**2 + (a0[1]-b1[1])**2)
                    distZ = np.abs(a0[2]-b1[2])
                    return a0,b1,distXY,distZ                
                
            # Is segment B after A?
            elif d0 >= magA <= d1:
                if clampA1 and clampB0:
                    if np.absolute(d0) < np.absolute(d1):
                    #     return a1,b0,np.linalg.norm(a1-b0)
                        distXY = np.sqrt((a1[0]-b0[0])**2 + (a1[1]-b0[1])**2)
                        distZ = np.abs(a1[2]-b0[2])
                        return a0,b0,distXY,distZ                
                    # return a1,b1,np.linalg.norm(a1-b1)
                    distXY = np.sqrt((a1[0]-b1[0])**2 + (a1[1]-b1[1])**2)
                    distZ = np.abs(a1[2]-b1[2])
                    return a1,b1,distXY,distZ                
                
                
        # Segments overlap, return distance between parallel segments
        # return None,None,np.linalg.norm(((d0*_A)+a0)-b0)
        distXY = np.linalg.norm(((d0*_A)+a0)-b0)
        distZ = 0.0
        return None,None,distXY,distZ
        
    
    
    # Lines criss-cross: Calculate the projected closest points
    t = (b0 - a0)
    detA = np.linalg.det([t, _B, cross])
    detB = np.linalg.det([t, _A, cross])

    t0 = detA/denom
    t1 = detB/denom

    pA = a0 + (_A * t0) # Projected closest point on segment A
    pB = b0 + (_B * t1) # Projected closest point on segment B


    # Clamp projections
    if clampA0 or clampA1 or clampB0 or clampB1:
        if clampA0 and t0 < 0:
            pA = a0
        elif clampA1 and t0 > magA:
            pA = a1
        
        if clampB0 and t1 < 0:
            pB = b0
        elif clampB1 and t1 > magB:
            pB = b1
            
        # Clamp projection A
        if (clampA0 and t0 < 0) or (clampA1 and t0 > magA):
            dot = np.dot(_B,(pA-b0))
            if clampB0 and dot < 0:
                dot = 0
            elif clampB1 and dot > magB:
                dot = magB
            pB = b0 + (_B * dot)
    
        # Clamp projection B
        if (clampB0 and t1 < 0) or (clampB1 and t1 > magB):
            dot = np.dot(_A,(pB-a0))
            if clampA0 and dot < 0:
                dot = 0
            elif clampA1 and dot > magA:
                dot = magA
            pA = a0 + (_A * dot)

    distXY = np.sqrt((pA[0]-pB[0])**2 + (pA[1]-pB[1])**2)
    distZ = np.abs(pA[2]-pB[2])
    # return pA,pB,np.linalg.norm(pA-pB)
    return pA,pB,distXY,distZ

def lcLocalDensity(dataset, lc_id):
    layer = dataset[dataset['LCID']==lc_id]['layer'].values
    layer = layer[0]
    layer_enFlow = [layer-2, layer-1, layer+1, layer+2]
    energyFlow = dataset[dataset['layer'].isin(layer_enFlow)]['energy'].values

    return np.mean(energyFlow)

def findDuplicates(dataset, lc_id):
    dup = dataset[dataset['LCID']==lc_id]
    if(len(dup)==0):
        return list(), list()
    elif(len(dup)==1):
        return dup['TrkId'].values, list()
    else:
        trk_ids = dup['TrkId'].values
        trks = deepcopy(dataset[dataset['TrkId'].isin(trk_ids)])
        return trk_ids, trks

def findNeighbors(dataset, cubes_indices):
    l = [tuple(i) for i in cubes_indices]
    trk_ids = np.unique(dataset[dataset[['i','j','k']].apply(tuple, axis = 1).isin(l)]['TrkId'].values)
    
    dup = deepcopy(dataset[dataset['TrkId'].isin(trk_ids)])
    return dup

def compatAndFit(dataset, trk_id1, trk_id2, dist, ang, pThrs, energyThrs, energyThrsCumulative, zTolerance):
    trk1 = dataset[dataset['TrkId']==trk_id1]
    trk2 = dataset[dataset['TrkId']==trk_id2]

    distXY = dist[0]
    distZ = dist[1]

    lcs1_XYZ = trk1.loc[:,['x', 'y', 'z']].to_numpy() 
    lcs1_en = trk1.loc[:,'energy'].to_numpy()
    lcs2_XYZ = trk2.loc[:,['x', 'y', 'z']].to_numpy()
    lcs2_en = trk2.loc[:,'energy'].to_numpy()

    if(len(lcs1_en)<=2 or len(lcs2_en)<=2):
        print('****** :', trk1)
        print('****** :', trk2)

    linepts1, eigenvector1 = line_fit(lcs1_XYZ, lcs1_en)
    linepts2, eigenvector2 = line_fit(lcs2_XYZ, lcs2_en)

    prod = np.dot(eigenvector1, eigenvector2)
    if (prod > 1):
        prod = 1.
    alignment = np.arccos(prod)
    # if(alignment < 1.e-7):
    _, _, distanceXY, distanceZ = closestDistanceBetweenLines(linepts1, linepts2, clampAll=True)
    # else:
    #     _, _, distanceXY, distanceZ = closestDistanceBetweenLines(linepts1, linepts2, clampAll=False)

    if (alignment > ang or distanceXY > distXY or distanceZ > distZ):
        return False
    else:
        lcsTot = np.concatenate((lcs1_XYZ, lcs2_XYZ))
        _, idx = np.unique(lcsTot, axis=0, return_index=True)
        lcsTot = lcsTot[np.sort(idx)]
        lcsTotEn = np.concatenate((lcs1_en, lcs2_en))
        # _, idxEn = np.unique(lcsTotEn, axis=0, return_index=True)
        #  lcsTotEn = lcsTotEn[np.sort(idxEn)]
        lcsTotEn = lcsTotEn[np.sort(idx)]


        ######## find energy-weighed mean point for each layer (points weighed with their energies)
        ######## before calling pval_fit

        # calculate pval
        pval = pval_fit(lcsTot, lcsTotEn)
        if(pval > pThrs):
            return False
        else:
            ###### Sort energies in Z, sum energies of LCs on the same layer/zvalue and apply
            ###### energy difference criteria
            enDiff = 0
            allZ = lcsTot[:,2]
            indices = np.argsort(allZ,)
            sorted_AllZ = np.flip(allZ[indices[::-1]]).tolist()
            # print(sorted_AllZ)
            sorted_En = np.flip(lcsTotEn[indices[::-1]]).tolist()
            i = 0
            while(i<len(sorted_AllZ) - 1):
                if(np.abs(sorted_AllZ[i]-sorted_AllZ[i+1])<zTolerance):
                    sorted_AllZ.pop(i+1)
                    sorted_En[i] += sorted_En[i+1]
                    sorted_En.pop(i+1)
                else:
                    i += 1

            for i in range(len(sorted_En)):
                if(i>0):
                    enContr = np.abs((sorted_En[i] - curr)/(sorted_En[i] + curr))
                    if(enContr < energyThrs):
                        enDiff += enContr
                    else:
                        return False
                curr = sorted_En[i]
            if(enDiff > energyThrsCumulative*len(sorted_En)): # we multiply the energyThrsCumulative by the number of LCs
                return False            
    return True


def mergedTrkIsValid(dataset, trkId, energyThrs, energyThrsCumulative, pThrs, zTolerance):

    trk = dataset[dataset['TrkId']==trkId].sort_values(by=['layer'])

    layerIds = np.unique(trk['layer'].values)
    if(len(layerIds) <= 2):
        return False

    lcs_XYZ = trk.loc[:,['x', 'y', 'z']].to_numpy() 
    lcs_en = trk.loc[:,'energy'].to_numpy()

    # calculate pval
    pval = pval_fit(lcs_XYZ, lcs_en)
    if(pval > pThrs):
        return False
    else:
        ###### Sort energies in Z, sum energies of LCs on the same layer/zvalue and apply
        ###### energy difference criteria
        enDiff = 0
        allZ = lcs_XYZ[:,2]
        indices = np.argsort(allZ,)
        sorted_AllZ = np.flip(allZ[indices[::-1]]).tolist()
        sorted_En = np.flip(lcs_en[indices[::-1]]).tolist()
        i = 0
        while(i<len(sorted_AllZ) - 1):
            if(np.abs(sorted_AllZ[i]-sorted_AllZ[i+1])<zTolerance):
                sorted_AllZ.pop(i+1)
                sorted_En[i] += sorted_En[i+1]
                sorted_En.pop(i+1)
            else:
                i += 1

        for i in range(len(sorted_En)):
            if(i>0):
                enContr = np.abs((sorted_En[i] - curr)/(sorted_En[i] + curr))
                if(enContr < energyThrs):
                    enDiff += enContr
                else:
                    return False
            curr = sorted_En[i]
        if(enDiff > energyThrsCumulative*len(sorted_En)): # we multiply the energyThrsCumulative by the number of LCs
            return False            
    return True

def mergeTrkDup(dataset, dist, ang, pThrs, energyThrs, energyThrsCumulative, zTolerance):
    lc_ids = np.unique(dataset['LCID'].values)
    # pbar = tqdm(total=len(lc_ids))
    for i in lc_ids:
        dupsId, dupsTrk = findDuplicates(dataset, i)
        old_dupsId = dupsId
        if(len(dupsId)>1):
            energiesTrk = [np.sum(dupsTrk[dupsTrk['TrkId']==j]['energy'].values) for j in dupsId]
            energiesTrk_idx = np.argsort(energiesTrk)[::-1] #order of the indices of the energies from highest to lowest
            keep_merging = True
            en_index = 0
            while keep_merging:
                indices = np.delete(energiesTrk_idx, en_index)
                for j in indices:
                    trk_merge = compatAndFit(dupsTrk, dupsId[energiesTrk_idx[en_index]], dupsId[j], dist, ang, pThrs, energyThrs, energyThrsCumulative, zTolerance)
                    if(trk_merge):
                        ##### merge tracksters (modify dupsId and dupsTrk) and redefine energiesTrk_idx and energiesTrk
                        dupsTrk.loc[dupsTrk.TrkId==dupsId[j], 'TrkId'] = dupsId[energiesTrk_idx[en_index]] # change the id of the other trackster with the id of the most energetic 
                        dupsTrk = dupsTrk.drop_duplicates(subset = ['LCID', 'TrkId']) # remove duplicate (LC) rows  
                        dupsId = np.delete(dupsId, j) #--> remove the index from the list of the indices 

                        # redefine these
                        energiesTrk = [np.sum(dupsTrk[dupsTrk['TrkId']==j]['energy'].values) for j in dupsId]
                        energiesTrk_idx = np.argsort(energiesTrk)[::-1] #order of the indices of the energies from highest to lowest
                        en_index = 0
                        break
                    else:
                        en_index += 1
                if(en_index==(len(energiesTrk_idx)-1) or len(indices)==0):
                    keep_merging = False

            
            # If some Tracksters were not merged, assign energy fraction to duplicate LC with index i
            dupLC = dupsTrk[dupsTrk['LCID']==i]
            enDupLC = dupLC['energy'].values
            totEnergyDensity = 0
            for id in dupsId:
                density = lcLocalDensity(dupsTrk[dupsTrk['TrkId']==id], i)
                totEnergyDensity += density
                dupsTrk.loc[(dupsTrk.LCID==i) & (dupsTrk.TrkId==id), 'energy'] = enDupLC[0] * density

            dupsTrk.loc[dupsTrk.LCID==i, 'energy'] /= totEnergyDensity # here 'normalize' the energy

            existsInvalid = True
            while existsInvalid:
                invalidTrks = list()
                for trkId in dupsId:
                    if(not mergedTrkIsValid(dupsTrk, trkId, energyThrs, energyThrsCumulative, pThrs, zTolerance)):
                        invalidTrks.append(trkId)
                        if(len(dupsId) == 1):
                            dupsTrk = list()
                            existsInvalid = False
                if(len(invalidTrks)==0 or len(dupsTrk)==0 or not existsInvalid):
                    existsInvalid = False
                    break
                else:
                ###### if exist invalid tracksters, remove common LC from least energetic and recompute energy of the other trackster
                ###### if LC in common is not in invalid trackster anymore, remove the trackster, else do the instructions below
                    leastEnIndex = energiesTrk_idx[-1]
                    leastTrkId = dupsId[leastEnIndex]
                    dupsId = np.delete(dupsId, leastEnIndex)
                       
                    dupsTrk = dupsTrk.drop(dupsTrk[(dupsTrk['TrkId']==leastTrkId) & (dupsTrk['LCID']==i)].index, axis=0)

                    # check that the trackster without the LC in common is still valid
                    if(not mergedTrkIsValid(dupsTrk, leastTrkId, energyThrs, energyThrsCumulative, pThrs, zTolerance)):
                        dupsTrk = dupsTrk.drop(dupsTrk[(dupsTrk['TrkId']==leastTrkId)].index, axis=0)

                    totEnergyDensity = 0
                    for id in dupsId:
                        density = lcLocalDensity(dupsTrk[dupsTrk['TrkId']==id], i)
                        totEnergyDensity += density
                        dupsTrk.loc[(dupsTrk.LCID==i) & (dupsTrk.TrkId==id), 'energy'] = enDupLC[0] * density

                    dupsTrk.loc[dupsTrk.LCID==i, 'energy'] /= totEnergyDensity # here 'normalize' the energy
                    energiesTrk = [np.sum(dupsTrk[dupsTrk['TrkId']==j]['energy'].values) for j in dupsId]
                    energiesTrk_idx = np.argsort(energiesTrk)[::-1] #order of the indices of the energies from highest to lowest

            #### Update dataset with dupsTrk (removing the older tracksters using old_dupsId)
            dataset = dataset.drop(dataset[(dataset['TrkId'].isin(old_dupsId))].index, axis=0)
            if(len(dupsTrk) != 0):
                dataset_toMerge = [dataset, dupsTrk]
                dataset = pd.concat(dataset_toMerge, ignore_index=True)


            if (np.abs(np.sum(dataset[dataset['LCID']==i]['energy'].values) - enDupLC[0]) > 1.e-10 and len(dupsTrk) != 0):
                print('******* ERRORE! DUPLICATES PRESENT! *******')
                sys.exit()

        # pbar.update(1)

    # pbar.close()
    return dataset

def mergeTrkAll(dataset, dist, ang, pThrs, energyThrs, energyThrsCumulative, zTolerance):

    neighbour_radius = 1

    all_merge = True
    en_idx = 0

    while(all_merge):
        merged = False

        trk_ids = np.unique(dataset['TrkId'].values)
        energiesTrk = [np.sum(dataset[dataset['TrkId']==j]['energy'].values) for j in trk_ids]
        energiesTrk_idx = np.argsort(energiesTrk)[::-1] #order of the indices of the energies from highest to lowest
        trk_toMergeIdx = trk_ids[energiesTrk_idx[en_idx]]
        trk_toMerge = dataset[dataset['TrkId']==trk_toMergeIdx]
        all_cube_indices = trk_toMerge.drop_duplicates(subset = ['i', 'j', 'k'])[['i', 'j', 'k']].values # remove duplicate (i,j,k) rows  
        neighbour_cubes = list()
        for triplet in all_cube_indices:
            all_i = np.arange((triplet[0]-neighbour_radius),triplet[0]+neighbour_radius+1)
            all_j = np.arange((triplet[1]-neighbour_radius),triplet[1]+neighbour_radius+1)
            all_k = np.arange((triplet[2]-neighbour_radius),triplet[2]+neighbour_radius+1)
            neighbour_cubes += list(itertools.product(*[all_i, all_j, all_k]))

        neighbour_cubes = np.unique(neighbour_cubes, axis = 0)
        neighbour_Trks = findNeighbors(dataset, neighbour_cubes)

        neighbour_TrksIdx = np.unique(neighbour_Trks['TrkId'].values)
        old_TrksIdx = neighbour_TrksIdx

        if(len(neighbour_TrksIdx)>1):
            energiesNeighbourTrk = [np.sum(neighbour_Trks[neighbour_Trks['TrkId']==j]['energy'].values) for j in neighbour_TrksIdx]
            energiesNeighbourTrk_idx = np.argsort(energiesNeighbourTrk)[::-1] #order of the indices of the energies from highest to lowest

            keep_merging = True
            en_index = 0
            while keep_merging:
                indices = np.delete(energiesNeighbourTrk_idx, en_index)
                for j in indices:
                    trk_merge = compatAndFit(neighbour_Trks, neighbour_TrksIdx[energiesNeighbourTrk_idx[en_index]], neighbour_TrksIdx[j], dist, ang, pThrs, energyThrs, energyThrsCumulative, zTolerance)
                    if(trk_merge):
                        ##### merge tracksters (modify neighbour_TrksIdx and neighbour_Trks) and redefine energiesNeighbourTrk_idx and energiesNeighbourTrk
                        neighbour_Trks.loc[neighbour_Trks.TrkId==neighbour_TrksIdx[j], 'TrkId'] = neighbour_TrksIdx[energiesNeighbourTrk_idx[en_index]] # change the id of the other trackster with the id of the most energetic 
                        neighbour_TrksIdx = np.delete(neighbour_TrksIdx, j) #--> remove the index from the list of the indices 

                        # redefine these
                        energiesNeighbourTrk = [np.sum(neighbour_Trks[neighbour_Trks['TrkId']==j]['energy'].values) for j in neighbour_TrksIdx]
                        energiesNeighbourTrk_idx = np.argsort(energiesNeighbourTrk)[::-1] #order of the indices of the energies from highest to lowest
                        en_index = 0
                        # It might happen that the new merged trackster is more energetic that the previous most energetic one
                        # For better efficiency, rather than setting en_idx to 0 again we could check the energy and compare with most energetic trackster
                        en_idx = 0
                        merged = True 
                        break
                    else:
                        en_index += 1
                if(en_index==(len(energiesNeighbourTrk_idx)-1) or len(indices)==1):
                    keep_merging = False
                    # print('********* Stop merging ********* ')
   
            #### Update dataset with neighbour_Trks (removing the older tracksters using old_dupsId)
            dataset = dataset.drop(dataset[(dataset['TrkId'].isin(old_TrksIdx))].index, axis=0)
            dataset_toMerge = [dataset, neighbour_Trks]
            dataset = pd.concat(dataset_toMerge, ignore_index=True)
        
        if(not merged):
            en_idx += 1
            if(en_idx==len(energiesTrk_idx)):
                all_merge = False
                print('********* Done merging ********* ')

        # pbar.update(1)
    # pbar.close()
    return dataset


if __name__=='__main__':

    # warnings.filterwarnings("ignore")
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir', type=str, default='./')
    parser.add_argument('--grid', type=float, default='2.5')
    parser.add_argument('--en', type=float, default='0.7')
    parser.add_argument('--encum', type=float, default='0.6')
    parser.add_argument('--pval', type=float, default='0.99')

    args = parser.parse_args()

    myDir = args.dir
    dist = [7.5, 5] # XY and Z
    ang = np.pi/3 #np.pi/4
    pThreshold = 0.99 
    enThreshold = 0.9
    enThresholdCumulative = 0.8
    zTolerance = 0.5
    overlap = [2,2,2]

    # dataset = pd.read_csv(myDir + "Tracksters_gTh" + str(args.grid) + "_pTh"  + str(args.pval) + "_en" + str(args.en) + "_encm" + str(args.encum) + "_overlap" + str(overlap[0]) + str(overlap[1]) + str(overlap[2]) +".csv")
    dataset = pd.read_csv(myDir + "long_Tracksters_gTh" + str(args.grid) + "_pTh"  + str(args.pval) + "_en" + str(args.en) + "_encm" + str(args.encum) + "_overlap" + str(overlap[0]) + str(overlap[1]) + str(overlap[2]) +".csv")
    
    pThreshold = 0.99
    dataset = mergeTrkDup(dataset, dist, ang, pThreshold, enThreshold, enThresholdCumulative, zTolerance)
    print('\n\n\n***** DUPLICATI TUTT APPOST *****\n\n\n')

    dataset = mergeTrkAll(dataset, dist, ang, pThreshold, enThreshold, enThresholdCumulative, zTolerance)
    print('***** ALL TUTT APPOST *****')

    fig = plt.figure(figsize = (30,25))
    trk_id =  np.unique(dataset['TrkId'].values)
    xs = list()
    ys = list()
    zs = list()
    ranges = list()

    for id in trk_id:
        x_lcs = dataset[dataset['TrkId'] == id]['x'].values
        y_lcs = dataset[dataset['TrkId'] == id]['y'].values
        z_lcs = dataset[dataset['TrkId'] == id]['z'].values
        
        xs.append(x_lcs)
        ys.append(y_lcs)
        zs.append(z_lcs)
        
        if(id == trk_id[0]):            
            ranges = [[np.min(x_lcs), np.max(x_lcs)], [np.min(y_lcs), np.max(y_lcs)], [np.min(z_lcs), np.max(z_lcs)]]
        else:
            if(np.min(x_lcs)<ranges[0][0]):
                ranges[0][0] = np.min(x_lcs)
            if(np.max(x_lcs)>ranges[0][1]):
                ranges[0][1] = np.max(x_lcs)
            if(np.min(y_lcs)<ranges[1][0]):
                ranges[1][0] = np.min(y_lcs)
            if(np.max(y_lcs)>ranges[1][1]):
                ranges[1][1] = np.max(y_lcs)
            if(np.min(z_lcs)<ranges[2][0]):
                ranges[2][0] = np.min(z_lcs)
            if(np.max(z_lcs)>ranges[2][1]):
                ranges[2][1] = np.max(z_lcs)

    plots3DwithProjection(fig, xs, ys, zs, ranges)
    # plt.savefig(myDir + "MergedTracksters_gTh" + str(args.grid) + "_pTh"  + str(args.pval) + "_en" + str(args.en) + "_encm" + str(args.encum) + "_overlap" + str(overlap[0]) + str(overlap[1]) + str(overlap[2]) +".png")
    plt.savefig(myDir + "long_MergedTracksters_gTh" + str(args.grid) + "_pTh"  + str(args.pval) + "_en" + str(args.en) + "_encm" + str(args.encum) + "_overlap" + str(overlap[0]) + str(overlap[1]) + str(overlap[2]) +".png")
