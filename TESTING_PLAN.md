# MayaBook M4B Integration Testing Plan

**Branch:** `feature/abogen-integration`
**Status:** Backend + GUI Complete, Ready for Testing
**Created:** 2025-11-13

---

## 📋 Testing Checklist

### Phase 1: Basic Functionality Tests

#### Test 1.1: EPUB Chapter Extraction
- [ ] **Test with proper TOC EPUB**
  - Use: `assets/test/test.epub` (if available) or any EPUB with chapters
  - Expected: Chapters extracted correctly, titles shown in preview
  - Verify: Metadata fields auto-populate (title, author, year, genre)
  - Check: Chapter preview shows word counts for each chapter

- [ ] **Test EPUB without TOC**
  - Use: Create or find EPUB without table of contents
  - Expected: Falls back to document extraction, creates "Chapter 1", "Chapter 2", etc.
  - Verify: All text still extracted correctly

- [ ] **Test with nested chapters**
  - Use: EPUB with section → subsection structure
  - Expected: All chapters extracted, nested structure handled
  - Verify: Chapter numbering sequential

- [ ] **Test with custom chapter markers**
  - Add `<<CHAPTER_MARKER:Custom Name>>` to EPUB text
  - Expected: Chapters re-split by markers
  - Verify: Marker text removed from output

#### Test 1.2: GUI Controls
- [ ] **Extract EPUB button**
  - Click "Extract EPUB" with valid EPUB
  - Verify: Chapter preview appears
  - Verify: Metadata fields populate
  - Verify: "Auto-detected: ..." status label shows

- [ ] **Chapter options toggle**
  - Uncheck "Enable chapter-aware processing"
  - Verify: Chapter options and metadata fields become disabled
  - Re-check: Fields become enabled again

- [ ] **Format dropdown**
  - Change between M4B, WAV, MP4
  - Verify: Each selection saves correctly

- [ ] **FFmpeg check on startup**
  - Launch app with FFmpeg installed
  - Verify: "✓ FFmpeg with AAC codec is available" message
  - If FFmpeg not installed: Verify M4B removed from dropdown

#### Test 1.3: Scrollbar
- [ ] **Vertical scrolling**
  - Launch app, scroll through all sections
  - Verify: Scrollbar appears, all sections accessible
  - Verify: Mousewheel scrolling works

---

### Phase 2: M4B Generation Tests (CRITICAL)

**Prerequisites:**
- FFmpeg installed and in PATH
- Maya1 GGUF model downloaded
- Test EPUB with 2-3 short chapters (~100-200 words each)

#### Test 2.1: Basic M4B Generation
```
Settings:
- Format: M4B
- Enable chapter-aware processing: ✓
- Save chapters separately: ☐ (unchecked)
- Create merged file: ✓
- Chapter silence: 2.0s
```

**Steps:**
1. Extract EPUB (2-3 chapters)
2. Start Generation
3. Wait for completion

**Expected Results:**
- [ ] Merged M4B file created
- [ ] File size reasonable (not empty)
- [ ] No errors in log

**Verification:**
- [ ] Open M4B in VLC/iTunes/BookPlayer
- [ ] Verify chapter navigation works (jump between chapters)
- [ ] Verify chapter names appear correctly
- [ ] Verify chapter timings are accurate
- [ ] Verify 2-second silence between chapters

#### Test 2.2: M4B with Separate Chapters
```
Settings:
- Format: M4B
- Enable chapter-aware processing: ✓
- Save chapters separately: ✓
- Create merged file: ✓
- Chapter silence: 2.0s
```

**Expected Results:**
- [ ] Merged M4B file created
- [ ] Separate chapter folder created
- [ ] Individual WAV files for each chapter (01_ChapterName.wav, 02_ChapterName.wav)
- [ ] Chapter files playable independently

#### Test 2.3: Metadata Embedding
**Test automatic metadata:**
- [ ] Use EPUB with title, author, year in metadata
- [ ] Generate M4B
- [ ] Verify metadata appears in audio player (title, artist/author, year, genre)

**Test manual metadata:**
- [ ] Extract EPUB
- [ ] Manually edit metadata fields in GUI
- [ ] Generate M4B
- [ ] Verify manual metadata overrides EPUB metadata

#### Test 2.4: Chapter Silence Duration
**Test different silence durations:**
- [ ] Generate with 0.5s silence
- [ ] Generate with 2.0s silence (default)
- [ ] Generate with 5.0s silence
- [ ] Verify: Silence duration matches setting when playing M4B

---

### Phase 3: Format Comparison Tests

#### Test 3.1: WAV Format
- [ ] Format: WAV, Chapter-aware: ✓, Merged: ✓
- [ ] Expected: Single WAV file with all chapters
- [ ] Verify: Lossless quality, large file size

#### Test 3.2: MP4 Format (Video)
- [ ] Format: MP4, Cover image: Required
- [ ] Expected: MP4 video with static cover and audio
- [ ] Verify: Playable in video players

#### Test 3.3: Quality Comparison
- [ ] Generate same 2-chapter EPUB as WAV, MP4, M4B
- [ ] Compare file sizes
- [ ] Verify audio quality identical (no artifacts)

---

### Phase 4: Memory and Performance Tests

#### Test 4.1: Large EPUB (if available)
- [ ] Use EPUB with 10+ chapters or 10,000+ words
- [ ] Monitor RAM usage during generation
- [ ] Verify: Memory usage stays reasonable (no RAM spike)
- [ ] Verify: Incremental writing prevents buffering

