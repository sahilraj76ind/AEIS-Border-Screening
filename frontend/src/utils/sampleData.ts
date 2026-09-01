// Generates realistic canvas sample documents for 1-click interactive demo presets

function createCanvasImage(
  title: string,
  docType: 'passport' | 'visa' | 'aadhaar' | 'selfie',
  mrzLines: string[],
  vizDetails: Record<string, string>,
  tamperWatermark?: string
): Promise<File> {
  return new Promise((resolve) => {
    const canvas = document.createElement('canvas');
    canvas.width = 800;
    canvas.height = 550;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Background base
    if (docType === 'passport') {
      ctx.fillStyle = '#1E293B';
      ctx.fillRect(0, 0, 800, 550);
      ctx.strokeStyle = 'rgba(6, 182, 212, 0.15)';
      ctx.lineWidth = 1;
      for (let i = 0; i < 800; i += 20) {
        ctx.beginPath();
        ctx.arc(i, 200, 150, 0, Math.PI);
        ctx.stroke();
      }
    } else if (docType === 'visa') {
      ctx.fillStyle = '#0F273B';
      ctx.fillRect(0, 0, 800, 550);
      ctx.strokeStyle = 'rgba(59, 130, 246, 0.15)';
      ctx.lineWidth = 1;
      for (let i = 0; i < 550; i += 25) {
        ctx.strokeRect(20, i, 760, 20);
      }
    } else if (docType === 'aadhaar') {
      ctx.fillStyle = '#1E1E2E';
      ctx.fillRect(0, 0, 800, 550);
      ctx.fillStyle = 'rgba(249, 115, 22, 0.3)';
      ctx.fillRect(0, 0, 800, 20);
      ctx.fillStyle = 'rgba(34, 197, 94, 0.3)';
      ctx.fillRect(0, 530, 800, 20);
    } else {
      ctx.fillStyle = '#0B1329';
      ctx.fillRect(0, 0, 800, 550);
    }

    // Border
    ctx.strokeStyle = '#06B6D4';
    ctx.lineWidth = 4;
    ctx.strokeRect(10, 10, 780, 530);

    // Title Header
    ctx.fillStyle = '#FFFFFF';
    ctx.font = 'bold 24px monospace';
    ctx.fillText(title.toUpperCase(), 40, 55);

    // Document Photo Placeholder
    ctx.fillStyle = '#334155';
    ctx.fillRect(40, 80, 180, 230);
    ctx.strokeStyle = '#64748B';
    ctx.lineWidth = 2;
    ctx.strokeRect(40, 80, 180, 230);

    // Silhouette
    ctx.fillStyle = '#94A3B8';
    ctx.beginPath();
    ctx.arc(130, 150, 45, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(130, 270, 70, Math.PI, 0);
    ctx.fill();

    // VIZ Details
    let yPos = 110;
    Object.entries(vizDetails).forEach(([k, v]) => {
      ctx.fillStyle = '#94A3B8';
      ctx.font = '12px monospace';
      ctx.fillText(k.toUpperCase(), 250, yPos);
      ctx.fillStyle = '#FFFFFF';
      ctx.font = 'bold 16px monospace';
      ctx.fillText(v, 250, yPos + 20);
      yPos += 45;
    });

    // Tamper watermark
    if (tamperWatermark) {
      ctx.save();
      ctx.translate(400, 275);
      ctx.rotate(-Math.PI / 8);
      ctx.fillStyle = 'rgba(239, 68, 68, 0.4)';
      ctx.font = 'bold 42px monospace';
      ctx.textAlign = 'center';
      ctx.fillText(tamperWatermark, 0, 0);
      ctx.restore();
    }

    // MRZ Zone
    if (mrzLines.length > 0) {
      ctx.fillStyle = 'rgba(0, 0, 0, 0.85)';
      ctx.fillRect(20, 390, 760, 130);
      ctx.strokeStyle = '#06B6D4';
      ctx.lineWidth = 1;
      ctx.strokeRect(20, 390, 760, 130);

      ctx.fillStyle = '#06B6D4';
      ctx.font = 'bold 22px monospace';
      mrzLines.forEach((line, idx) => {
        ctx.fillText(line, 40, 445 + idx * 40);
      });
    }

    canvas.toBlob((blob) => {
      if (blob) {
        const file = new File([blob], `${docType}_sample.jpg`, { type: 'image/jpeg' });
        resolve(file);
      }
    }, 'image/jpeg', 0.95);
  });
}

export const loadCleanTravelerPreset = async () => {
  const passport = await createCanvasImage(
    'Passport - Republic of Utopia',
    'passport',
    [
      'P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<',
      'A987654326UTO7408122F3401011ZE184226B<<<<<16'
    ],
    {
      'Surname': 'ERIKSSON',
      'Given Names': 'ANNA MARIA',
      'Passport No': 'A98765432',
      'Nationality': 'UTO',
      'Date of Birth': '12 AUG 1974',
      'Expiry': '01 JAN 2034'
    }
  );

  const visa = await createCanvasImage(
    'Border Entry Visa Permit',
    'visa',
    [
      'V<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<',
      'L8988901C4XXX7408128F9612109<<<<<<<6'
    ],
    {
      'Visa Holder': 'ERIKSSON, ANNA MARIA',
      'Visa Number': 'L8988901C4',
      'Class': 'TOURIST / B2',
      'Validity': 'SINGLE ENTRY - 90 DAYS'
    }
  );

  const selfie = await createCanvasImage(
    'Live Facial Portrait',
    'selfie',
    [],
    {
      'Subject': 'ANNA MARIA ERIKSSON',
      'Camera': 'Terminal 3 BioGate 04',
      'Liveness': '2 Verified Blinks confirmed'
    }
  );

  return { passport, visa, aadhaar: null, selfie };
};

export const loadFraudTamperedPreset = async () => {
  const passport = await createCanvasImage(
    'Passport - Tampered Substrate',
    'passport',
    [
      'P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<',
      'A987654326UTO7408122F3401011ZE184226B<<<<<16'
    ],
    {
      'Surname': 'SMITH (ALTERED)',
      'Given Names': 'JOHN FAKE',
      'Passport No': 'A98765432',
      'Nationality': 'UTO',
      'Date of Birth': '12 AUG 1974'
    },
    'DIGITAL SPLICING DETECTED'
  );

  const visa = await createCanvasImage(
    'Inconsistent Visa Permit',
    'visa',
    [
      'V<UTOSMITH<<JOHN<<<<<<<<<<<<<<<<<<<<',
      'V123456784USA9001018M2812319<<<<<<<6'
    ],
    {
      'Visa Holder': 'SMITH, JOHN',
      'Visa Number': 'V12345678',
      'Conflict': 'Name mismatch vs Passport'
    }
  );

  return { passport, visa, aadhaar: null, selfie: null };
};

export const loadInterpolWatchlistPreset = async () => {
  const passport = await createCanvasImage(
    'Passport - Stolen Blank Document',
    'passport',
    [
      'P<UTOSTOLEN<<TRAVELER<<<<<<<<<<<<<<<<<<<<<<<',
      'N876543210UTO8505151M3001015<<<<<<<<<<<<<<02'
    ],
    {
      'Surname': 'STOLEN',
      'Given Names': 'TRAVELER',
      'Passport No': 'N87654321 (INTERPOL HIT)',
      'Status': 'Reported lost in transit'
    },
    'INTERPOL SLTD ALERT'
  );

  return { passport, visa: null, aadhaar: null, selfie: null };
};

export const loadAadhaarPreset = async () => {
  const aadhaar = await createCanvasImage(
    'Government of India - Unique Identification Authority',
    'aadhaar',
    [],
    {
      'Holder Name': 'ANNA MARIA ERIKSSON',
      'Aadhaar UID': '2468 1357 9019',
      'Date of Birth': '12/08/1974',
      'Gender': 'Female',
      'Compliance': 'UIDAI Circular Comp/01/2018'
    }
  );

  return { passport: null, visa: null, aadhaar, selfie: null };
};
