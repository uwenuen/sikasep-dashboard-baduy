from django.shortcuts import render, redirect
import csv
import json
import io
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Max, Count, Q
from django.utils import timezone
from django.utils.text import slugify
from django.core.files.storage import FileSystemStorage

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from .models import (
    Citizens, Cadres, ScreeningSessions, ScreeningResults,
    Referrals, Regions, EducationMaterials, Kader
)

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
    # Total warga unik yang sudah pernah melakukan skrining
    total_warga = ScreeningSessions.objects.filter(
        deleted_at__isnull=True
    ).values('citizen_id').distinct().count()

    # Kader Aktif
    kader_aktif = Cadres.objects.filter(
        active=1, deleted_at__isnull=True
    ).count()

    # Hasil Positif & Negatif
    positif = ScreeningResults.objects.filter(
        result='positive',
        screening__deleted_at__isnull=True
    ).count()

    negatif = ScreeningResults.objects.filter(
        result='negative',
        screening__deleted_at__isnull=True
    ).count()

    # Data Peta & Warga Positif
    sessions = ScreeningSessions.objects.select_related(
        'citizen', 'cadre__user', 'screeningresults'
    ).filter(deleted_at__isnull=True)

    maps = []
    warga_positif_list = []

    for s in sessions:
        lat = s.latitude
        lng = s.longitude
        
        result_obj = getattr(s, 'screeningresults', None)
        res_code = result_obj.result if result_obj else 'negative'
        label = result_obj.status_label if result_obj else 'Sehat / Negatif'

        if lat and lng:
            maps.append({
                "nama": s.citizen.name if s.citizen else "Warga",
                "lat": float(lat),
                "lng": float(lng),
                "status_risiko": res_code,
                "label": label
            })

        if res_code == 'positive':
            warga_positif_list.append({
                "citizen_id": s.citizen.id if s.citizen else s.id,
                "name": s.citizen.name if s.citizen else "Warga Adat",
                "status_label": label,
                "date": s.screening_date,
                "lat": float(lat) if lat else -6.6120,
                "lng": float(lng) if lng else 106.2230
            })

    context = {
        "total_warga": total_warga,
        "kader_aktif": kader_aktif,
        "positif": positif,
        "negatif": negatif,
        "obat_hari_ini": 0,
        "total_wajib_obat": total_warga,
        "map_points": json.dumps(maps),
        "warga_positif_list": warga_positif_list
    }

    return render(
        request,
        "dashboard/home.html",
        context
    )


