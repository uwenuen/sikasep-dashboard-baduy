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
    start = request.GET.get("start", "").strip()
    end = request.GET.get("end", "").strip()
    res_filter = request.GET.get("result", "").strip()
    region_filter = request.GET.get("region", "").strip()

    sessions = ScreeningSessions.objects.select_related(
        'citizen', 'cadre__user', 'screeningresults'
    ).filter(deleted_at__isnull=True).order_by('-screening_date')

    if start:
        sessions = sessions.filter(screening_date__gte=start)
    if end:
        sessions = sessions.filter(screening_date__lte=end)
    if region_filter:
        sessions = sessions.filter(
            Q(citizen__region__name__icontains=region_filter) |
            Q(cadre__region__name__icontains=region_filter)
        )
    if res_filter:
        sessions = sessions.filter(screeningresults__result=res_filter)

    report_list = []
    for s in sessions:
        res = getattr(s, 'screeningresults', None)
        res_code = res.result if res else 'negative'
        res_label = res.status_label if res else ("Positif TBC" if res_code == 'positive' else "Sehat / Negatif")
        
        ref = Referrals.objects.filter(
            Q(screening=s) | Q(citizen=s.citizen),
            deleted_at__isnull=True
        ).first()

        status_rujukan = "Sudah" if ref else "Belum"
        if ref and ref.status == 'completed':
            status_rujukan = "Sudah (Selesai)"
        elif ref and ref.status == 'scheduled':
            status_rujukan = "Sudah (Terjadwal)"

        report_list.append({
            "date": s.screening_date.strftime("%d/%m/%Y") if s.screening_date else "-",
            "citizen_name": s.citizen.name if s.citizen else "Warga Adat",
            "region": s.citizen.region.name if (s.citizen and s.citizen.region) else "Wilayah Baduy",
            "cadre_name": s.cadre.user.name if (s.cadre and s.cadre.user) else "Kader PMO",
            "result_label": res_label,
            "result_code": res_code,
            "referral_status": status_rujukan,
        })

    # Export CSV Handler
    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="laporan_skrining.csv"'
        writer = csv.writer(response)
        writer.writerow(["Tanggal", "Nama Warga", "Wilayah", "Kader", "Hasil", "Status Rujukan"])
        for item in report_list:
            writer.writerow([
                item["date"],
                item["citizen_name"],
                item["region"],
                item["cadre_name"],
                item["result_label"],
                item["referral_status"],
            ])
        return response

    total_skrining = len(report_list)
    total_positif = sum(1 for item in report_list if item["result_code"] == 'positive')
    total_negatif = sum(1 for item in report_list if item["result_code"] == 'negative')
    total_rujukan = sum(1 for item in report_list if item["referral_status"] != 'Belum')

    summary = {
        "totals": {
            "screenings": total_skrining,
            "positive_screenings": total_positif,
            "negative_screenings": total_negatif,
            "referrals": total_rujukan,
        }
    }

    all_regions = Regions.objects.filter(deleted_at__isnull=True).values_list('name', flat=True)

    return render(
        request,
        "dashboard/reports.html",
        {
            "summary": summary,
            "report_list": report_list,
            "regions": list(all_regions),
        }
    )


def format_indo_date(date_str):
    if not date_str or date_str in ["-", "None", ""]:
        return "Semua Waktu"
    try:
        months = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", 
                  "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
        dt = timezone.datetime.strptime(date_str, "%Y-%m-%d")
        return f"{dt.day} {months[dt.month]} {dt.year}"
    except Exception:
        return date_str


