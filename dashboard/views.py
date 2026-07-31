from django.shortcuts import render
import csv
from django.http import HttpResponse
import json
from .api_service import SiKasepAPI
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
"""
from .models import (
    Citizens, Cadres, ScreeningSessions, ScreeningResults, MedicationLogs
)
"""

from django.shortcuts import render
import json
from .api_service import SiKasepAPI

from django.contrib.auth.models import User

def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard_home")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)
            return redirect("dashboard_home")

        messages.error(request, "Username atau password salah.")

    return render(request, "dashboard/login.html")

def signup_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard_home")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not username or not password:
            messages.error(request, "Username dan password wajib diisi.")
        elif password != confirm_password:
            messages.error(request, "Konfirmasi password tidak cocok.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username sudah digunakan, silakan pilih username lain.")
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            user.save()
            login(request, user)
            messages.success(request, "Pendaftaran berhasil! Anda telah masuk.")
            return redirect("dashboard_home")

    return render(request, "dashboard/signup.html")

def logout_view(request):
    logout(request)
    return redirect("login")


@login_required(login_url="login")
def dashboard_home(request):
    api = SiKasepAPI()

    context = {
        "total_warga": 0,
        "kader_aktif": 0,
        "positif": 0,
        "negatif": 0,
        "obat_hari_ini": 0,
        "total_wajib_obat": 0,
        "map_points": "[]",
        "warga_positif_list": []
    }
    # ===============================
    # DASHBOARD SUMMARY
    # ===============================
    summary = api.get_dashboard_summary()

    if summary:
        totals = summary.get("totals", {})
        context["total_warga"] = totals.get("citizens", 0)
        context["kader_aktif"] = totals.get("active_cadres", 0)
        context["positif"] = totals.get("positive_screenings", 0)
        context["negatif"] = totals.get("negative_screenings", 0)
        context["obat_hari_ini"] = totals.get("medication_reports_today", 0)
        context["total_wajib_obat"] = totals.get("screenings", 0)

    # ===============================
    # DATA SKRINING
    # ===============================
    if summary:
        maps = []
        warga = []

        for item in summary.get("mapPoints", []):
            lat = item.get("latitude")
            lng = item.get("longitude")

            if lat and lng:
                maps.append({
                    "nama": item.get("citizen_name"),
                    "lat": float(lat),
                    "lng": float(lng),
                    "status_risiko": item.get("result"),
                    "label": item.get("status_label")
                })

            if item.get("result") == "positive":
                warga.append({
                    "citizen_id": item.get("id"),
                    "name": item.get("citizen_name"),
                    "status_label": item.get("status_label"),
                    "date": item.get("screening_date"),
                    "lat": lat,
                    "lng": lng
                })

        context["map_points"] = json.dumps(maps)
        context["warga_positif_list"] = warga

    return render(
        request,
        "dashboard/home.html",
        context
    )

# 2. VIEW DATA WARGA YANG SUDAH DI SKRINING
@login_required(login_url="login")
def dashboard_citizens(request):
    api = SiKasepAPI()
    response = api.get_screenings()
    skrining_list = []

    # ==========================
    # Ambil data dari API
    # ==========================

    for item in response:
        skrining_list.append({
            "citizen_id": item.get("id"),
            "code": item.get("id"),
            "name": item.get("patientName") or item.get("name") or "Warga Adat",
            "officer": item.get("cadre") or item.get("cadreName") or item.get("officer") or "Kader PMO Adat",
            "score": item.get("bmi", "-"),
            "result": item.get("result"),
            "status_label": item.get("screeningStatus") or item.get("status_label") or ("Positif TBC" if item.get("result") == "positive" else "Sehat / Negatif"),
            "sync_status": item.get("sync_status") or item.get("syncStatus") or "Tersinkron",
            "factors": item.get("reasonSummary") or item.get("factors") or "Tidak ada gejala terekam",
            "recommendation": item.get("recommendation") or "Edukasi pencegahan rutin",
            "date": item.get("date") or item.get("screening_date") or "-",
            "region": item.get("region") or "Wilayah Baduy",
        })

    # ==========================
    # SEARCH
    # ==========================
    q = request.GET.get("q", "").strip()

    if q:
        skrining_list = [
            x for x in skrining_list
            if q.lower() in x["name"].lower()
        ]

    # ==========================
    # FILTER TANGGAL (SINGLE DATE)
    # ==========================
    search_date = request.GET.get("date", "").strip() or request.GET.get("start", "").strip()

    if search_date:
        skrining_list = [
            x for x in skrining_list
            if x["date"] == search_date
        ]

    # ==========================
    # EXPORT CSV
    # ==========================
    if request.GET.get("export") == "csv":

        response = HttpResponse(
            content_type="text/csv"
        )

        response["Content-Disposition"] = (
            'attachment; filename="data_skrining.csv"'
        )

        writer = csv.writer(response)

        writer.writerow([
            "ID",
            "Nama",
            "Tanggal",
            "Wilayah",
            "Status",
            "BMI",
            "Rekomendasi"
        ])

        for item in skrining_list:
            writer.writerow([
                item["citizen_id"],
                item["name"],
                item["date"],
                item["region"],
                item["status_label"],
                item["score"],
                item["recommendation"],
            ])

        return response
    return render(
        request,
        "dashboard/citizens.html",
        {
            "skrining_list": skrining_list,
            "search_q": q,
            "search_date": search_date,
        }
    )

