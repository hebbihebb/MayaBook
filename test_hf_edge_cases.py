
import sys
import os
import logging
import time
import soundfile as sf
import numpy as np
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.tts_maya1_hf import synthesize_chunk_hf

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def diagnose_audio(audio_path: str) -> dict:
    """Analyze audio file for basic quality metrics"""
    try:
        audio, sr = sf.read(audio_path)
        if audio.ndim > 1:
            audio = audio[:, 0]  # Take first channel if stereo

        rms = float(np.sqrt(np.mean(audio ** 2)))
        duration = len(audio) / sr
        peak = float(np.max(np.abs(audio)))
        
        return {
            'success': True,
            'duration': duration,
            'rms': rms,
            'peak': peak,
            'is_silent': rms < 1e-3,
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

def run_edge_case_tests():
    model_path = "assets/models/maya1_4bit_safetensor"
    voice = "A professional, clear female narrator."
    
    test_cases = [
        {
            "name": "Very Short Text",
            "text": "Hi.",
            "desc": "Tests minimum token generation limits."
        },
        {
            "name": "Special Characters",
            "text": "The price is $12.99 @ 50% off! #deal & *limited* time only.",
            "desc": "Tests symbol handling and tokenization."
        },
        {
            "name": "Heavy Emotion Tags",
            "text": "<laugh> That's so funny! <cry> But also sad. <angry> And now I'm mad! <whisper> Don't tell anyone.",
            "desc": "Tests stability with rapid emotion switching."
        },
        {
            "name": "Numbers and Dates",
            "text": "On January 1st, 2025, the ID was 1234-5678. The ratio is 1:5.",
            "desc": "Tests text normalization and number pronunciation."
        },
        {
            "name": "Technical Jargon",
            "text": "The API returned a 404 error because the JSON payload was malformed in the SQL query.",
            "desc": "Tests pronunciation of acronyms and technical terms."
        },
        {
            "name": "Repetitive Structure",
            "text": "Step one: check the logs. Step two: check the code. Step three: check the config. Step four: restart.",
            "desc": "Tests if repetition penalty triggers falsely on valid repetition."
        },
        {
            "name": "Long Sentence (No Punctuation)",
            "text": "This is a very long sentence that goes on and on without any commas or periods to see how the model handles breathing and pacing when there are no explicit pause markers in the text at all.",
            "desc": "Tests prosody and breath handling."
        }
    ]

    logger.info(f"Starting Edge Case Tests ({len(test_cases)} cases)")
    logger.info("=" * 60)

    results = []
    
    for i, case in enumerate(test_cases, 1):
        logger.info(f"Test {i}: {case['name']}")
        logger.info(f"  Desc: {case['desc']}")
        logger.info(f"  Text: {case['text'][:60]}...")
        
        start_time = time.time()
        try:
            output_path = synthesize_chunk_hf(
                model_path=model_path,
                text=case['text'],
                voice_description=voice,
                temperature=0.43,
                top_p=0.90,
                max_tokens=2500,
            )
            elapsed = time.time() - start_time
            
            diag = diagnose_audio(output_path)
            
            if diag['success']:
                status = "PASS"
                # Basic sanity checks
                if diag['is_silent']:
                    status = "FAIL (Silent)"
                elif diag['duration'] < 0.5:
                    status = "FAIL (Too Short)"
                elif diag['duration'] > 30.0 and len(case['text']) < 100:
                    status = "FAIL (Too Long/Looping)"
                
                logger.info(f"  Result: {status}")
                logger.info(f"  Time: {elapsed:.2f}s | Audio: {diag['duration']:.2f}s | RMS: {diag['rms']:.4f}")
                logger.info(f"  File: {output_path}")
                
                results.append({
                    "name": case['name'],
                    "status": status,
                    "duration": diag['duration'],
                    "file": output_path
                })
            else:
                logger.error(f"  Audio Diagnosis Failed: {diag['error']}")
                results.append({"name": case['name'], "status": "ERROR", "error": diag['error']})

        except Exception as e:
            logger.error(f"  Synthesis Failed: {e}")
            results.append({"name": case['name'], "status": "CRASH", "error": str(e)})
        
        logger.info("-" * 60)

    # Summary
    logger.info("Test Summary:")
    for r in results:
        status_icon = "✅" if r['status'] == "PASS" else "❌"
        logger.info(f"{status_icon} {r['name']:<30} {r['status']}")

if __name__ == "__main__":
    run_edge_case_tests()