@login_required(login_url="login")
def dashboard_citizens(request):
    sessions = ScreeningSessions.objects.select_related(
        'citizen', 'cadre__user', 'screeningresults'
    ).filter(deleted_at__isnull=True).order_by('-screening_date')

    q = request.GET.get("q", "").strip()
    if q:
        sessions = sessions.filter(citizen__name__icontains=q)

    search_date = request.GET.get("date", "").strip() or request.GET.get("start", "").strip()
    if search_date:
        sessions = sessions.filter(screening_date=search_date)

    skrining_list = []
    for s in sessions:
        res = getattr(s, 'screeningresults', None)
        skrining_list.append({
            "citizen_id": s.citizen.id if s.citizen else s.id,
            "code": s.code or f"SCR-{s.id}",
            "name": s.citizen.name if s.citizen else "Warga Adat",
            "officer": s.cadre.user.name if (s.cadre and s.cadre.user) else "Kader PMO Adat",
            "score": res.score if res else "-",
            "result": res.result if res else "negative",
            "status_label": res.status_label if res else "Sehat / Negatif",
            "sync_status": s.sync_status or "Tersinkron",
            "factors": res.reason_summary if (res and res.reason_summary) else "Tidak ada gejala terekam",
            "recommendation": res.recommendation if (res and res.recommendation) else "Edukasi pencegahan rutin",
            "date": str(s.screening_date),
            "region": (s.citizen.region.name if (s.citizen and s.citizen.region) else "Wilayah Baduy"),
        })

    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="data_skrining.csv"'
        writer = csv.writer(response)
        writer.writerow(["ID", "Nama", "Tanggal", "Wilayah", "Status", "BMI", "Rekomendasi"])
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
    total_skrining = ScreeningSessions.objects.filter(deleted_at__isnull=True).count()
    total_positif = ScreeningResults.objects.filter(result='positive', screening__deleted_at__isnull=True).count()
    total_rujukan = Referrals.objects.filter(deleted_at__isnull=True).count()
    total_kader = Cadres.objects.filter(active=1, deleted_at__isnull=True).count()

    summary = {
        "totals": {
            "screenings": total_skrining,
            "positive_screenings": total_positif,
            "referrals": total_rujukan,
            "active_cadres": total_kader
        }
    }

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
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#0c2335'),
        alignment=1
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#64748b'),
        alignment=1
    )
    cell_style = ParagraphStyle(
        'CellText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12
    )

    elements = []

    # Title & Subtitle
    elements.append(Paragraph("LAPORAN PENCEGAHAN TUBERKULOSIS (SI-KASEP BADUY)", title_style))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(f"Tanggal Cetak: {timezone.now().strftime('%d %B %Y %H:%M')}", subtitle_style))
    elements.append(Spacer(1, 14))

    # Ringkasan Statistik Box
    total_skrining = ScreeningSessions.objects.filter(deleted_at__isnull=True).count()
    total_positif = ScreeningResults.objects.filter(result='positive', screening__deleted_at__isnull=True).count()
    total_negatif = ScreeningResults.objects.filter(result='negative', screening__deleted_at__isnull=True).count()
    total_rujukan = Referrals.objects.filter(deleted_at__isnull=True).count()

    stat_data = [
        [
            Paragraph(f"<b>Total Skrining:</b> {total_skrining}", cell_style),
            Paragraph(f"<b>Hasil Positif:</b> {total_positif}", cell_style),
            Paragraph(f"<b>Hasil Negatif:</b> {total_negatif}", cell_style),
            Paragraph(f"<b>Total Rujukan:</b> {total_rujukan}", cell_style),
        ]
    ]
    stat_table = Table(stat_data, colWidths=[135, 135, 135, 135])
    stat_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(stat_table)
    elements.append(Spacer(1, 14))

    # Tabel Data
    headers = [
        Paragraph("<b>No</b>", cell_style),
        Paragraph("<b>Nama Warga</b>", cell_style),
        Paragraph("<b>Tanggal</b>", cell_style),
        Paragraph("<b>Petugas / Kader</b>", cell_style),
        Paragraph("<b>Hasil Skrining</b>", cell_style),
    ]
    table_data = [headers]

    sessions = ScreeningSessions.objects.select_related(
        'citizen', 'cadre__user', 'screeningresults'
    ).filter(deleted_at__isnull=True).order_by('-screening_date')[:50]

    for idx, s in enumerate(sessions, start=1):
        res = getattr(s, 'screeningresults', None)
        lbl = res.status_label if res else ("Positif TBC" if (res and res.result == 'positive') else "Sehat / Negatif")
        name = s.citizen.name if s.citizen else "Warga Adat"
        officer = s.cadre.user.name if (s.cadre and s.cadre.user) else "Kader PMO"
        date_str = str(s.screening_date)

        table_data.append([
            Paragraph(str(idx), cell_style),
            Paragraph(name, cell_style),
            Paragraph(date_str, cell_style),
            Paragraph(officer, cell_style),
            Paragraph(lbl, cell_style),
        ])

    data_table = Table(table_data, colWidths=[30, 150, 80, 140, 140])
    data_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0c2335')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(data_table)

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="laporan_skrining.pdf"'
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
        Q(youtube_url__gt='') | Q(image_path__gt='')
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
            "Gambar": "image",
            "youtube": "youtube",
            "image": "image"
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
        file_upload = request.FILES.get("file_upload")
        content = request.POST.get("content", "").strip()

        if youtube_url and not youtube_url.startswith(("http://", "https://")):
            youtube_url = "https://" + youtube_url

        image_path = None

        if file_upload and education_type == 'image':
            fs = FileSystemStorage(location='media/education_materials/', base_url='/media/education_materials/')
            filename = fs.save(f"{uuid.uuid4().hex[:8]}_{file_upload.name}", file_upload)
            image_path = f"education_materials/{filename}"

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
                content=content,
                education_type=education_type,
                youtube_url=youtube_url if education_type == 'youtube' else None,
                image_path=image_path if education_type == 'image' else None,
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
                "Link YouTube": "youtube", "Gambar": "image",
                "youtube": "youtube", "image": "image"
            }
            education_type = type_mapping.get(type_input, item.education_type)

            status_input = request.POST.get("status", "published")
            status_mapping = {
                "Aktif": "published", "Review": "review", "Draft": "draft",
                "published": "published", "review": "review", "draft": "draft"
            }
            status = status_mapping.get(status_input, "published")

            youtube_url = request.POST.get("youtube_url", "").strip()
            file_upload = request.FILES.get("file_upload")
            content = request.POST.get("content", "").strip()

            if youtube_url and not youtube_url.startswith(("http://", "https://")):
                youtube_url = "https://" + youtube_url

            if title:
                item.title = title
                item.category = category
                item.summary = summary
                item.education_type = education_type
                item.status = status
                item.content = content
                item.updated_at = timezone.now()

                if status == 'published' and not item.published_at:
                    item.published_at = timezone.now()

                if education_type == 'youtube':
                    item.youtube_url = youtube_url
                    item.image_path = None
                elif education_type == 'image':
                    item.youtube_url = None
                    if file_upload:
                        fs = FileSystemStorage(location='media/education_materials/', base_url='/media/education_materials/')
                        filename = fs.save(f"{uuid.uuid4().hex[:8]}_{file_upload.name}", file_upload)
                        item.image_path = f"education_materials/{filename}"

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
    cadres = Cadres.objects.select_related('user', 'region').filter(deleted_at__isnull=True)
    
    cadres_list = []
    for c in cadres:
        s_count = ScreeningSessions.objects.filter(cadre=c, deleted_at__isnull=True).count()
        last_s = ScreeningSessions.objects.filter(cadre=c, deleted_at__isnull=True).aggregate(latest=Max('screening_date'))['latest']
        
        region_name = c.region.name if c.region else (c.assigned_area or "Kawasan Baduy")
        user_name = c.user.name if (c.user and c.user.name) else f"Kader {c.cadre_code}"
        user_phone = c.user.phone if (c.user and c.user.phone) else "-"
        
        cadres_list.append({
            "id": c.id,
            "cadre_code": c.cadre_code,
            "name": user_name,
            "region": region_name,
            "phone": user_phone,
            "status": "Aktif" if c.active == 1 else "Non-Aktif",
            "screening_count": s_count,
            "last_active": last_s.strftime("%d %b %Y") if last_s else "-",
            "is_local": False,
        })
        
    kader_aktif = sum(1 for c in cadres_list if c["status"] == "Aktif")
    total_wilayah = len(set(c["region"] for c in cadres_list if c.get("region")))
    total_catatan = sum(c["screening_count"] for c in cadres_list)

    context = {
        "cadres_list": cadres_list,
        "kader_aktif": kader_aktif,
        "total_wilayah": total_wilayah,
        "total_catatan": total_catatan,
        "tersimpan_lokal": len(cadres_list),
    }
    return render(request, "dashboard/cadres.html", context)


@login_required(login_url="login")
def dashboard_referrals(request):
    referrals = Referrals.objects.select_related(
        'citizen', 'screening', 'created_by_user'
    ).filter(deleted_at__isnull=True).order_by('-created_at')

    q = request.GET.get("q", "").strip()
    if q:
        referrals = referrals.filter(
            Q(referral_code__icontains=q) |
            Q(citizen__name__icontains=q) |
            Q(destination__icontains=q)
        )

    status_filter = request.GET.get("status", "").strip()
    if status_filter:
        referrals = referrals.filter(status=status_filter)

    context = {
        "referrals": referrals,
        "search_q": q,
        "status_filter": status_filter,
    }
    return render(request, "dashboard/referrals.html", context)


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