@login_required(login_url="login")
def dashboard_reports(request):
    api = SiKasepAPI()

    summary = api.get_dashboard_summary()

    return render(
        request,
        "dashboard/reports.html",
        {
            "summary": summary,
            "regions": []
        }
    )
    
@login_required(login_url="login")
def export_screening_pdf(request):

    api = SiKasepAPI()

    params = {
        "periodStart": request.GET.get("start"),
        "periodEnd": request.GET.get("end"),
        "result": request.GET.get("result"),
        "regionId": request.GET.get("region"),
        "cadreId": request.GET.get("cadre"),
    }

    params = {k: v for k, v in params.items() if v}

    pdf = api.download_screening_pdf(params)

    if pdf is None:
        return HttpResponse(
            "Gagal membuat PDF.",
            status=500
        )

    response = HttpResponse(
        pdf,
        content_type="application/pdf"
    )

    response["Content-Disposition"] = (
        'attachment; filename="laporan_skrining.pdf"'
    )

    return response


import uuid
from django.utils import timezone
from django.utils.text import slugify
from django.core.files.storage import FileSystemStorage
from .models import EducationMaterials
from django.db.models import Q

@login_required(login_url="login")
def dashboard_education(request):
    materials = EducationMaterials.objects.filter(deleted_at__isnull=True).order_by('-created_at')
    
    total_materi = materials.count()
    aktif_count = materials.filter(status='published').count()
    draft_review_count = materials.filter(status__in=['draft', 'review']).count()
    
    media_tersedia_count = materials.filter(
        Q(youtube_url__gt='') | Q(image_path__gt='') | Q(video_url__gt='') | Q(audio_url__gt='')
    ).count()

    context = {
        'materials': materials,
        'total_materi': total_materi,
        'aktif_count': aktif_count,
        'draft_review_count': draft_review_count,
        'media_tersedia_count': media_tersedia_count,
    }
    return render(request, 'dashboard/education.html', context)