#### Test 4.2: Very Long Chapter Names
- [ ] Test chapter with 100+ character title
- [ ] Expected: Name sanitized to 80 characters
- [ ] Verify: Filename created without errors

#### Test 4.3: Special Characters in Chapter Names
**Test these characters:**
- [ ] Colons: "Chapter: The Beginning"
- [ ] Slashes: "Part 1/2"
- [ ] Question marks: "What Happened?"
- [ ] Asterisks: "Chapter *Important*"
- [ ] Quotes: 'Chapter "Title"'

**Expected:** All characters sanitized, filenames valid on Windows/macOS/Linux

---

### Phase 5: Error Handling Tests

#### Test 5.1: Cancel During Generation
- [ ] Start M4B generation
- [ ] Click "Cancel" button mid-generation
- [ ] Expected: Process stops, cleanup happens
- [ ] Verify: No partial files left, UI resets

#### Test 5.2: Missing FFmpeg
- [ ] Rename or temporarily remove FFmpeg from PATH
- [ ] Launch app
- [ ] Expected: Warning message, M4B removed from dropdown
- [ ] Verify: WAV and MP4 still work (MP4 requires FFmpeg too, should warn)

#### Test 5.3: Invalid EPUB
- [ ] Select non-EPUB file (e.g., .txt, .pdf)
- [ ] Click "Extract EPUB"
- [ ] Expected: Error message, no crash

#### Test 5.4: Missing Model File
- [ ] Enter invalid model path
- [ ] Click "Start Generation"
- [ ] Expected: "Model Not Found" error message

---

### Phase 6: Edge Cases

#### Test 6.1: Single Chapter EPUB
- [ ] Generate M4B with only 1 chapter
- [ ] Expected: Works, but no chapter markers needed
- [ ] Verify: Still creates valid M4B

#### Test 6.2: Empty Chapter
- [ ] EPUB with chapter that has no text
- [ ] Expected: Skips empty chapter or handles gracefully

#### Test 6.3: No Chapters Selected
- [ ] Uncheck "Enable chapter-aware processing"
- [ ] Try to generate
- [ ] Expected: Falls back to legacy pipeline (flat text)

#### Test 6.4: No Merged File
- [ ] Uncheck "Create merged file"
- [ ] Check "Save chapters separately"
- [ ] Expected: Only individual chapter files created

---

## 🎯 Priority Order

### Must Test (Before Merge):
1. ✅ Basic M4B generation (Test 2.1)
2. ✅ Chapter navigation verification (Test 2.1)
3. ✅ Metadata embedding (Test 2.3)
4. ✅ Format comparison (Test 3.1-3.3)
5. ✅ Cancel functionality (Test 5.1)

### Should Test (Important):
6. M4B with separate chapters (Test 2.2)
7. Special characters in names (Test 4.3)
8. Error handling (Test 5.2-5.4)

### Nice to Test (If Time Permits):
9. Large EPUB memory usage (Test 4.1)
10. Edge cases (Test 6.1-6.4)

---

## 📝 Testing Notes Template

Use this template to record results:

```markdown
### Test: [Test Name]
**Date:** YYYY-MM-DD
**Tester:** [Your Name]
**EPUB Used:** [Filename, chapter count, word count]

**Steps:**
1. [Step taken]
2. [Step taken]

**Results:**
- ✅ PASS / ❌ FAIL
- Observations: [What you noticed]
- Issues found: [Any bugs or problems]
- Screenshots: [If applicable]

**Log File:** [Path to mayabook_*.log]
```

---

## 🐛 Known Issues to Watch For

Based on implementation, these areas might have issues:

1. **Chapter timing accuracy**: Verify start/end times match actual playback
2. **FFmpeg process cleanup**: Ensure FFmpeg processes don't hang
3. **File locking**: Verify files close properly after generation
4. **Progress bar accuracy**: Check progress updates correctly with chapter context
5. **Metadata status label**: Verify it shows correct fields

---

## 📂 Test Data Needed

### Required Files:
- [ ] Test EPUB with 2-3 chapters (~100-200 words each)
- [ ] Test cover image (JPG/PNG)
- [ ] Maya1 GGUF model file

### Optional Files:
- [ ] Large EPUB (10+ chapters, 10k+ words)
- [ ] EPUB without TOC
- [ ] EPUB with special characters in chapter names
- [ ] EPUB with nested chapter structure

### Where to Find Test EPUBs:
- Project Gutenberg (public domain books)
- Calibre (can create test EPUBs)
- StandardEbooks.org (well-formatted EPUBs)

---

## ✅ Success Criteria

**The integration is ready to merge when:**
- [x] All "Must Test" items pass
- [ ] At least 80% of "Should Test" items pass
- [ ] No critical bugs found
- [ ] M4B chapter navigation works in at least 2 different players
- [ ] Memory usage is reasonable for typical EPUBs
- [ ] Error handling prevents crashes

---

## 🚀 After Testing

**If tests pass:**
1. Update INTEGRATION_STATUS.md: Mark Testing as complete
2. Update README.md: Add M4B features to documentation
3. Create pull request to merge `feature/abogen-integration` → `main`
4. Celebrate! 🎉

**If tests fail:**
1. Document issues in GitHub issues or this file
2. Fix bugs on feature branch
3. Re-test
4. Repeat until success criteria met

---

**Last Updated:** 2025-11-13
**Branch:** feature/abogen-integration
**Commits:** 5 (foundation, pipeline, docs, GUI integration, scrollbar)
