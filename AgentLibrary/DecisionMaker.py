import json
import math
import datetime
import time
from shapely.geometry import Polygon
from shapely.validation import make_valid
import numpy as np
import traceback
import warnings
from scipy.optimize import OptimizeWarning
import sys
import os
import random

sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../')

from Library.StateAggregator import *
from Library.ConfigurationFactory import *
from Library.localDB import *
from AgentLibrary.Actuator import *
from Library.Environment import *
from scipy.spatial import ConvexHull
from scipy.optimize import curve_fit

warnings.simplefilter("error", OptimizeWarning)

def generalTwoDegreePlate(xy, a, b, c, d, e, f):
    x, y = xy
    return a + b*x + c*y + d*x**2 + e*y**2 + f*x*y

def simplePlate(xy, a, b, c):
    x, y = xy
    return c + a*x + b*y
    
class DecisionMaker:

    def fix_geom(self, in_feature: Polygon):

        return in_feature.buffer(0)

        if not in_feature['geometry'].is_valid:
            fix = make_valid(in_feature['geometry'])
            # HOW TO CONVERT BaseGeometry to Polygon
            try:
                in_feature =  fix # issue with Poly > Multipolygon
            except ValueError:
                in_feature = in_feature.buffer(0)
        return in_feature

    def layDown(self, points, plate):
        result = []
        minx = 1000000000
        miny = 1000000000
        for obj in points:
            if minx > obj[0]:
                minx = obj[0]
            if miny > obj[1]:
                miny = obj[1]
        for obj in points:
            on_plate_corresponding_point = simplePlate((obj[0], obj[1]), *plate)
            distance = abs(plate[0]*obj[0] + plate[1]*obj[1] - obj[2] + plate[2])/((plate[0]**2+plate[1]**2+1)**0.5) 
            if on_plate_corresponding_point < obj[2]:
                result.append([obj[0] - minx, obj[1] - miny, distance])
            else:
                result.append([obj[0] - minx, obj[1] - miny, -1*distance])
        return result

    def fetchState(self):

        # TODO: Final Target Reach Distance is 1 and near it no close rule should be met
        # TODO: Number of slow nodes and the percent of them has affect on decision

        time.sleep(self.config.get("warmupDuration"))

        lastDecision = ''
        eachDegreeScale = 100000000 / 90
        timeoutInSeconds = 0
        nextTargetSpeed = 0
        missionIsCompleted = False
        hasTarget = False
        enemyIsDetected = False
        enemy = None

        myloc = []
        myinfo = []

        while not hasTarget or not missionIsCompleted:

            weightedMeanOrintation = random.randint(0,1000)/1000
            centerVectorWeight = 1 - weightedMeanOrintation/2
            otherVectorWeight = 1 + weightedMeanOrintation/2

            state = self.state.getAgentStatus()
            legalForm = self.config.get("Formation")
            minLegalDistance = self.config.get("minLegalDistance")/eachDegreeScale
            maxLegalDistance = self.config.get("maxLegalDistance")/eachDegreeScale
            minLegalSpeed = self.config.get("minLegalSpeed")
            maxLegalSpeed = self.config.get("maxLegalSpeed")
            minLegalCoherence = self.config.get("minLegalCoherence")
            normalCoherence = self.config.get("normalCoherence")
            legalReachDistance = self.config.get("reachDistance")/eachDegreeScale
            objects = []

            nearestPoint = []
            nearestDistance = -1
            direction = [0,0,0]
            center = [0,0,0]
            totalCenter = [0,0,0]
            reachDistance = legalReachDistance * 2

            targets = []
            isReached = False
            nextTarget = None
            missionIsCompleted = True
            lastTarget = False
            if "Targets" in state and len(myloc) == 3:
                if enemyIsDetected:
                    targets = enemy.targets
                else:
                    targets = state["Targets"].targets
                counter = 0
                if targets and len(targets) > 0:
                    hasTarget = True
                    for target in targets:

                        if counter == len(targets) - 1:
                            lastTarget = True

                        if target.isReached == False:
                            missionIsCompleted = False
                            nextTarget = [target.location.latitude,target.location.longitude,target.location.altitude]
                            reachDistance = ((nextTarget[0]-myloc[0])**2+(nextTarget[1]-myloc[1])**2+(nextTarget[2]-myloc[2])**2)**0.5
                            if ( lastTarget and reachDistance < (1/eachDegreeScale) ) or ( not lastTarget and reachDistance < legalReachDistance):
                                self.state.setReached(counter)
                                state["Targets"].targets[counter].isReached = True
                                targets[counter].isReached = True
                                isReached = True
                                if not lastTarget:
                                    nextTarget = [targets[counter+1].location.latitude,targets[counter+1].location.longitude,targets[counter+1].location.altitude]
                                else:
                                    nextTarget = None
                                    missionIsCompleted = True
                            
                            timeout = target.deadline
                            timeout = timeout - datetime.datetime.now()
                            timeoutInSeconds = timeout.total_seconds()
                            if timeoutInSeconds < 0:
                                timeoutInSeconds = 1

                            break
                        counter = counter + 1
                    if missionIsCompleted:
                        break
                else:
                    hasTarget = False
                    self.state.subscribeWayPoint()
            else:
                hasTarget = False
                self.state.subscribeWayPoint()

            # if self.ID == 10:
            #     print(len(targets))
            #     print(myloc)

            if "objects" in state and len(state["objects"]) > 0:
                friendsCount = 0
                for obj in state["objects"]:
                    if obj["party"] == "friend" and obj["object_id"] != int(self.ID):
                        objects.append([obj["location"]["lat"],obj["location"]["lon"],obj["location"]["alt"]])
                        center[0] += obj["location"]["lat"]
                        center[1] += obj["location"]["lon"]
                        center[2] += obj["location"]["alt"]
                        friendsCount = friendsCount + 1
                    elif obj["party"] == "enemy":
                        if not obj["object_id"] in self.detectedEnemies:
                            enemyIsDetected = True
                            self.detectedEnemies.append(obj["object_id"])

                            distance_to_enemy = ((myloc[0] - obj["location"]["lat"])**2+(myloc[1] - obj["location"]["lon"])**2+(myloc[2] - obj["location"]["alt"])**2)**0.5
                            timeout_to_enemy = int(distance_to_enemy / (maxLegalSpeed*0.8))
                            if timeout_to_enemy == 0:
                                timeout_to_enemy = 1

                            enemy = WayPoint()
                            t = TargetInfo(timeout_to_enemy, 2, obj["location"]["lat"], obj["location"]["lon"], obj["location"]["alt"])
                            enemy.append(t)
                            self.state.receiveTargets({"WayPoint":enemy})
                            self.DDS.publish({"WayPoint":enemy}, True)
                    elif obj["object_id"] == int(self.ID):
                        myloc = [obj["location"]["lat"],obj["location"]["lon"],obj["location"]["alt"]]
                        myinfo = obj

                    if obj["party"] == "friend":
                        totalCenter[0] += obj["location"]["lat"]
                        totalCenter[1] += obj["location"]["lon"]
                        totalCenter[2] += obj["location"]["alt"]

                if len(myloc) == 3:

                    totalCenter[0] = totalCenter[0] / (friendsCount + 1)
                    totalCenter[1] = totalCenter[1] / (friendsCount + 1)
                    totalCenter[2] = totalCenter[2] / (friendsCount + 1)

                    centerVariance = 0
                    for obj in state["objects"]:
                        if obj["party"] == "friend":
                            centerVariance += (obj["location"]["lat"] - totalCenter[0])**2 + (obj["location"]["lon"] - totalCenter[1])**2 + (obj["location"]["alt"] - totalCenter[2])**2
                    centerVariance = centerVariance / (friendsCount + 1)
                    centerVariance = centerVariance ** 0.5

                    numberOfOutObjects = 0
                    if centerVariance > maxLegalDistance:
                        for obj in state["objects"]:
                            if obj["party"] == "friend":
                                tmpDistance = ((obj["location"]["lat"] - totalCenter[0])**2 + (obj["location"]["lon"] - totalCenter[1])**2 + (obj["location"]["alt"] - totalCenter[2])**2) ** 0.5
                                if tmpDistance > 2*centerVariance:
                                    numberOfOutObjects = numberOfOutObjects + 1
                    
                    if (numberOfOutObjects/(friendsCount+1)) > (1 - minLegalCoherence) and hasTarget:
                        missionIsCompleted = True

                    if friendsCount > 0:
                        center[0] = center[0] / friendsCount
                        center[1] = center[1] / friendsCount
                        center[2] = center[2] / friendsCount
                    else:
                        center = myloc

                    nearestDistance = -1
                    for obj in objects:
                        distance = ((obj[0]-myloc[0])**2 + (obj[1]-myloc[1])**2 + (obj[2]-myloc[2])**2)**0.5
                        if nearestDistance > distance or nearestDistance == -1:
                            nearestDistance = distance
                            nearestPoint = obj

                    objects_withme = objects
                    objects_withme.append(myloc)

                    center_me_vector = [myloc[0] - center[0], myloc[1] - center[1], myloc[2] - center[2]]
                    if len(nearestPoint) > 0:
                        center_nearestpoint_vector = [nearestPoint[0] - center[0], nearestPoint[1] - center[1], nearestPoint[2] - center[2]]
                        nearest_me_vector = [myloc[0] - nearestPoint[0], myloc[1] - nearestPoint[1], myloc[2] - nearestPoint[2]]
                    else:
                        center_nearestpoint_vector = [0, 0, 0]
                        nearest_me_vector = [0, 0, 0]
                    center_me_distance = (center_me_vector[0]**2+center_me_vector[1]**2+center_me_vector[2]**2)**0.5
                    nearest_me_distance = (nearest_me_vector[0]**2+nearest_me_vector[1]**2+nearest_me_vector[2]**2)**0.5
                    center_nearestpoint_distance = (center_nearestpoint_vector[0]**2+center_nearestpoint_vector[1]**2+center_nearestpoint_vector[2]**2)**0.5
                    if center_me_distance != 0:
                        center_me_vector = [center_me_vector[0]/center_me_distance,center_me_vector[1]/center_me_distance,center_me_vector[2]/center_me_distance]
                    if nearest_me_distance != 0:
                        nearest_me_vector = [nearest_me_vector[0]/nearest_me_distance,nearest_me_vector[1]/nearest_me_distance,nearest_me_vector[2]/nearest_me_distance]
                    if center_nearestpoint_distance != 0:
                        center_nearestpoint_vector = [center_nearestpoint_vector[0]/center_nearestpoint_distance,center_nearestpoint_vector[1]/center_nearestpoint_distance,center_nearestpoint_vector[2]/center_nearestpoint_distance]

                    orthogonal_center_me_vector = center_me_vector

                    if random.random() > 0.5:
                        orthogonal_center_me_vector[0] = center_me_vector[1] 
                        orthogonal_center_me_vector[1] = -1*center_me_vector[0] 
                    else:
                        orthogonal_center_me_vector[0] = -1*center_me_vector[1] 
                        orthogonal_center_me_vector[1] = center_me_vector[0] 

                    # if center_me_vector[0]*center_me_vector[1] >= 0:
                    #     orthogonal_center_me_vector[0] = center_me_vector[1] 
                    #     orthogonal_center_me_vector[1] = -1*center_me_vector[0] 
                    # else:
                    #     orthogonal_center_me_vector[0] = -1*center_me_vector[1] 
                    #     orthogonal_center_me_vector[1] = center_me_vector[0] 

                    center_is_between_me_and_nearest_point = False

                    cosine_sign_me_nearestpoint_center = center_me_vector[0]*center_nearestpoint_vector[0] + center_me_vector[1]*center_nearestpoint_vector[1] + center_me_vector[2]*center_nearestpoint_vector[2]
                    if cosine_sign_me_nearestpoint_center < 0:
                        center_is_between_me_and_nearest_point = True

                    target_me_vector = None
                    if nextTarget != None:
                        target_me_vector = [myloc[0] - nextTarget[0], myloc[1] - nextTarget[1], myloc[2] - nextTarget[2]]
                        target_me_distance = (target_me_vector[0]**2+target_me_vector[1]**2+target_me_vector[2]**2)**0.5
                        if target_me_distance > 0:
                            target_me_vector = [target_me_vector[0]/target_me_distance,target_me_vector[1]/target_me_distance,target_me_vector[2]/target_me_distance]
                        target_me_distance *= eachDegreeScale
                        nextTargetSpeed = target_me_distance / timeoutInSeconds
                        if nextTargetSpeed > ConfigurationFactory.getInstance().get("maxLegalSpeed"):
                            nextTargetSpeed = ConfigurationFactory.getInstance().get("maxLegalSpeed")
                        if nextTargetSpeed < minLegalSpeed:
                            nextTargetSpeed = minLegalSpeed

                    if len(objects) > 0:
                        popt_withoutme = [0, 0, objects[0][2]]
                        popt_withme = [0, 0, objects_withme[0][2]]
                        popt_legal = [0, 0, legalForm[0][2]]
                        try:
                            if len(objects) > 2:
                                popt_withoutme, pcov = curve_fit(simplePlate, (np.array([item[0] for item in objects]), np.array([item[1] for item in objects])), np.array([item[2] for item in objects]))
                            if len(objects_withme) > 2:
                                popt_withme, pcov = curve_fit(simplePlate, (np.array([item[0] for item in objects_withme]), np.array([item[1] for item in objects_withme])), np.array([item[2] for item in objects_withme]))
                            if len(legalForm) > 2:
                                popt_legal, pcov = curve_fit(simplePlate, (np.array([item[0] for item in legalForm]), np.array([item[1] for item in legalForm])), np.array([item[2] for item in legalForm]))
                        except Exception as e:
                            pass
                            # print("==========\n Error is: \n", e)
                            # print(traceback.format_exc())

                        if len(objects) > 3 and len(legalForm) > 3:
                            adjusted_objects = []
                            adjusted_objects_withme = []
                            adjusted_legal = []

                            adjusted_objects = self.layDown(objects, popt_withoutme)
                            adjusted_objects_withme = self.layDown(objects, popt_withme)
                            adjusted_legal = self.layDown(objects, popt_legal)

                            withoutme_hull = ConvexHull(adjusted_objects)
                            withme_hull = ConvexHull(adjusted_objects_withme)
                            legal_hull = ConvexHull(adjusted_legal)

                            newPoints = []
                            for value in withoutme_hull.vertices:
                                newPoints.append(adjusted_objects[value])
                            withoutme_poly = Polygon(newPoints)
                            newPoints = []
                            for value in withme_hull.vertices:
                                newPoints.append(adjusted_objects_withme[value])
                            withme_poly = Polygon(newPoints)
                            newPoints = []
                            for value in legal_hull.vertices:
                                newPoints.append(adjusted_legal[value])
                            legal_poly = Polygon(newPoints)

                            if not withme_poly.is_valid:
                                withme_poly = self.fix_geom(withme_poly)
                            if not withoutme_poly.is_valid:
                                withoutme_poly = self.fix_geom(withoutme_poly)
                            if not legal_poly.is_valid:
                                legal_poly = self.fix_geom(legal_poly)
                            withme_intersect = legal_poly.intersection(withme_poly).area
                            withoutme_intersect = legal_poly.intersection(withoutme_poly).area

                            withme_area = withme_hull.area
                            withoutme_area = withoutme_hull.area
                            legal_area = legal_hull.area
                        else:
                            withme_area = 1
                            withoutme_area = 1
                            legal_area = 1
                            withme_intersect = 1
                            withoutme_intersect = 1

                    if hasTarget and lastTarget and reachDistance < 2*legalReachDistance and nextTarget != None:
                        lastDecision = 'approach'
                        self.actuator.goto(nextTarget[0], nextTarget[1], nextTarget[2], timeoutInSeconds, 1)
                        self.DB.insert("Decisions", {"status":"STRAIGHTTOTARGET","goto":{"lat":nextTarget[0], "lon":nextTarget[1], "alt":nextTarget[2], "timeout":timeoutInSeconds, "behave":1}})
                    else:

                        outOfFormCloseCond = legal_area / 1.2*withme_area
                        if withme_intersect > 0 and withoutme_intersect > 0 and withoutme_area > 0:
                            outOfFormCond = (withme_area/withme_intersect) / (withoutme_area/withoutme_intersect)
                        else:
                            outOfFormCond = 1000
                        if nearestDistance > 0 :
                            veryCloseCond = minLegalDistance / nearestDistance
                        else:
                            veryCloseCond = 1000
                        veryFarCond = nearestDistance / maxLegalDistance
                        # if (center_me_distance/(maxLegalDistance*((len(objects)+1)/8))) > veryFarCond:
                        #     veryFarCond = (center_me_distance/(maxLegalDistance*((len(objects)+1)/8)))

                        outOfFormCloseCondTurn = False
                        outOfFormCondTurn = False
                        veryCloseCondTurn = False
                        veryFarCondTurn = False

                        if not missionIsCompleted:
                            if outOfFormCloseCond > 1 and outOfFormCloseCond > outOfFormCond and outOfFormCloseCond > veryCloseCond and outOfFormCloseCond > veryFarCond and len(objects) > 0 and withoutme_intersect > 0 and withme_intersect > 0 and (withme_area/withme_intersect) > 1:
                                outOfFormCloseCondTurn = True
                            elif outOfFormCond > 1 and outOfFormCond > veryCloseCond and outOfFormCond > veryFarCond and len(objects) > 0 and withoutme_intersect > 0 and withme_intersect > 0 and (withme_area/withme_intersect) > 1:
                                outOfFormCondTurn = True
                            elif outOfFormCond > 1 and outOfFormCond > veryCloseCond and outOfFormCond > veryFarCond and len(objects) > 0 and withoutme_intersect > 0 and withme_intersect == 0:
                                outOfFormCondTurn = True
                            elif veryCloseCond > 1 and veryCloseCond > veryFarCond and len(objects) > 0 and len(nearestPoint) > 0 and (not lastTarget or reachDistance > minLegalDistance):
                                veryCloseCondTurn = True
                            elif veryFarCond > 1 and len(objects) > 0 and len(nearestPoint) > 0:
                                veryFarCondTurn = True
                            
                        # if outOfFormCloseCond > outOfFormCond and outOfFormCloseCond > veryCloseCond and outOfFormCloseCond > veryFarCond and lastDecision != 'maneuver-form' and len(objects) > 0 and withoutme_intersect > 0 and withme_intersect > 0 and (withoutme_area/withoutme_intersect) < (withme_area/withme_intersect) and (withme_area/withme_intersect) > 1:
                        #     outOfFormCloseCondTurn = True
                        # elif outOfFormCond > veryCloseCond and outOfFormCond > veryFarCond and lastDecision != 'maneuver-form' and len(objects) > 0 and withoutme_intersect > 0 and withme_intersect > 0 and (withoutme_area/withoutme_intersect) < (withme_area/withme_intersect) and (withme_area/withme_intersect) > 1:
                        #     outOfFormCondTurn = True
                        # elif outOfFormCond > veryCloseCond and outOfFormCond > veryFarCond and lastDecision != 'maneuver-form' and len(objects) > 0 and withoutme_intersect > 0 and withme_intersect == 0:
                        #     outOfFormCondTurn = True
                        # elif veryCloseCond > veryFarCond and lastDecision != 'maneuver-close' and len(objects) > 0 and nearestDistance < minLegalDistance and len(nearestPoint) > 0 and not lastTarget:
                        #     veryCloseCondTurn = True
                        # elif lastDecision != 'maneuver-far' and len(objects) > 0 and nearestDistance > maxLegalDistance and len(nearestPoint) > 0:
                        #     veryFarCondTurn = True
                            
                        decisionState = {}
                        decisionState["OutOfForm"] = outOfFormCond
                        decisionState["OutOfFormClose"] = outOfFormCloseCond
                        decisionState["VeryClose"] = veryCloseCond
                        decisionState["VeryFar"] = veryFarCond
                        decisionState["LastDecision"] = lastDecision
                        decisionState["MissionFailure"] = numberOfOutObjects/(friendsCount+1)

                        if outOfFormCloseCondTurn :
                            if nextTarget != None:
                                if (numberOfOutObjects/(friendsCount+1)) < (1 - normalCoherence) and nextTargetSpeed < maxLegalSpeed:
                                    newdirection = [(centerVectorWeight*orthogonal_center_me_vector[0]-otherVectorWeight*target_me_vector[0])/2,(centerVectorWeight*orthogonal_center_me_vector[1]-otherVectorWeight*target_me_vector[1])/2,(centerVectorWeight*orthogonal_center_me_vector[2]-otherVectorWeight*target_me_vector[2])/2]
                                else:
                                    newdirection = [-1*target_me_vector[0],-1*target_me_vector[1],-1*target_me_vector[2]]
                            else:
                                newdirection = orthogonal_center_me_vector
                            directionSize = (newdirection[0]**2 + newdirection[1]**2 + newdirection[2]**2)**0.5
                            if directionSize > 0:
                                newdirection = [(180*math.acos(newdirection[0]/directionSize))/math.pi,(180*math.acos(newdirection[1]/directionSize))/math.pi,(180*math.acos(newdirection[2]/directionSize))/math.pi]

                                newspeed = abs(myinfo["velocity"]["speed"])
                                if nextTarget != None:
                                    newspeed = nextTargetSpeed
                                if newspeed < minLegalSpeed:
                                    newspeed = minLegalSpeed

                                self.actuator.moveMe(newspeed, newdirection[0], newdirection[1], newdirection[2], 0)
                                self.DB.insert("Decisions", {"status":"OUTOFFORM","conditions":decisionState,"maneuver":{"speed":newspeed, "alpha":newdirection[0], "beta":newdirection[1], "gamma":newdirection[2], "acceleration":0}})
                            else:
                                newspeed = abs(myinfo["velocity"]["speed"])
                                if nextTarget != None:
                                    newspeed = nextTargetSpeed
                                if newspeed < minLegalSpeed:
                                    newspeed = minLegalSpeed

                                self.actuator.moveMe(newspeed, myinfo["velocity"]["direction"]["alpha"], myinfo["velocity"]["direction"]["beta"], myinfo["velocity"]["direction"]["gamma"], 0)
                                self.DB.insert("Decisions", {"status":"OUTOFFORM","conditions":decisionState,"maneuver":{"speed":newspeed, "alpha":myinfo["velocity"]["direction"]["alpha"], "beta":myinfo["velocity"]["direction"]["beta"], "gamma":myinfo["velocity"]["direction"]["gamma"], "acceleration":0}})
                            lastDecision = 'maneuver-form'

                        elif outOfFormCondTurn and withoutme_intersect > 0 and withme_intersect > 0 :
                            if (numberOfOutObjects/(friendsCount+1)) < (1 - normalCoherence) and nextTargetSpeed < maxLegalSpeed:
                                newdirection = [-1*center_me_vector[0],-1*center_me_vector[1],-1*center_me_vector[2]]
                            elif nextTarget != None:
                                newdirection = [-1*target_me_vector[0],-1*target_me_vector[1],-1*target_me_vector[2]]
                            else:
                                newdirection = [-1*center_me_vector[0],-1*center_me_vector[1],-1*center_me_vector[2]]
                            directionSize = (newdirection[0]**2 + newdirection[1]**2 + newdirection[2]**2)**0.5
                            newdirection = [(180*math.acos(newdirection[0]/directionSize))/math.pi,(180*math.acos(newdirection[1]/directionSize))/math.pi,(180*math.acos(newdirection[2]/directionSize))/math.pi]
                            newspeed = myinfo["velocity"]["speed"] * ((withme_area/withme_intersect)/(withoutme_area/withoutme_intersect))
                            if newspeed > ConfigurationFactory.getInstance().get("maxLegalSpeed"):
                                newspeed = ConfigurationFactory.getInstance().get("maxLegalSpeed")
                            if newspeed < minLegalSpeed:
                                newspeed = minLegalSpeed
                            lastDecision = 'maneuver-form'
                            self.actuator.moveMe(newspeed, newdirection[0], newdirection[1], newdirection[2], ((withme_area/withme_intersect)/(withoutme_area/withoutme_intersect)))
                            self.DB.insert("Decisions", {"status":"OUTOFFORM","conditions":decisionState,"maneuver":{"speed":newspeed, "alpha":newdirection[0], "beta":newdirection[1], "gamma":newdirection[2], "acceleration":((withme_area/withme_intersect)/(withoutme_area/withoutme_intersect))}})                        
                        elif outOfFormCondTurn :
                            if (numberOfOutObjects/(friendsCount+1)) < (1 - normalCoherence) and nextTargetSpeed < maxLegalSpeed:
                                newdirection = [-1*center_me_vector[0],-1*center_me_vector[1],-1*center_me_vector[2]]
                            elif nextTarget != None:
                                newdirection = [-1*target_me_vector[0],-1*target_me_vector[1],-1*target_me_vector[2]]
                            else:
                                newdirection = [-1*center_me_vector[0],-1*center_me_vector[1],-1*center_me_vector[2]]

                            directionSize = (newdirection[0]**2 + newdirection[1]**2 + newdirection[2]**2)**0.5
                            newdirection = [(180*math.acos(newdirection[0]/directionSize))/math.pi,(180*math.acos(newdirection[1]/directionSize))/math.pi,(180*math.acos(newdirection[2]/directionSize))/math.pi]
                            newspeed = myinfo["velocity"]["speed"] * 1.5
                            if newspeed > ConfigurationFactory.getInstance().get("maxLegalSpeed"):
                                newspeed = ConfigurationFactory.getInstance().get("maxLegalSpeed")
                            if newspeed < minLegalSpeed:
                                newspeed = minLegalSpeed
                            lastDecision = 'maneuver-form'
                            self.actuator.moveMe(newspeed, newdirection[0], newdirection[1], newdirection[2], ((withme_area/withme_intersect)/(withoutme_area/withoutme_intersect)))
                            self.DB.insert("Decisions", {"status":"OUTOFFORM","conditions":decisionState,"maneuver":{"speed":newspeed, "alpha":newdirection[0], "beta":newdirection[1], "gamma":newdirection[2], "acceleration":((withme_area/withme_intersect)/(withoutme_area/withoutme_intersect))}})

                        elif veryCloseCondTurn :

                            if center_is_between_me_and_nearest_point:
                                # Go mean vector of reverse vector to center and straight vector to the target
                                if nextTarget != None:
                                    if (numberOfOutObjects/(friendsCount+1)) < (1 - normalCoherence) and nextTargetSpeed < maxLegalSpeed:
                                        newdirection = [(centerVectorWeight*center_me_vector[0]+nearest_me_vector[0]-otherVectorWeight*target_me_vector[0])/3,(centerVectorWeight*center_me_vector[1]+nearest_me_vector[1]-otherVectorWeight*target_me_vector[1])/3,(centerVectorWeight*center_me_vector[2]+nearest_me_vector[2]-otherVectorWeight*target_me_vector[2])/3]
                                    else:
                                        newdirection = [-1*target_me_vector[0],-1*target_me_vector[1],-1*target_me_vector[2]]
                                else:
                                    newdirection = [(center_me_vector[0]+nearest_me_vector[0])/2,(center_me_vector[1]+nearest_me_vector[1])/2,(center_me_vector[2]+nearest_me_vector[2])/2]
                            else:
                                if center_me_distance < center_nearestpoint_distance:
                                    if nextTarget != None:
                                        if (numberOfOutObjects/(friendsCount+1)) < (1 - normalCoherence) and nextTargetSpeed < maxLegalSpeed:
                                            newdirection = [(centerVectorWeight*orthogonal_center_me_vector[0]+nearest_me_vector[0]-otherVectorWeight*target_me_vector[0])/3,(centerVectorWeight*orthogonal_center_me_vector[1]+nearest_me_vector[1]-otherVectorWeight*target_me_vector[1])/3,(centerVectorWeight*orthogonal_center_me_vector[2]+nearest_me_vector[2]-otherVectorWeight*target_me_vector[2])/3]
                                        else:
                                            newdirection = [-1*target_me_vector[0],-1*target_me_vector[1],-1*target_me_vector[2]]
                                    else:
                                        newdirection = [(orthogonal_center_me_vector[0]+nearest_me_vector[0])/2,(orthogonal_center_me_vector[1]+nearest_me_vector[1])/2,(orthogonal_center_me_vector[2]+nearest_me_vector[2])/2]
                                else:
                                    if nextTarget != None:
                                        if (numberOfOutObjects/(friendsCount+1)) < (1 - normalCoherence) and nextTargetSpeed < maxLegalSpeed:
                                            newdirection = [(centerVectorWeight*center_me_vector[0]+nearest_me_vector[0]-otherVectorWeight*target_me_vector[0])/3,(centerVectorWeight*center_me_vector[1]+nearest_me_vector[1]-otherVectorWeight*target_me_vector[1])/3,(centerVectorWeight*center_me_vector[2]+nearest_me_vector[2]-otherVectorWeight*target_me_vector[2])/3]
                                        else:
                                            newdirection = [-1*target_me_vector[0],-1*target_me_vector[1],-1*target_me_vector[2]]
                                    else:
                                        newdirection = [(center_me_vector[0]+nearest_me_vector[0])/2,(center_me_vector[1]+nearest_me_vector[1])/2,(center_me_vector[2]+nearest_me_vector[2])/2]

                            directionSize = (newdirection[0]**2 + newdirection[1]**2 + newdirection[2]**2)**0.5
                            if directionSize > 0:
                                newdirection = [(180*math.acos(newdirection[0]/directionSize))/math.pi,(180*math.acos(newdirection[1]/directionSize))/math.pi,(180*math.acos(newdirection[2]/directionSize))/math.pi]

                                newspeed = abs(myinfo["velocity"]["speed"])
                                if nextTarget != None:
                                    newspeed = nextTargetSpeed
                                if newspeed < minLegalSpeed:
                                    newspeed = minLegalSpeed

                                self.actuator.moveMe(newspeed, newdirection[0], newdirection[1], newdirection[2], 0)
                                self.DB.insert("Decisions", {"status":"VERYCLOSE","conditions":decisionState,"maneuver":{"speed":newspeed, "alpha":newdirection[0], "beta":newdirection[1], "gamma":newdirection[2], "acceleration":0}})
                            else:
                                newspeed = abs(myinfo["velocity"]["speed"])
                                if nextTarget != None:
                                    newspeed = nextTargetSpeed
                                if newspeed < minLegalSpeed:
                                    newspeed = minLegalSpeed

                                self.actuator.moveMe(newspeed, myinfo["velocity"]["direction"]["alpha"], myinfo["velocity"]["direction"]["beta"], myinfo["velocity"]["direction"]["gamma"], 0)
                                self.DB.insert("Decisions", {"status":"VERYCLOSE","conditions":decisionState,"maneuver":{"speed":newspeed, "alpha":myinfo["velocity"]["direction"]["alpha"], "beta":myinfo["velocity"]["direction"]["beta"], "gamma":myinfo["velocity"]["direction"]["gamma"], "acceleration":0}})

                            lastDecision = 'maneuver-close'

                        elif veryFarCondTurn :

                            if nextTarget != None:
                                if nextTargetSpeed >= maxLegalSpeed:
                                    newdirection = [-1*target_me_vector[0],-1*target_me_vector[1],-1*target_me_vector[2]]
                                elif (numberOfOutObjects/(friendsCount+1)) < (1 - normalCoherence):
                                    newdirection = [-1 * nearest_me_vector[0], -1 * nearest_me_vector[1], -1 * nearest_me_vector[2]]
                                    # newdirection = [(-1*centerVectorWeight*center_me_vector[0]-otherVectorWeight*target_me_vector[0])/2,(-1*centerVectorWeight*center_me_vector[1]-otherVectorWeight*target_me_vector[1])/2,(-1*centerVectorWeight*center_me_vector[2]-otherVectorWeight*target_me_vector[2])/2]
                                else:
                                    newdirection = [-1 * nearest_me_vector[0], -1 * nearest_me_vector[1], -1 * nearest_me_vector[2]]
                                    # newdirection = [(-1*centerVectorWeight*center_me_vector[0]-otherVectorWeight*target_me_vector[0])/2,(-1*centerVectorWeight*center_me_vector[1]-otherVectorWeight*target_me_vector[1])/2,(-1*centerVectorWeight*center_me_vector[2]-otherVectorWeight*target_me_vector[2])/2]
                            else:
                                newdirection = [-1*nearest_me_vector[0],-1*nearest_me_vector[1],-1*nearest_me_vector[2]]

                            directionSize = (newdirection[0]**2 + newdirection[1]**2 + newdirection[2]**2)**0.5
                            if directionSize > 0:
                                newdirection = [(180*math.acos(newdirection[0]/directionSize))/math.pi,(180*math.acos(newdirection[1]/directionSize))/math.pi,(180*math.acos(newdirection[2]/directionSize))/math.pi]

                                newspeed = abs(myinfo["velocity"]["speed"])
                                if nextTarget != None:
                                    newspeed = nextTargetSpeed
                                # newspeed = int(newspeed * veryFarCond)
                                if newspeed > maxLegalSpeed:
                                    newspeed = maxLegalSpeed
                                if newspeed < minLegalSpeed:
                                    newspeed = minLegalSpeed

                                self.actuator.moveMe(newspeed, newdirection[0], newdirection[1], newdirection[2], 0)
                                self.DB.insert("Decisions", {"status":"VERYFAR","conditions":decisionState,"maneuver":{"speed":newspeed, "alpha":newdirection[0], "beta":newdirection[1], "gamma":newdirection[2], "acceleration":0}})
                            else:
                                newspeed = abs(myinfo["velocity"]["speed"])
                                if nextTarget != None:
                                    newspeed = nextTargetSpeed
                                # newspeed = int(newspeed * veryFarCond)
                                if newspeed > maxLegalSpeed:
                                    newspeed = maxLegalSpeed
                                if newspeed < minLegalSpeed:
                                    newspeed = minLegalSpeed

                                self.actuator.moveMe(newspeed, myinfo["velocity"]["direction"]["alpha"], myinfo["velocity"]["direction"]["beta"], myinfo["velocity"]["direction"]["gamma"], 0)
                                self.DB.insert("Decisions", {"status":"VERYFAR","conditions":decisionState,"maneuver":{"speed":newspeed, "alpha":myinfo["velocity"]["direction"]["alpha"], "beta":myinfo["velocity"]["direction"]["beta"], "gamma":myinfo["velocity"]["direction"]["gamma"], "acceleration":0}})
                            lastDecision = 'maneuver-far'

                        else:
                            if missionIsCompleted:
                                if lastDecision != "tired":
                                    self.actuator.iAmTired()
                                    self.DB.insert("Decisions", {"status":"MISSIONCOMPLETE","conditions":decisionState})
                                lastDecision = "tired"
                            elif nextTarget != None:
                                lastDecision = 'approach'
                                self.actuator.goto(nextTarget[0], nextTarget[1], nextTarget[2], timeoutInSeconds, 1)
                                self.DB.insert("Decisions", {"status":"STRAIGHTTOTARGET","conditions":decisionState,"goto":{"lat":nextTarget[0], "lon":nextTarget[1], "alt":nextTarget[2], "timeout":timeoutInSeconds, "behave":1}})
                                
            else:                    
                if missionIsCompleted:
                    if lastDecision != "alonetired":
                        self.actuator.iAmTired()
                        self.DB.insert("Decisions", {"status":"MISSIONCOMPLETE","alone":"true"})
                    lastDecision = "alonetired"
                elif nextTarget != None:
                    lastDecision = 'approach'
                    self.actuator.goto(nextTarget[0], nextTarget[1], nextTarget[2], timeoutInSeconds, 1)
                    self.DB.insert("Decisions", {"status":"STRAIGHTTOTARGET","goto":{"lat":nextTarget[0], "lon":nextTarget[1], "alt":nextTarget[2], "timeout":timeoutInSeconds, "behave":1}})

            time.sleep(self.config.get("DecisionSentivity"))

        decisionState = {}
        decisionState["HasTarget"] = hasTarget
        decisionState["MissionIsCompleted"] = missionIsCompleted
        self.actuator.iAmTired()
        self.DB.insert("Decisions", {"status":"MISSIONCOMPLETE","alone":"true","conditions":decisionState})

    def __init__(self, ID: str):

        self.ID = ID
        self.detectedEnemies = []
        self.config = ConfigurationFactory()
        self.DB = localDB.getInstance()
        self.DDS = DDSWrapper.getInstance(self.ID)
        self.actuator = Actuator(self.ID)
        self.state = StateAggregator(self.ID)
        self.env = Environment(self.ID)

        self.stateWatch = threading.Thread(target=self.fetchState, args=())
        self.stateWatch.start()