@login_required(login_url="login")
def add_education_material(request):
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        category = request.POST.get("category", "Edukasi").strip() or "Edukasi"
        summary = request.POST.get("summary", "").strip()
        
        type_input = request.POST.get("education_type", "youtube")
        type_mapping = {
            "Link YouTube": "youtube",
            "Artikel": "article",
            "PDF / Dokumen": "pdf",
            "Gambar": "image",
            "Video": "video",
            "youtube": "youtube",
            "article": "article",
            "pdf": "pdf",
            "image": "image",
            "video": "video"
        }
        education_type = type_mapping.get(type_input, "youtube")

        status_input = request.POST.get("status", "draft")
        status_mapping = {
            "Aktif": "published",
            "Review": "review",
            "Draft": "draft",
            "published": "published",
            "review": "review",
            "draft": "draft"
        }
        status = status_mapping.get(status_input, "draft")

        youtube_url = request.POST.get("youtube_url", "").strip()
        article_url = request.POST.get("article_url", "").strip()
        file_upload = request.FILES.get("file_upload")
        content = request.POST.get("content", "").strip()

        if youtube_url and not youtube_url.startswith(("http://", "https://")):
            youtube_url = "https://" + youtube_url
        if article_url and not article_url.startswith(("http://", "https://")):
            article_url = "https://" + article_url

        image_path = None
        video_url = None
        audio_url = None

        if file_upload:
            fs = FileSystemStorage(location='media/education_materials/', base_url='/media/education_materials/')
            filename = fs.save(f"{uuid.uuid4().hex[:8]}_{file_upload.name}", file_upload)
            relative_path = f"education_materials/{filename}"

            if education_type == 'image':
                image_path = relative_path
            elif education_type == 'video':
                video_url = relative_path
            else:
                audio_url = relative_path

        base_slug = slugify(title) if title else "materi-edukasi"
        slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"

        now = timezone.now()
        published_at = now if status == 'published' else None

        if title:
            item = EducationMaterials.objects.create(
                slug=slug,
                title=title,
                category=category,
                summary=summary,
                content=content or (article_url if education_type == 'article' else ''),
                education_type=education_type,
                youtube_url=youtube_url if education_type == 'youtube' else None,
                image_path=image_path,
                video_url=video_url,
                audio_url=audio_url,
                status=status,
                published_at=published_at,
                created_at=now,
                updated_at=now
            )
            messages.success(request, f"Materi edukasi '{item.title}' berhasil ditambahkan ke SI-KASEP (Status: {item.display_status})!")
        else:
            messages.error(request, "Judul materi tidak boleh kosong.")

    return redirect("dashboard_education")


@login_required(login_url="login")
def edit_education_material(request, material_id):
    if request.method == "POST":
        try:
            item = EducationMaterials.objects.get(id=material_id, deleted_at__isnull=True)
            title = request.POST.get("title", "").strip()
            category = request.POST.get("category", "Edukasi").strip() or "Edukasi"
            summary = request.POST.get("summary", "").strip()
            
            type_input = request.POST.get("education_type", "youtube")
            type_mapping = {
                "Link YouTube": "youtube", "Artikel": "article", "PDF / Dokumen": "pdf",
                "Gambar": "image", "Video": "video", "youtube": "youtube", "article": "article",
                "pdf": "pdf", "image": "image", "video": "video"
            }
            education_type = type_mapping.get(type_input, item.education_type)

            status_input = request.POST.get("status", "published")
            status_mapping = {
                "Aktif": "published", "Review": "review", "Draft": "draft",
                "published": "published", "review": "review", "draft": "draft"
            }
            status = status_mapping.get(status_input, "published")

            youtube_url = request.POST.get("youtube_url", "").strip()
            article_url = request.POST.get("article_url", "").strip()
            file_upload = request.FILES.get("file_upload")
            content = request.POST.get("content", "").strip()

            if youtube_url and not youtube_url.startswith(("http://", "https://")):
                youtube_url = "https://" + youtube_url
            if article_url and not article_url.startswith(("http://", "https://")):
                article_url = "https://" + article_url

            if title:
                item.title = title
                item.category = category
                item.summary = summary
                item.education_type = education_type
                item.status = status
                item.content = content or (article_url if education_type == 'article' else item.content)
                item.updated_at = timezone.now()

                if status == 'published' and not item.published_at:
                    item.published_at = timezone.now()

                if education_type == 'youtube':
                    item.youtube_url = youtube_url

                if file_upload:
                    fs = FileSystemStorage(location='media/education_materials/', base_url='/media/education_materials/')
                    filename = fs.save(f"{uuid.uuid4().hex[:8]}_{file_upload.name}", file_upload)
                    relative_path = f"education_materials/{filename}"

                    if education_type == 'image':
                        item.image_path = relative_path
                    elif education_type == 'video':
                        item.video_url = relative_path
                    else:
                        item.audio_url = relative_path

                item.save()
                messages.success(request, f"Materi edukasi '{item.title}' berhasil diperbarui (Status: {item.display_status})!")
            else:
                messages.error(request, "Judul materi tidak boleh kosong.")
        except EducationMaterials.DoesNotExist:
            messages.error(request, "Materi edukasi tidak ditemukan.")

    return redirect("dashboard_education")


@login_required(login_url="login")
def delete_education_material(request, material_id):
    if request.method == "POST":
        try:
            item = EducationMaterials.objects.get(id=material_id, deleted_at__isnull=True)
            title = item.title
            item.deleted_at = timezone.now()
            item.save()
            messages.success(request, f"Materi edukasi '{title}' berhasil dihapus.")
        except EducationMaterials.DoesNotExist:
            messages.error(request, "Materi edukasi tidak ditemukan.")

    return redirect("dashboard_education")