@login_required(login_url="login")
def export_screening_pdf(request):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
    )

    styles = getSampleStyleSheet()

    header_style = ParagraphStyle(
        'OfficialHeader',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=colors.HexColor('#000000'),
        alignment=1
    )
    sub_header_style = ParagraphStyle(
        'OfficialSubHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#0c2335'),
        alignment=1
    )
    puskesmas_style = ParagraphStyle(
        'PuskesmasHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#334155'),
        alignment=1
    )
    
    meta_label_style = ParagraphStyle(
        'MetaLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#000000')
    )
    meta_colon_style = ParagraphStyle(
        'MetaColon',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#000000'),
        alignment=1
    )
    meta_val_style = ParagraphStyle(
        'MetaVal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#000000')
    )

    stat_cell_style = ParagraphStyle(
        'StatCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#000000')
    )

    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#1e293b')
    )
    
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#000000'),
        alignment=1
    )

    cell_style = ParagraphStyle(
        'CellText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#000000')
    )
    
    footer_style = ParagraphStyle(
        'DocFooter',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#475569'),
        alignment=1
    )

    elements = []

    # 1. Header & Kop Dokumen
    elements.append(Paragraph("LAPORAN HASIL SKRINING", header_style))
    elements.append(Spacer(1, 2))
    elements.append(Paragraph("SISTEM INFORMASI PENCEGAHAN TBC (SI-KASEP BADUY)", sub_header_style))
    elements.append(Spacer(1, 2))
    elements.append(Paragraph("Puskesmas Cisimeut - Kabupaten Lebak", puskesmas_style))
    elements.append(Spacer(1, 10))

    # 2. Blok Identitas Laporan (Rata Kiri Vertikal Table)
    months_indo = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", 
                   "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    now = timezone.now()
    now_str = f"{now.day} {months_indo[now.month]} {now.year} {now.strftime('%H:%M')}"

    start_raw = request.GET.get("start", "").strip()
    end_raw = request.GET.get("end", "").strip()

    if start_raw and end_raw:
        periode_val = f"{format_indo_date(start_raw)} – {format_indo_date(end_raw)}"
    elif start_raw:
        periode_val = f"Mulai {format_indo_date(start_raw)}"
    elif end_raw:
        periode_val = f"Sampai {format_indo_date(end_raw)}"
    else:
        periode_val = "Semua Waktu"

    region_raw = request.GET.get("region", "").strip()
    wilayah_val = region_raw if region_raw else "Semua Wilayah"
    petugas_val = "Semua Kader"

    meta_rows = [
        [Paragraph("Tanggal Cetak", meta_label_style), Paragraph(":", meta_colon_style), Paragraph(now_str, meta_val_style)],
        [Paragraph("Periode", meta_label_style), Paragraph(":", meta_colon_style), Paragraph(periode_val, meta_val_style)],
        [Paragraph("Wilayah", meta_label_style), Paragraph(":", meta_colon_style), Paragraph(wilayah_val, meta_val_style)],
        [Paragraph("Petugas", meta_label_style), Paragraph(":", meta_colon_style), Paragraph(petugas_val, meta_val_style)],
    ]
    meta_table = Table(meta_rows, colWidths=[90, 15, 435])
    meta_table.setStyle(TableStyle([
        ('PADDING', (0, 0), (-1, -1), 1.5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 10))

    # Fetch Data
    sessions = ScreeningSessions.objects.select_related(
        'citizen', 'cadre__user', 'screeningresults'
    ).filter(deleted_at__isnull=True).order_by('-screening_date')

    if start_raw:
        sessions = sessions.filter(screening_date__gte=start_raw)
    if end_raw:
        sessions = sessions.filter(screening_date__lte=end_raw)
    if region_raw:
        sessions = sessions.filter(
            Q(citizen__region__name__icontains=region_raw) |
            Q(cadre__region__name__icontains=region_raw)
        )

    res_filter = request.GET.get("result", "").strip()
    if res_filter:
        sessions = sessions.filter(screeningresults__result=res_filter)

    report_items = []
    for s in sessions:
        res = getattr(s, 'screeningresults', None)
        res_code = res.result if res else 'negative'
        res_label = res.status_label if res else ("Positif TBC" if res_code == 'positive' else "Sehat / Negatif")
        ref = Referrals.objects.filter(Q(screening=s) | Q(citizen=s.citizen), deleted_at__isnull=True).first()
        status_rujukan = "Sudah" if ref else "Belum"
        nik_code = s.citizen.nik if (s.citizen and s.citizen.nik) else f"SB-{s.citizen.id if s.citizen else s.id}"

        report_items.append({
            "date": s.screening_date.strftime("%d/%m/%Y") if s.screening_date else "-",
            "citizen_name": s.citizen.name if s.citizen else "Warga Adat",
            "nik": nik_code,
            "region": s.citizen.region.name if (s.citizen and s.citizen.region) else "Wilayah Baduy",
            "cadre_name": s.cadre.user.name if (s.cadre and s.cadre.user) else "Kader PMO",
            "result_label": res_label,
            "result_code": res_code,
            "referral_status": status_rujukan
        })

    tot_skrining = len(report_items)
    tot_positif = sum(1 for x in report_items if x["result_code"] == 'positive')
    tot_negatif = sum(1 for x in report_items if x["result_code"] == 'negative')
    tot_rujukan = sum(1 for x in report_items if x["referral_status"] != 'Belum')

    # 3. Ringkasan Statistik Formal (Dua Garis Pembatas Tipis Atas-Bawah)
    stat_data = [
        [
            Paragraph(f"<b>Total Skrining :</b> {tot_skrining}", stat_cell_style),
            Paragraph(f"<b>Positif :</b> {tot_positif}", stat_cell_style),
            Paragraph(f"<b>Negatif :</b> {tot_negatif}", stat_cell_style),
            Paragraph(f"<b>Rujukan :</b> {tot_rujukan}", stat_cell_style),
        ]
    ]
    stat_table = Table(stat_data, colWidths=[135, 135, 135, 135])
    stat_table.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, -1), 1, colors.HexColor('#475569')),
        ('LINEBELOW', (0, 0), (-1, -1), 1, colors.HexColor('#475569')),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]))
    elements.append(stat_table)
    elements.append(Spacer(1, 10))

    # 4. Paragraf Pengantar Ringkasan (Sebelum Tabel)
    elements.append(Paragraph("<b>Ringkasan</b>", body_style))
    elements.append(Spacer(1, 2))
    elements.append(Paragraph(
        "Laporan ini menyajikan hasil skrining Tuberkulosis berdasarkan data yang tercatat "
        "pada Sistem Informasi Pencegahan TBC (SI-KASEP) sesuai periode dan wilayah yang dipilih.",
        body_style
    ))
    elements.append(Spacer(1, 10))

    # 5. Tabel 8 Kolom Presisi (Black-and-White Friendly)
    headers = [
        Paragraph("<b>No</b>", table_header_style),
        Paragraph("<b>Tanggal Skrining</b>", table_header_style),
        Paragraph("<b>Nama Warga</b>", table_header_style),
        Paragraph("<b>NIK</b>", table_header_style),
        Paragraph("<b>Wilayah</b>", table_header_style),
        Paragraph("<b>Kader</b>", table_header_style),
        Paragraph("<b>Hasil Skrining</b>", table_header_style),
        Paragraph("<b>Status Rujukan</b>", table_header_style),
    ]
    table_data = [headers]

    for idx, item in enumerate(report_items, start=1):
        table_data.append([
            Paragraph(str(idx), cell_style),
            Paragraph(item["date"], cell_style),
            Paragraph(item["citizen_name"], cell_style),
            Paragraph(item["nik"], cell_style),
            Paragraph(item["region"], cell_style),
            Paragraph(item["cadre_name"], cell_style),
            Paragraph(item["result_label"], cell_style),
            Paragraph(item["referral_status"], cell_style),
        ])

    data_table = Table(table_data, colWidths=[22, 62, 100, 75, 80, 75, 66, 60])
    data_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#94a3b8')),
        ('PADDING', (0, 0), (-1, -1), 4.5),
    ]))
    elements.append(data_table)
    elements.append(Spacer(1, 16))

    # 6. Footer Resmi
    elements.append(Paragraph("Dokumen ini dihasilkan otomatis oleh Sistem Informasi Pencegahan TBC (SI-KASEP).", footer_style))

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="laporan_skrining_puskesmas_cisimeut.pdf"'
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