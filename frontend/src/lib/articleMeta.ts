export type TimelineItem = { date: string; text: string };

export type ArticleMeta = {
  entity: string;
  aspect: string;
  timeline?: TimelineItem[];
};

export const articleMeta: Record<string, ArticleMeta> = {
  'agustus-2025-ai-uranus-dan-gelembung': {
    entity: 'Industri AI & Uranus',
    aspect: 'Saturnus–Neptunus',
    timeline: [
      { date: '19 Agustus', text: 'NASA mengumumkan satelit baru Uranus.' },
      { date: '21 Agustus', text: 'Studi MIT tentang hasil investasi AI ramai diberitakan.' }
    ]
  },
  'september-2025-kimmel-dan-siklus-24-tahun': {
    entity: 'Jimmy Kimmel',
    aspect: 'Uranus di Gemini · siklus Jupiter',
    timeline: [
      { date: '17 September', text: 'ABC menghentikan sementara Jimmy Kimmel Live.' },
      { date: '23 September', text: 'Program kembali mengudara.' }
    ]
  },
  'oktober-2025-pencurian-louvre': {
    entity: 'Museum Louvre',
    aspect: 'Merkurius–Mars di Scorpio'
  },
  'november-2025-cloudflare-dan-merkurius': {
    entity: 'Cloudflare',
    aspect: 'Merkurius retrograde ↔ Uranus'
  },
  'januari-2026-minneapolis-mars-pluto': {
    entity: 'Minneapolis',
    aspect: 'Mars–Pluto di Aquarius',
    timeline: [
      { date: '7 Januari', text: 'Renee Nicole Good meninggal dalam operasi imigrasi federal.' },
      { date: '24 Januari', text: 'Alex Pretti meninggal dalam insiden terpisah.' }
    ]
  },
  'februari-2026-super-bowl-bad-bunny': {
    entity: 'Bad Bunny & Puerto Riko',
    aspect: 'Saturnus–Neptunus'
  },
  'maret-2026-sora-ditutup': {
    entity: 'OpenAI Sora',
    aspect: 'Matahari–Saturnus',
    timeline: [
      { date: '24 Maret', text: 'OpenAI mengumumkan penghentian Sora.' },
      { date: '26 April', text: 'Aplikasi dan pengalaman web resmi ditutup.' }
    ]
  },
  'april-2026-percobaan-serangan-dan-uranus': {
    entity: 'Donald Trump',
    aspect: 'Uranus masuk Gemini'
  },
  'mei-2026-ledakan-pabrik-kembang-api': {
    entity: 'Pabrik kembang api',
    aspect: 'Mars □ Jupiter'
  },
  'juni-2026-gempa-venezuela': {
    entity: 'Venezuela',
    aspect: 'Mars–Uranus'
  },
  'juli-2026-lindsey-graham': {
    entity: 'Lindsey Graham',
    aspect: 'Mars–Uranus'
  }
};
