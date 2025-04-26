import cv2
import threading
from flask import Flask, render_template, jsonify, request, redirect, url_for
import mediapipe as mp
import numpy as np
import winsound
import pyttsx3
import time
from twilio.rest import Client
import json

# Twilio setup
account_sid = "AC43c980359c0c2584c5b4808dc856f51e"
auth_token = "23d75fdba1f81837f017e5f495286541"
twilio_phone_number = "+19413940345"
with open("current_user.json", "r") as f:
    data = json.load(f)

to_phone_number = f"+91{data.get('phone_number')}"
print("Using phone number:", to_phone_number)
#to_phone_number="=+919866362629"
username = data.get("username")
client = Client(account_sid, auth_token)

# Alert counters
drowsy_count = 0
yawn_count = 0
hands_count = 0

# Add flags to track if an SMS has been sent for each count
drowsy_sent = False
yawn_sent = False
hands_sent = False

# Add flags for calls
drowsy_calls_sent = False
yawn_calls_sent = False
hands_calls_sent = False

# Initialize the Twilio client
drowsiness_call_url = 'https://driver-alerts-8035.twil.io/drowsiness'
yawning_call_url = 'https://driver-alerts-8035.twil.io/yawning'
hands_call_url = 'https://driver-alerts-8035.twil.io/hands'

# Mediapipe module with face mesh and hands
mp_face_mesh = mp.solutions.face_mesh
mp_hands = mp.solutions.hands
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=False, max_num_faces=2, refine_landmarks=True)
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=2)

# Time module
eye_start = None
mouth_start = None
eye_3shold = 3
mouth_3shold = 2

# Alarm module with winsound
def alarm1():
    winsound.Beep(800, 500)

def alarm2():
    winsound.Beep(1200, 500)

def alarm3():
    winsound.Beep(1500, 500)

# Text-to-speech module
text_to_speech = pyttsx3.init()  # Initialize the text-to-speech engine
text_to_speech.setProperty('rate', 100)
text_to_speech.setProperty('volume', 10)

def speech(msg):  # Function to convert text to speech
    text_to_speech.say(msg)
    text_to_speech.runAndWait()

