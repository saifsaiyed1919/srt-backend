# firmware_tools/views.py
import os
import subprocess
import tempfile
import re
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status

# MONGODB MODEL IMPORT
from .models import FirmwareLog

def strip_ansi_codes(text):
    ansi_escape = re.compile(r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', text)

class MEAnalyzerAPIView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        bios_file = request.FILES.get('file')

        if not bios_file:
            return Response({"error": "No BIOS file provided"}, status=status.HTTP_400_BAD_REQUEST)

        size_bytes = bios_file.size
        size_kb = round(size_bytes / 1024, 2)
        size_mb = round(size_bytes / (1024 * 1024), 2)
        size_hex = hex(size_bytes).upper()

        temp_file_path = ""
        
        # Ab hum 'logs' array ki jagah 'parsed_data' array of objects bhejenge
        parsed_data = []
        error_logs = []

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as temp_file:
                for chunk in bios_file.chunks():
                    temp_file.write(chunk)
                temp_file_path = temp_file.name

            mea_executable_path = os.path.join(settings.BASE_DIR, 'firmware_tools', 'MEA.exe') 

            result = subprocess.run(
                [mea_executable_path, temp_file_path, "-skip", "-exit"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )

            raw_output = strip_ansi_codes(result.stdout)

            target_keys = [
                "Family", "Version", "Release", "Type", "SKU", "Chipset", 
                "File System State", "Production Ready", "Date", "Size", 
                "FWUpdate Support", "Chipset Support", "Latest"
            ]

            # Current section tracker (CSE ME, PMC, etc.)
            current_section = "General"

            for line in raw_output.split('\n'):
                # Jab bhi naya bada section aata hai (jaise Power Management Controller)
                if '║' in line and not '│' in line and len(line.strip()) > 5:
                    section_name = line.replace('║', '').strip()
                    if section_name not in ["ME Analyzer v1.96.4 r378", temp_file_path.split('\\')[-1], bios_file.name]:
                        current_section = section_name

                if '│' in line:
                    parts = line.split('│')
                    if len(parts) == 2:
                        key = parts[0].replace('║', '').strip()
                        value = parts[1].replace('║', '').strip()

                        if key in target_keys:
                            parsed_data.append({
                                "section": current_section,
                                "key": key,
                                "value": value
                            })

            if result.stderr:
                error_logs.extend([line.strip() for line in strip_ansi_codes(result.stderr).split('\n') if line.strip()])

            # ==========================================
            # MONGODB ME DATA SAVE KARNE KA JAADU 🔥
            # ==========================================
            # Agar koi error log hai toh status "Warnings", warna "Success"
            db_status = "Success" if len(error_logs) == 0 else "Processed with Warnings"
            
            new_log = FirmwareLog(
                file_name=bios_file.name,
                file_size_mb=size_mb,
                tool_used="ME Analyzer",
                status=db_status
            )
            new_log.save()  # <--- Ye line seedha aapke MongoDB Compass me data bhej degi!
            # ==========================================

        except Exception as e:
            error_logs.append(f"Backend Execution Error: {str(e)}")
        
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)

        return Response({
            "status": "success",
            "file_info": {
                "name": bios_file.name,
                "size_bytes": size_bytes,
                "size_kb": size_kb,
                "size_mb": size_mb,
                "size_hex": size_hex
            },
            "mea_data": parsed_data,
            "errors": error_logs
        }, status=status.HTTP_200_OK)


# firmware_tools/views.py (Sabse niche add karein)

class DashboardStatsAPIView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            # 1. MongoDB se data fetch karein (Latest pehle aayega, limit 10)
            recent_logs = FirmwareLog.objects.order_by('-created_at')[:10]
            
            # 2. Total Scans aur Success count nikalein
            total_scans = FirmwareLog.objects.count()
            success_scans = FirmwareLog.objects.filter(status="Success").count()
            
            # 3. Data ko frontend ke liye format karein
            logs_data = []
            for log in recent_logs:
                logs_data.append({
                    "id": str(log.id),
                    "file_name": log.file_name,
                    "file_size_mb": log.file_size_mb,
                    "tool_used": log.tool_used,
                    "status": log.status,
                    "created_at": log.created_at.strftime("%Y-%m-%d %H:%M")
                })
                
            return Response({
                "status": "success",
                "total_scans": total_scans,
                "success_scans": success_scans,
                "recent_logs": logs_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)