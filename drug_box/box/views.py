# api/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import User, DosageSchedule, EventLog

def log_event(user, rfid_code, fingerprint_id, status_, message):
    EventLog.objects.create(
        event_type="Authentication",
        user=user,
        rfid_code=rfid_code,
        fingerprint_id=fingerprint_id,
        status=status_,
        message=message
    )

class HandleRequestAPIView(APIView):
    def post(self, request):
        rfid = request.data.get("rfid_code")
        fp = request.data.get("fingerprint_id")
        ts = request.data.get("timestamp")
        
        if not (rfid and fp and ts):
            log_event(None, rfid, fp, "Failed", "Missing required fields")
            return Response({"message":"Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(rfid_code=rfid)
        except User.DoesNotExist:
            log_event(None, rfid, fp, "Failed", "RFID not found")
            return Response({"message":"RFID not found"}, status=status.HTTP_404_NOT_FOUND)

        if user.fingerprint_id != int(fp):
            log_event(user, rfid, fp, "Failed", "Fingerprint mismatch")
            return Response({"message":"Fingerprint mismatch"}, status=status.HTTP_401_UNAUTHORIZED)

        date = ts.split("T")[0]
        try:
            dosage_obj = DosageSchedule.objects.get(user=user, date=date)
        except DosageSchedule.DoesNotExist:
            log_event(user, rfid, fp, "Failed", "No dosage for date")
            return Response({"message":"No dosage defined for the specified date"}, status=status.HTTP_403_FORBIDDEN)

        log_event(user, rfid, fp, "Success", "Authentication successful, dosage sent")
        return Response({
            "status":"success",
            "dosage": dosage_obj.dosage
        })

class AddUserFromDeviceAPIView(APIView):
    def post(self, request):
        rfid = request.data.get("rfid_code")
        fp = request.data.get("fingerprint_id")
        
        if not (rfid and fp):
            log_event(None, rfid, fp, "Failed", "Missing required fields for user creation")
            return Response({"message":"Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.create(name=None, rfid_code=rfid, fingerprint_id=fp)
        except Exception as e:
            log_event(None, rfid, fp, "Failed", str(e))
            return Response({"message":"RFID or fingerprint already exists"}, status=status.HTTP_400_BAD_REQUEST)

        log_event(user, rfid, fp, "Success", "User created by device")
        return Response({"status":"success","message":"User added successfully"}, status=status.HTTP_201_CREATED)
