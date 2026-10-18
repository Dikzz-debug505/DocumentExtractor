# NovaDev Document Extractor (Vercel)

## Deploy ke Vercel

1. Push folder ini ke GitHub
2. Import project di [vercel.com](https://vercel.com)
3. Deploy

Atau via CLI:
```bash
npm i -g vercel
vercel
```

## Fitur
- Upload Document.unity3d
- Extract + zip
- MD5 + xxhash (pure Python) di setiap file + zip
- Design gelap bersih

## Catatan
- Cocok untuk file < ~50-80 MB (batas serverless)
- File temporary otomatis hilang setelah beberapa waktu