cap = cv2.VideoCapture(0)
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    current_time = time.time()
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # BGR to RGB
    res = face_mesh.process(rgb_frame)
    hands_res = hands.process(rgb_frame)

    # Face detection
    if res.multi_face_landmarks:
        for face_landmarks in res.multi_face_landmarks:
            landmarks = [(int(point.x * frame.shape[1]), int(point.y * frame.shape[0])) for point in face_landmarks.landmark]

            # Mouth detection
            upper_lip = np.array([(face_landmarks.landmark[i].x, face_landmarks.landmark[i].y) for i in [61, 185, 40, 39, 37, 0, 267, 269, 270, 409]])
            lower_lip = np.array([(face_landmarks.landmark[i].x, face_landmarks.landmark[i].y) for i in [146, 91, 181, 84, 17, 314, 405, 321, 375, 291]])
            lip_distance = np.mean([abs(ul[1] - ll[1]) for ul, ll in zip(upper_lip, lower_lip)])
            yawn_3shold = 0.05

            # Eye detection
            LEFT_EYE_INDICES = [362, 385, 387, 263, 373, 380]
            RIGHT_EYE_INDICES = [33, 160, 158, 133, 153, 144]

            left_eye = np.array([(landmarks[i][0], landmarks[i][1]) for i in LEFT_EYE_INDICES])
            right_eye = np.array([(landmarks[i][0], landmarks[i][1]) for i in RIGHT_EYE_INDICES])

            # Left eye landmarks
            left_horif = np.linalg.norm(left_eye[0] - left_eye[3])
            left_ver1 = np.linalg.norm(left_eye[1] - left_eye[4])
            left_ver2 = np.linalg.norm(left_eye[2] - left_eye[5])
            left_ratio = (left_ver1 + left_ver2) / left_horif

            # Right eye landmarks
            right_horir = np.linalg.norm(right_eye[0] - right_eye[3])
            right_ver1 = np.linalg.norm(right_eye[1] - right_eye[4])
            right_ver2 = np.linalg.norm(right_eye[2] - right_eye[5])
            right_ratio = (right_ver1 + right_ver2) / right_horir

            avg_eye = (left_ratio + right_ratio) / 2
            eye_3shold = 0.85

            cv2.putText(frame, f"EYE: {avg_eye:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Mouth: {lip_distance:.2f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            if avg_eye < eye_3shold:
                if eye_start is None:
                    eye_start = current_time
                elif current_time - eye_start > 2:
                    cv2.putText(frame, 'Drowsiness Detected', (270, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    speech("Drowsiness detected, please stay alert.")
                    drowsy_count += 1
                    if drowsy_count % 5 == 0 and not drowsy_sent:
                        client.messages.create(
                            body="Alert: Drowsiness detected multiple times. Driver may be tired.",
                            from_=twilio_phone_number,
                            to=to_phone_number
                        )
                        drowsy_sent = True
                        if drowsy_count % 15 == 0 and not drowsy_calls_sent:
                            client.calls.create(
                                url=drowsiness_call_url,
                                to=to_phone_number,
                                from_=twilio_phone_number
                            )
                            drowsy_calls_sent = True
                else:
                    eye_start = None

            if lip_distance > yawn_3shold:
                if mouth_start is None:
                    mouth_start = current_time
                elif current_time - mouth_start > 2:
                    cv2.putText(frame, 'Yawning Detected', (270, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    speech("Yawning detected, please take a break.")
                    yawn_count += 1
                    if yawn_count % 5 == 0 and not yawn_sent:
                        client.messages.create(
                            body="Alert: Yawning detected multiple times. Driver may be tired.",
                            from_=twilio_phone_number,
                            to=to_phone_number
                        )
                        yawn_sent = True
                        if yawn_count % 15 == 0 and not yawn_calls_sent:
                            client.calls.create(
                                url=yawning_call_url,
                                to=to_phone_number,
                                from_=twilio_phone_number
                            )
                            yawn_calls_sent = True
                else:
                    mouth_start = None

    # Hand detection
    if hands_res.multi_hand_landmarks:
        for hand_landmarks in hands_res.multi_hand_landmarks:
            for point in hand_landmarks.landmark:
                x, y = int(point.x * frame.shape[1]), int(point.y * frame.shape[0])
                cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)
            hands_face_dis = np.linalg.norm(np.array([x, y]) - np.array(landmarks[1]))
            if hands_face_dis < 80:
                cv2.putText(frame, 'Hands Too Close!', (270, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                speech("Hands too close to your face, please don't eat or do other things. Focus on driving.")
                cv2.putText(frame, f"hands: {hands_face_dis:.2f}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                hands_count += 1
            if hands_count % 5 == 0 and not hands_sent:
                client.messages.create(
                    body="Alert: Hands too close to face detected multiple times. Driver may be distracted.",
                    from_=twilio_phone_number,
                    to=to_phone_number
                )
                hands_sent = True
                if hands_count % 15 == 0 and not hands_calls_sent:
                    client.calls.create(
                        url=hands_call_url,
                        to=to_phone_number,
                        from_=twilio_phone_number
                    )
                    hands_calls_sent = True

    # Reset flags after each cycle to allow sending messages for the next 5 counts
    if drowsy_count % 5 == 0:
        drowsy_sent = False
    if yawn_count % 5 == 0:
        yawn_sent = False
    if hands_count % 5 == 0:
        hands_sent = False

    # Reset call flags after 15 events (3 * 5)
    if drowsy_count % 15 == 0:
        drowsy_calls_sent = False
    if yawn_count % 15 == 0:
        yawn_calls_sent = False
    if hands_count % 15 == 0:
        hands_calls_sent = False

    cv2.imshow('Driver Safety System', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()