from .models import Kader

@login_required(login_url="login")
def dashboard_cadres(request):
    api = SiKasepAPI()
    api_cadres = api.get_cadres() or []
    local_cadres = list(Kader.objects.all())
    
    cadres_list = []
    
    # Process API cadres if available
    for item in api_cadres:
        cadres_list.append({
            "id": item.get("id"),
            "cadre_code": item.get("cadre_code") or f"KD-{item.get('id', '001')}",
            "name": item.get("name") or item.get("user", {}).get("name", "Kader Kesehatan"),
            "region": item.get("region_name") or item.get("assigned_area") or "Kawasan Baduy",
            "phone": item.get("phone") or item.get("user", {}).get("phone", "-"),
            "status": "Aktif" if item.get("active", 1) else "Non-Aktif",
            "screening_count": item.get("screening_count", 0),
            "last_active": item.get("updated_at") or "-",
            "is_local": False,
        })
        
    # Add local cadres
    for item in local_cadres:
        cadres_list.append({
            "id": item.id,
            "cadre_code": item.cadre_code,
            "name": item.name,
            "region": item.region,
            "phone": item.phone or "-",
            "status": item.status,
            "screening_count": item.screening_count,
            "last_active": item.last_active.strftime("%d %b %Y %H:%M") if item.last_active else "-",
            "is_local": True,
        })
        
    kader_aktif = sum(1 for c in cadres_list if c["status"] == "Aktif")
    total_wilayah = len(set(c["region"] for c in cadres_list if c.get("region")))
    total_catatan = sum(c["screening_count"] for c in cadres_list)
    tersimpan_lokal = len(local_cadres)

    context = {
        "cadres_list": cadres_list,
        "kader_aktif": kader_aktif,
        "total_wilayah": total_wilayah,
        "total_catatan": total_catatan,
        "tersimpan_lokal": tersimpan_lokal,
    }
    return render(request, "dashboard/cadres.html", context)


@login_required(login_url="login")
def add_cadre(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        cadre_code = request.POST.get("cadre_code", "").strip()
        region = request.POST.get("region", "").strip() or "Kawasan Baduy"
        phone = request.POST.get("phone", "").strip()
        status = request.POST.get("status", "Aktif")

        if not cadre_code:
            import random
            cadre_code = f"KD-{random.randint(100, 999)}"

        if name:
            if Kader.objects.filter(cadre_code=cadre_code).exists():
                messages.error(request, f"Kode kader '{cadre_code}' sudah digunakan.")
            else:
                item = Kader.objects.create(
                    cadre_code=cadre_code,
                    name=name,
                    region=region,
                    phone=phone,
                    status=status
                )
                messages.success(request, f"Kader '{item.name}' berhasil ditambahkan!")
        else:
            messages.error(request, "Nama kader wajib diisi.")

    return redirect("dashboard_cadres")


@login_required(login_url="login")
def edit_cadre(request, cadre_id):
    if request.method == "POST":
        try:
            item = Kader.objects.get(id=cadre_id)
            name = request.POST.get("name", "").strip()
            cadre_code = request.POST.get("cadre_code", "").strip()
            region = request.POST.get("region", "").strip() or "Kawasan Baduy"
            phone = request.POST.get("phone", "").strip()
            status = request.POST.get("status", "Aktif")

            if name:
                item.name = name
                if cadre_code:
                    item.cadre_code = cadre_code
                item.region = region
                item.phone = phone
                item.status = status
                item.save()
                messages.success(request, f"Data kader '{item.name}' berhasil diperbarui!")
            else:
                messages.error(request, "Nama kader wajib diisi.")
        except Kader.DoesNotExist:
            messages.error(request, "Data kader tidak ditemukan.")

    return redirect("dashboard_cadres")


@login_required(login_url="login")
def delete_cadre(request, cadre_id):
    if request.method == "POST":
        try:
            item = Kader.objects.get(id=cadre_id)
            name = item.name
            item.delete()
            messages.success(request, f"Data kader '{name}' berhasil dihapus.")
        except Kader.DoesNotExist:
            messages.error(request, "Data kader tidak ditemukan.")

    return redirect("dashboard_cadres")