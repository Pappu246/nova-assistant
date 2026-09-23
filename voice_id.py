"""
NOVA Voice ID v3 - speechbrain ECAPA.
"""
import os
import pickle
import numpy as np

try:
    import torch
    from speechbrain.inference.speaker import EncoderClassifier
    _SB = True
except Exception as e:
    print(f"[voice_id] speechbrain import fail: {e}")
    _SB = False

VOICE_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "boss_voice.pkl")
_classifier = None


def get_classifier():
    global _classifier
    if _classifier is None and _SB:
        try:
            print("[voice_id] Model load ho raha hai...")
            _classifier = EncoderClassifier.from_hparams(
                source="speechbrain/spkrec-ecapa-voxceleb",
                savedir=os.path.join(
                    os.path.expanduser("~"),
                    "AppData", "Local", "nova_speechbrain"
                ),
                run_opts={"device": "cpu"},
            )
            print("[voice_id] Ready")
        except Exception as e:
            print(f"[voice_id] load fail: {e}")
    return _classifier


def _embed(audio_np, sample_rate=16000):
    clf = get_classifier()
    if clf is None:
        return None
    audio_float = audio_np.astype(np.float32) / 32768.0
    if len(audio_float.shape) > 1:
        audio_float = audio_float.flatten()
    try:
        wav = torch.from_numpy(audio_float).unsqueeze(0)
        emb = clf.encode_batch(wav)
        return emb.squeeze().detach().numpy()
    except Exception as e:
        print(f"[voice_id] embed fail: {e}")
        return None


def register_voice(audio_np, sample_rate=16000):
    emb = _embed(audio_np, sample_rate)
    if emb is None:
        return False
    with open(VOICE_DB, "wb") as f:
        pickle.dump(emb, f)
    return True


def is_boss(audio_np, threshold=0.25):
    # Development override
    if os.environ.get("NOVA_ALLOW_ANY") == "1":
        return True

    if not os.path.exists(VOICE_DB):
        print("[voice_id] SECURITY: no voice print. Fail closed.")
        return False
    emb = _embed(audio_np)
    if emb is None:
        print("[voice_id] SECURITY: embed failed. Fail closed.")
        return False
    try:
        with open(VOICE_DB, "rb") as f:
            boss_emb = pickle.load(f)
        sim = float(np.dot(emb, boss_emb) / (
            np.linalg.norm(emb) * np.linalg.norm(boss_emb) + 1e-8
        ))
        print(f"[voice_id] similarity: {sim:.2f}")
        return sim > threshold
    except Exception as e:
        print(f"[voice_id] compare fail: {e}")
        return False


def is_enrolled():
    """Check if user voice is registered."""
    return os.path.exists(VOICE_DB)


def has_voice():
    return os.path.exists(VOICE_DB)


def reset_voice():
    if os.path.exists(VOICE_DB):
        os.remove(VOICE_DB)
        return True
    return False


if __name__ == "__main__":
    import sounddevice as sd

    print("=" * 55)
    print("  NOVA VOICE ID - Registration")
    print("=" * 55)
    get_classifier()
    print()
    print("Boss, 3 baar bolo: 'Main Boss hoon, mera naam Pappu hai'")
    print()

    samples = []
    i = 0
    while i < 3:
        input(f"Enter dabao - Recording {i+1}/3...")
        audio = sd.rec(int(5 * 16000), samplerate=16000,
                       channels=1, dtype="int16", device=1)
        sd.wait()
        peak = float(np.abs(audio).max())
        print(f"  Peak: {peak:.0f}")
        if peak < 500:
            print("  WEAK - dobara bolo")
            continue
        samples.append(audio.flatten())
        print("  OK")
        i += 1

    if len(samples) >= 2:
        combined = np.concatenate(samples)
        print("\nRegistering...")
        if register_voice(combined):
            print("SUCCESS - Boss voice save ho gayi!")
        else:
            print("FAIL")
    else:
        print("Kam se kam 2 samples chahiye")
